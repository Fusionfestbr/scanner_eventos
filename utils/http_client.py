"""
HTTP Client com resiliência: retry, circuit breaker e timeout.
Fornece wrappers seguros para todas as chamadas HTTP externas.
"""
import os
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Any, Callable, Optional
from functools import wraps
from utils.logger import logger

DEFAULT_TIMEOUT = int(os.environ.get("DEFAULT_TIMEOUT", "30"))
DEFAULT_RETRY = int(os.environ.get("API_RETRY_MAX", "3"))
CIRCUIT_BREAKER_THRESHOLD = int(os.environ.get("CIRCUIT_BREAKER_THRESHOLD", "5"))
CIRCUIT_BREAKER_TIMEOUT = int(os.environ.get("CIRCUIT_BREAKER_TIMEOUT", "60"))


class CircuitBreaker:
    """Circuit breaker para proteção contra falhas em cascata."""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half-open
    
    def record_success(self):
        """Registra sucesso e reseta contador."""
        self.failures = 0
        self.state = "closed"
    
    def record_failure(self):
        """Registra falha e abre o circuit se necessário."""
        self.failures += 1
        self.last_failure_time = time.time()
        
        if self.failures >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker ABERTO após {self.failures} falhas")
    
    def can_execute(self) -> bool:
        """Verifica se pode executar ou se está em timeout."""
        if self.state == "closed":
            return True
        
        elapsed = time.time() - self.last_failure_time
        if elapsed >= self.timeout:
            self.state = "half-open"
            logger.info("Circuit breaker em modo TESTE")
            return True
        
        return False
    
    def get_status(self) -> str:
        """Retorna status atual."""
        return self.state


class ResilientSession:
    """
    Sessão HTTP com retry automático e circuit breaker.
    Uso:
        session = ResilientSession()
        response = session.get(url)
        response = session.post(url, json={...})
    """
    
    def __init__(
        self,
        retries: int = DEFAULT_RETRY,
        timeout: int = DEFAULT_TIMEOUT,
        circuit_threshold: int = CIRCUIT_BREAKER_THRESHOLD,
        circuit_timeout: int = CIRCUIT_BREAKER_TIMEOUT
    ):
        self.retries = retries
        self.timeout = timeout
        self.session = requests.Session()
        self.circuit_breakers = {}
        
        retry_strategy = Retry(
            total=retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "PATCH"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        logger.info(f"ResilientSession criada: retry={retries}, timeout={timeout}s")
    
    def _get_circuit(self, name: str) -> CircuitBreaker:
        """Obtém ou cria circuit breaker para o serviço."""
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = CircuitBreaker(
                failure_threshold=CIRCUIT_BREAKER_THRESHOLD,
                timeout=CIRCUIT_BREAKER_TIMEOUT
            )
        return self.circuit_breakers[name]
    
    def request(
        self,
        method: str,
        url: str,
        service_name: str = "default",
        **kwargs
    ) -> Optional[requests.Response]:
        """
        Faz requisição HTTP com resiliência.
        
        Args:
            method: GET, POST, PUT, DELETE, etc.
            url: URL da requisição
            service_name: Nome do serviço para circuit breaker
            **kwargs: Argumentos para requests (json, params, headers, etc.)
            
        Returns:
            Response ou None em caso de falha
        """
        circuit = self._get_circuit(service_name)
        
        if not circuit.can_execute():
            logger.warning(f"Circuit breaker ABERTO para {service_name}, pulando requisição")
            return None
        
        timeout = kwargs.pop("timeout", self.timeout)
        
        try:
            response = self.session.request(
                method,
                url,
                timeout=timeout,
                **kwargs
            )
            response.raise_for_status()
            circuit.record_success()
            return response
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout ({timeout}s) em {url}")
            circuit.record_failure()
            return None
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Erro de conexão: {service_name} - {e}")
            circuit.record_failure()
            return None
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Erro HTTP: {response.status_code} - {e}")
            if response.status_code in [429, 500, 502, 503, 504]:
                circuit.record_failure()
            return None
            
        except Exception as e:
            logger.error(f"Erro inesperado em {service_name}: {e}")
            circuit.record_failure()
            return None
    
    def get(self, url: str, service_name: str = "default", **kwargs) -> Optional[requests.Response]:
        """GET com resiliência."""
        return self.request("GET", url, service_name, **kwargs)
    
    def post(self, url: str, service_name: str = "default", **kwargs) -> Optional[requests.Response]:
        """POST com resiliência."""
        return self.request("POST", url, service_name, **kwargs)
    
    def put(self, url: str, service_name: str = "default", **kwargs) -> Optional[requests.Response]:
        """PUT com resiliência."""
        return self.request("PUT", url, service_name, **kwargs)
    
    def delete(self, url: str, service_name: str = "default", **kwargs) -> Optional[requests.Response]:
        """DELETE com resiliência."""
        return self.request("DELETE", url, service_name, **kwargs)
    
    def get_status(self, service_name: str = "default") -> str:
        """Retorna status do circuit breaker."""
        circuit = self._get_circuit(service_name)
        return circuit.get_status()


_default_session: Optional[ResilientSession] = None


def get_session() -> ResilientSession:
    """Retorna sessão HTTP global (singleton)."""
    global _default_session
    if _default_session is None:
        _default_session = ResilientSession()
    return _default_session


def with_resilience(service_name: str = "default"):
    """
    Decorator para adicionar resiliência a funções.
    
    Uso:
        @with_resilience("ingresse")
        def buscar_eventos():
            return requests.get(url)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            session = get_session()
            result = func(*args, **kwargs)
            
            if result is None:
                logger.warning(f"Falha em {service_name}, tentando fallback")
                try:
                    result = func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Fallback falhou: {e}")
                    return None
            
            return result
        return wrapper
    return decorator