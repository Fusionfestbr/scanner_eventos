"""
Agente coletor de eventos.
Suporta modo simulado (fallback) e real (scraper).
"""
from config import MODO_COLETA
from agents.scraper import buscar_eventos_reais


def coletar_eventos(modo: str | None = None) -> list[dict]:
    """
    Retorna lista de eventos coletados.
    
    Args:
        modo: "simulado" ou "real" (default: config.MODO_COLETA)
    
    Returns:
        Lista de eventos
    """
    modo = modo or MODO_COLETA
    
    if modo == "real":
        eventos = buscar_eventos_reais()
        eventos_validos = [e for e in eventos if e.get("data")]
        if eventos_validos:
            return eventos_validos
        print("   [WARN] Scraping não retornou eventos válidos, usando modo simulado")
    
    return coletar_eventos_simulados()


def coletar_eventos_simulados() -> list[dict]:
    """
    Retorna lista de eventos simulados (fallback).
    """
    eventos = [
        {"nome": "Rock in Rio 2026", "artista": "Various Artists", "data": "2026-09-15", "cidade": "Rio de Janeiro", "fonte": "simulado", "url": "https://rockinrio.com"},
        {"nome": "Lollapalooza Brasil", "artista": "Various Artists", "data": "2026-05-28", "cidade": "São Paulo", "fonte": "simulado", "url": "https://lollapaloozabr.com"},
        {"nome": "Show Metallica", "artista": "Metallica", "data": "2025-01-10", "cidade": "São Paulo", "fonte": "simulado", "url": "https://metallica.com"},
        {"nome": "Festival de Verão", "artista": "Various Artists", "data": "2025-12-20", "cidade": "Salvador", "fonte": "simulado", "url": "https://festivaldeverao.com"},
        {"nome": "Rock in Rio 2026", "artista": "Various Artists", "data": "2026-09-15", "cidade": "Rio de Janeiro", "fonte": "simulado", "url": "https://rockinrio.com"},
        {"nome": "Show Taylor Swift", "artista": "Taylor Swift", "data": "2026-06-20", "cidade": "São Paulo", "fonte": "simulado", "url": "https://taylorswift.com"},
        {"nome": "Rock in Rio 2026", "artista": "Various Artists", "data": "2026-09-15", "cidade": "Rio de Janeiro", "fonte": "simulado", "url": "https://rockinrio.com"},
        {"nome": "Festival Tomorrowland", "artista": "Various Artists", "data": "2026-07-15", "cidade": "São Paulo", "fonte": "simulado", "url": "https://tomorrowland.com"},
        {"nome": "Show Beyoncé", "artista": "Beyoncé", "data": "2026-08-10", "cidade": "Rio de Janeiro", "fonte": "simulado", "url": "https://beyonce.com"},
        {"nome": "Rock in Rio 2026", "artista": "Various Artists", "data": "2026-09-15", "cidade": "Rio de Janeiro", "fonte": "simulado", "url": "https://rockinrio.com"},
    ]
    
    return eventos
