"""
Agente coletor de eventos.
Apenas modo real - SEM FALLBACK.
"""
from agents.scraper import buscar_eventos_reais


def coletar_eventos() -> list[dict]:
    """
    Retorna lista de eventos coletados das fontes reais.
    SEM FALLBACK - retorna apenas dados reais ou lista vazia.
    """
    eventos = buscar_eventos_reais()
    eventos_validos = [e for e in eventos if e.get("data")]
    
    if not eventos_validos:
        print("   [ALERTA] Nenhum evento encontrado na varredura")
        print("   [INFO] Pipeline continua vazio (sem fallback)")
    
    return eventos_validos
