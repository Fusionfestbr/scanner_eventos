"""
Módulo de ranking de eventos.
Ordena eventos por decisão, nota e confiança.
"""
import json
import os
from typing import List, Dict

RANKING_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "ranking.json")

PESO_ACAO = {
    "COMPRAR": 3,
    "MONITORAR": 2,
    "IGNORAR": 1
}


def gerar_ranking(eventos: List[dict]) -> List[dict]:
    """
    Ordena eventos por:
    1. acao_final (COMPRAR > MONITORAR > IGNORAR)
    2. nota_final (maior primeiro)
    3. confianca (maior primeiro)
    
    Returns:
        Lista ordenada de eventos
    """
    def chave_ordenacao(item):
        acao = item.get("acao_final", "IGNORAR")
        nota = item.get("analise", {}).get("nota_final", 0)
        confianca = item.get("auditoria", {}).get("confianca", 0)
        
        peso_acao = PESO_ACAO.get(acao, 0)
        
        return (peso_acao, nota, confianca)
    
    ranking = sorted(eventos, key=chave_ordenacao, reverse=True)
    
    for i, item in enumerate(ranking, 1):
        item["posicao"] = i
    
    return ranking


def salvar_ranking(ranking: List[dict]) -> None:
    """Salva ranking em JSON."""
    os.makedirs(os.path.dirname(RANKING_FILE), exist_ok=True)
    with open(RANKING_FILE, "w", encoding="utf-8") as f:
        json.dump(ranking, f, ensure_ascii=False, indent=2)


def carregar_ranking() -> List[dict]:
    """Carrega ranking do JSON."""
    if not os.path.exists(RANKING_FILE):
        return []
    try:
        with open(RANKING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def get_estatisticas(ranking: List[dict]) -> dict:
    """Calcula estatísticas do ranking."""
    total = len(ranking)
    
    comprar = sum(1 for e in ranking if e.get("acao_final") == "COMPRAR")
    monitorar = sum(1 for e in ranking if e.get("acao_final") == "MONITORAR")
    ignorar = sum(1 for e in ranking if e.get("acao_final") == "IGNORAR")
    
    notas = [e.get("analise", {}).get("nota_final", 0) for e in ranking]
    nota_media = sum(notas) / total if total > 0 else 0
    
    return {
        "total": total,
        "comprar": comprar,
        "monitorar": monitorar,
        "ignorar": ignorar,
        "nota_media": round(nota_media, 2)
    }
