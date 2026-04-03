"""
Agente validador de eventos.
Realiza limpeza e validação dos dados coletados.
"""
from utils.date_utils import (
    validar_data,
    data_eh_futura,
    formatar_data_iso
)


def validar_eventos(eventos: list[dict]) -> list[dict]:
    """
    Valida e limpa lista de eventos.
    
    Regras:
    - Remove eventos com data anterior ao dia atual
    - Remove eventos com data inválida
    - Remove duplicados (mesmo nome + data)
    - Padroniza data no formato YYYY-MM-DD
    """
    eventos_validos = []
    seen = set()
    
    for evento in eventos:
        data_str = evento.get("data", "")
        
        if not validar_data(data_str):
            continue
            
        if not data_eh_futura(data_str):
            continue
        
        data_iso = formatar_data_iso(data_str)
        if not data_iso:
            continue
            
        key = (evento.get("nome", "").lower(), data_iso)
        if key in seen:
            continue
        seen.add(key)
        
        evento_limpo = {
            "nome": evento.get("nome", "").strip(),
            "artista": evento.get("artista", "").strip(),
            "data": data_iso,
            "cidade": evento.get("cidade", "").strip(),
            "fonte": evento.get("fonte", "").strip(),
            "url": evento.get("url", "").strip()
        }
        eventos_validos.append(evento_limpo)
    
    return eventos_validos