"""
Validação e sanitização de inputs.
Proteção contra XSS, injection e dados maliciosos.
"""
import re
import html
from typing import Any, Optional
from utils.logger import logger

MAX_STRING_LENGTH = 500
MAX_LIST_LENGTH = 1000
MAX_DEPTH = 5

DANGEROUS_PATTERNS = [
    r'<script',
    r'javascript:',
    r'onerror=',
    r'onclick=',
    r'onload=',
    r'<iframe',
    r'<!DOCTYPE',
    r'--><',
    r'eval\(',
    r'exec\(',
]


def sanitizar_string(texto: Any, max_length: int = MAX_STRING_LENGTH) -> str:
    """
    Sanitiza uma string, removendo caracteres perigosos.
    
    Args:
        texto: String ou valor a sanitizar
        max_length: Tamanho máximo permitido
        
    Returns:
        String sanitizada
    """
    if texto is None:
        return ""
    
    texto = str(texto)
    
    texto = html.escape(texto)
    
    texto = texto[:max_length]
    
    return texto.strip()


def sanitizar_evento(evento: dict) -> dict:
    """
    Sanitiza um evento completo.
    
    Args:
        evento: Dict do evento
        
    Returns:
        Evento sanitizado
    """
    sanitizado = {}
    
    campos_string = [
        "nome", "artista", "cidade", "estado", "pais",
        "fonte", "url", "categoria", "descricao",
        "tipo_geografico", "estilo"
    ]
    
    for campo in campos_string:
        valor = evento.get(campo)
        if valor:
            sanitizado[campo] = sanitizar_string(valor)
    
    campos_int = ["preco_base", "capacidade", "preco_min", "preco_max"]
    
    for campo in campos_int:
        valor = evento.get(campo)
        if valor:
            try:
                sanitizado[campo] = max(0, int(valor))
            except (ValueError, TypeError):
                sanitizado[campo] = 0
    
    campos_data = ["data", "data_inicio", "data_fim", "data_evento"]
    
    for campo in campos_data:
        valor = evento.get(campo)
        if valor:
            sanitizado[campo] = sanitizar_data(valor)
    
    return sanitizado


def sanitizar_data(data: Any) -> str:
    """
    Sanitiza e valida uma data.
    
    Args:
        data: String de data
        
    Returns:
        Data sanitizada ou string vazia
    """
    if data is None:
        return ""
    
    data = str(data)
    
    data = re.sub(r'[^\d\-T:/. ]+', '', data)
    
    if len(data) > 50:
        data = data[:50]
    
    return data


def validar_busca(termo: Any, max_length: int = 100) -> Optional[str]:
    """
    Valida termo de busca.
    
    Args:
        termo: Termo a validar
        max_length: Tamanho máximo
        
    Returns:
        Termo válido ou None
    """
    if termo is None:
        return None
    
    termo = str(termo).strip()
    
    if len(termo) < 2 or len(termo) > max_length:
        return None
    
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, termo, re.IGNORECASE):
            logger.warning(f"Busca bloqueada: padrão perigoso detectado em '{termo}'")
            return None
    
    return termo


def validar_filtro(valor: Any, valores_validos: list = None) -> Optional[str]:
    """
    Valida um filtro de URL.
    
    Args:
        valor: Valor do filtro
        valores_validos: Lista de valores permitidos
        
    Returns:
        Valor válido ou None
    """
    if valor is None:
        return None
    
    valor = str(valor).strip()
    
    if len(valor) > MAX_STRING_LENGTH:
        return None
    
    if valores_validos and valor not in valores_validos:
        return None
    
    return valor


def validar_json_seguro(data: Any, depth: int = 0) -> bool:
    """
    Valida seJSON não contém estruturas perigosas.
    
    Args:
        data: Dados a validar
        depth: Profundidade atual (para evitar recursão)
        
    Returns:
        True se seguro
    """
    if depth > MAX_DEPTH:
        return False
    
    if data is None:
        return True
    
    if isinstance(data, str):
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, data, re.IGNORECASE):
                return False
        return True
    
    if isinstance(data, dict):
        for key, value in data.items():
            if not validar_json_seguro(value, depth + 1):
                return False
        return True
    
    if isinstance(data, (list, tuple)):
        if len(data) > MAX_LIST_LENGTH:
            return False
        for item in data:
            if not validar_json_seguro(item, depth + 1):
                return False
        return True
    
    if isinstance(data, (int, float, bool)):
        return True
    
    return False


def sanitize_email(email: Any) -> Optional[str]:
    """
    Valida e sanitiza email.
    
    Args:
        email: Email a validar
        
    Returns:
        Email válido ou None
    """
    if email is None:
        return None
    
    email = str(email).strip().lower()
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if re.match(pattern, email):
        return email
    
    return None


def sanitize_url(url: Any) -> Optional[str]:
    """
    Valida e sanitiza URL.
    
    Args:
        url: URL a validar
        
    Returns:
        URL válida ou None
    """
    if url is None:
        return None
    
    url = str(url).strip()
    
    if len(url) > MAX_STRING_LENGTH:
        return None
    
    if not url.startswith(('http://', 'https://')):
        return None
    
    if any(pattern in url.lower() for pattern in DANGEROUS_PATTERNS):
        return None
    
    return url[:MAX_STRING_LENGTH]


def validar_intervalo(minimo: Any, maximo: Any, valor: Any, padrao: Any = None) -> Any:
    """
    Valida se um valor está dentro de um intervalo.
    
    Args:
        minimo: Valor mínimo
        maximo: Valor máximo
        valor: Valor a validar
        padrao: Valor padrão se inválido
        
    Returns:
        Valor válido ou padrão
    """
    try:
        valor = int(valor)
        if minimo <= valor <= maximo:
            return valor
    except (ValueError, TypeError):
        pass
    
    return padrao


class InputValidator:
    """Validador de inputs com regras customizáveis."""
    
    def __init__(self):
        self.erros = []
    
    def validar(self, dados: dict, regras: dict) -> bool:
        """
        Valida dados segundo regras.
        
        Args:
            dados: Dict com dados a validar
            regras: Dict com regras {campo: tipo}
            
        Returns:
            True se válido
        """
        self.erros = []
        
        for campo, tipo in regras.items():
            valor = dados.get(campo)
            
            if tipo == "string" and not valor:
                self.erros.append(f"Campo '{campo}' é obrigatório")
            
            elif tipo == "int":
                try:
                    int(valor)
                except (ValueError, TypeError):
                    self.erros.append(f"Campo '{campo}' deve ser número")
            
            elif tipo == "email":
                if not sanitize_email(valor):
                    self.erros.append(f"Campo '{campo}' é email inválido")
            
            elif tipo == "url":
                if not sanitize_url(valor):
                    self.erros.append(f"Campo '{campo}' é URL inválida")
        
        return len(self.erros) == 0
    
    def get_erros(self) -> list:
        """Retorna lista de erros."""
        return self.erros