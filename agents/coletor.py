"""
Agente coletor de eventos.
Simula coleta de eventos (hardcoded para esta fase).
"""
from datetime import datetime, timedelta


def coletar_eventos() -> list[dict]:
    """
    Retorna lista de eventos coletados.
    Inclui:
    - 2 eventos futuros válidos
    - 2 eventos passados (para teste)
    - 1 evento duplicado
    """
    hoje = datetime.now()
    
    eventos = [
        {
            "nome": "Rock in Rio 2026",
            "artista": "Various Artists",
            "data": "2026-09-15",
            "cidade": "Rio de Janeiro",
            "fonte": "simulado",
            "url": "https://rockinrio.com"
        },
        {
            "nome": "Lollapalooza Brasil",
            "artista": "Various Artists",
            "data": "2026-05-28",
            "cidade": "São Paulo",
            "fonte": "simulado",
            "url": "https://lollapaloozabr.com"
        },
        {
            "nome": "Show Metallica",
            "artista": "Metallica",
            "data": "2025-01-10",
            "cidade": "São Paulo",
            "fonte": "simulado",
            "url": "https://metallica.com"
        },
        {
            "nome": "Festival de Verão",
            "artista": "Various Artists",
            "data": "2025-12-20",
            "cidade": "Salvador",
            "fonte": "simulado",
            "url": "https://festivaldeverao.com"
        },
        {
            "nome": "Rock in Rio 2026",
            "artista": "Various Artists",
            "data": "2026-09-15",
            "cidade": "Rio de Janeiro",
            "fonte": "simulado",
            "url": "https://rockinrio.com"
        }
    ]
    
    return eventos