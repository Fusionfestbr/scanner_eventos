"""
Rate Limiting para proteção contra sobrecarga.
Limita o número de requisições por IP em janelas de tempo.
"""
import time
import os
from collections import defaultdict
from functools import wraps
from typing import Callable, Dict, Tuple
from utils.logger import logger

DEFAULT_REQUESTS_PER_MINUTE = int(os.environ.get("RATE_LIMIT_RPM", "1000"))
DEFAULT_REQUESTS_PER_HOUR = int(os.environ.get("RATE_LIMIT_RPH", "10000"))
BAN_DURATION = int(os.environ.get("RATE_BAN_DURATION", "300"))


class RateLimiter:
    """Rate limiter em memória."""
    
    def __init__(self, rpm: int = DEFAULT_REQUESTS_PER_MINUTE, rph: int = DEFAULT_REQUESTS_PER_HOUR):
        self.rpm = rpm
        self.rph = rph
        self.requests: Dict[str, list] = defaultdict(list)
        self.banned: Dict[str, float] = {}
        logger.info(f"RateLimiter: {rpm}/min, {rph}/hora")
    
    def _clean_old_requests(self, ip: str, janela_minutos: int = 60):
        """Remove requisições antigas."""
        now = time.time()
        limite = now - (janela_minutos * 60)
        self.requests[ip] = [t for t in self.requests[ip] if t > limite]
    
    def _is_banned(self, ip: str) -> bool:
        """Verifica se IP está bloqueado."""
        if ip not in self.banned:
            return False
        
        if time.time() - self.banned[ip] > BAN_DURATION:
            del self.banned[ip]
            logger.info(f"IP {ip} desbloqueado")
            return False
        
        return True
    
    def check(self, ip: str) -> Tuple[bool, str]:
        """
        Verifica se requisição é permitida.
        
        Args:
            ip: Endereço IP do cliente
            
        Returns:
            (permitido, motivo)
        """
        if self._is_banned(ip):
            return False, "IP bloqueado temporariamente"
        
        now = time.time()
        
        self._clean_old_requests(ip, 1)
        if len(self.requests[ip]) >= self.rpm:
            self.banned[ip] = now
            logger.warning(f"IP {ip} bloqueado por excesso de requisições por minuto")
            return False, f"Limite de {self.rpm} req/min excedido"
        
        self._clean_old_requests(ip, 60)
        requests_hour = len(self.requests[ip])
        if requests_hour >= self.rph:
            self.banned[ip] = now
            logger.warning(f"IP {ip} bloqueado por excesso de requisições por hora")
            return False, f"Limite de {self.rph} req/hora excedido"
        
        self.requests[ip].append(now)
        return True, "OK"
    
    def get_status(self, ip: str) -> dict:
        """Retorna status do IP."""
        self._clean_old_requests(ip, 1)
        self._clean_old_requests(ip, 60)
        
        return {
            "rpm": len(self.requests[ip]),
            "rpm_limite": self.rpm,
            "banned": self._is_banned(ip),
            "ban_expira_em": self.banned.get(ip, 0)
        }


_rate_limiter: RateLimiter = None


def get_rate_limiter() -> RateLimiter:
    """Retorna rate limiter singleton."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def rate_limit(rpm: int = None, rph: int = None):
    """
    Decorador para limitar rate de funções.
    
    Uso:
        @rate_limit(rpm=10)
        def minha_funcao():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            limiter = get_rate_limiter()
            
            if rpm or rph:
                limiter.rpm = rpm or limiter.rpm
                limiter.rph = rph or limiter.rph
            
            permitido, motivo = limiter.check("function")
            
            if not permitido:
                logger.warning(f"Rate limit excedido para {func.__name__}: {motivo}")
                raise Exception(f"Rate limit: {motivo}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def check_ip(ip: str) -> bool:
    """Verifica se IP pode fazer requisição."""
    limiter = get_rate_limiter()
    permitido, _ = limiter.check(ip)
    return permitido