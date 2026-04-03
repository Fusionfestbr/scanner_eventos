"""
Módulo de Arbitragem - Detecção de diferenças de preço entre plataformas.
Identifica oportunidades de lucro imediato comparando preços oficiais vs revenda.
"""
import re
from typing import Dict, List, Optional
from config import ARBITRAGE_MIN_SPREAD, SITES_REVENDA


def limpar_preco(preco_str: str) -> float:
    """Converte string de preço para float."""
    if not preco_str:
        return 0.0
    
    preco_str = preco_str.strip()
    preco_str = re.sub(r'[R$\s]', '', preco_str)
    preco_str = preco_str.replace('.', '').replace(',', '.')
    
    try:
        return float(preco_str)
    except (ValueError, AttributeError):
        return 0.0


def detectar_arbitragem(evento: dict) -> dict:
    """
    Detecta oportunidades de arbitragem para um evento.
    
    Args:
        evento: Dicionário com dados do evento (pode conter precos_encontrados)
    
    Returns:
        Dicionário com análise de arbitragem:
        - menor_preco: menor preço encontrado
        - maior_preco: maior preço encontrado
        - spread_percent: diferença percentual
        - lucro_potencial: valor do lucro em cima do menor preço
        - oportunidade: true se spread >= ARBITRAGE_MIN_SPREAD
        - fonte_menor: plataforma do menor preço
        - fonte_maior: plataforma do maior preço
        - precos_encontrados: lista de preços por plataforma
    """
    precos = evento.get("precos_encontrados", [])
    
    if len(precos) < 2:
        return {
            "menor_preco": 0.0,
            "maior_preco": 0.0,
            "spread_percent": 0.0,
            "lucro_potencial": 0.0,
            "oportunidade": False,
            "fonte_menor": "",
            "fonte_maior": "",
            "precos_encontrados": []
        }
    
    precos_validos = [(p.get("plataforma", ""), p.get("preco", 0)) 
                      for p in precos if p.get("preco", 0) > 0]
    
    if not precos_validos:
        return {
            "menor_preco": 0.0,
            "maior_preco": 0.0,
            "spread_percent": 0.0,
            "lucro_potencial": 0.0,
            "oportunidade": False,
            "fonte_menor": "",
            "fonte_maior": "",
            "precos_encontrados": []
        }
    
    precos_ordenados = sorted(precos_validos, key=lambda x: x[1])
    
    menor_plataforma, menor_preco = precos_ordenados[0]
    maior_plataforma, maior_preco = precos_ordenados[-1]
    
    if menor_preco > 0:
        spread_percent = ((maior_preco - menor_preco) / menor_preco) * 100
        lucro_potencial = maior_preco - menor_preco
    else:
        spread_percent = 0.0
        lucro_potencial = 0.0
    
    oportunidade = spread_percent >= ARBITRAGE_MIN_SPREAD
    
    return {
        "menor_preco": menor_preco,
        "maior_preco": maior_preco,
        "spread_percent": round(spread_percent, 1),
        "lucro_potencial": round(lucro_potencial, 2),
        "oportunidade": oportunidade,
        "fonte_menor": menor_plataforma,
        "fonte_maior": maior_plataforma,
        "precos_encontrados": [
            {"plataforma": p[0], "preco": p[1]} for p in precos_validos
        ]
    }


def processar_arbitragem(eventos: List[dict], apenas_comprar: bool = True) -> List[dict]:
    """
    Processa detecção de arbitragem para todos os eventos.
    
    Args:
        eventos: Lista de eventos
        apenas_comprar: Se True, processa apenas eventos com acao_final == "COMPRAR"
    
    Returns:
        Lista de eventos com campo 'arbitragem' adicionado
    """
    resultados = []
    
    for evento in eventos:
        evento_com_arbitragem = evento.copy()
        
        precos_encontrados = evento.get("precos_encontrados", [])
        
        if apenas_comprar:
            acao = evento.get("acao_final", "IGNORAR")
            if acao != "COMPRAR":
                evento_com_arbitragem["arbitragem"] = {
                    "menor_preco": 0.0,
                    "maior_preco": 0.0,
                    "spread_percent": 0.0,
                    "lucro_potencial": 0.0,
                    "oportunidade": False,
                    "fonte_menor": "",
                    "fonte_maior": "",
                    "precos_encontrados": precos_encontrados
                }
                resultados.append(evento_com_arbitragem)
                continue
        
        if precos_encontrados:
            arbitragem = detectar_arbitragem(evento)
        else:
            arbitragem = {
                "menor_preco": 0.0,
                "maior_preco": 0.0,
                "spread_percent": 0.0,
                "lucro_potencial": 0.0,
                "oportunidade": False,
                "fonte_menor": "",
                "fonte_maior": "",
                "precos_encontrados": precos_encontrados
            }
        
        evento_com_arbitragem["arbitragem"] = arbitragem
        resultados.append(evento_com_arbitragem)
    
    return resultados


def filtrar_oportunidades_arbitragem(eventos: List[dict]) -> List[dict]:
    """
    Filtra eventos com oportunidades de arbitragem.
    
    Args:
        eventos: Lista de eventos com arbitragem
    
    Returns:
        Lista de eventos com oportunidade == True
    """
    return [e for e in eventos if e.get("arbitragem", {}).get("oportunidade", False)]


def gerar_resumo_arbitragem(eventos: List[dict]) -> dict:
    """
    Gera resumo estatístico de arbitragem.
    
    Returns:
        Dicionário com estatísticas
    """
    total = len(eventos)
    
    arbitragem = [e.get("arbitragem", {}) for e in eventos]
    oportunidades = sum(1 for a in arbitragem if a.get("oportunidade", False))
    
    spreads = [a.get("spread_percent", 0) for a in arbitragem if a.get("spread_percent", 0) > 0]
    lucro_total = sum(a.get("lucro_potencial", 0) for a in arbitragem)
    
    return {
        "total_eventos": total,
        "oportunidades_arbitragem": oportunidades,
        "spread_medio": round(sum(spreads) / len(spreads), 1) if spreads else 0,
        "lucro_potencial_total": round(lucro_total, 2)
    }