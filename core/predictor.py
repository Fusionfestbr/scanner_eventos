from datetime import datetime
from typing import Dict, List, Optional
from core.historico_valorizacao import (
    carregar_historico,
    obter_estatisticas_artista,
    obter_tipos_evento
)


def calcular_score_nota(nota_final: float) -> float:
    """Calcula score baseado na nota do evento (peso 40%)."""
    if nota_final >= 8:
        return 10.0
    elif nota_final >= 7:
        return 7.0
    elif nota_final >= 6:
        return 5.0
    else:
        return 3.0


def calcular_score_historico(nome_artista: str) -> float:
    """Calcula score baseado no histórico do artista (peso 30%)."""
    stats = obter_estatisticas_artista(nome_artista)
    
    if stats["total_eventos"] == 0:
        return 0.0
    
    taxa_esgotamento = stats["taxa_esgotamento"]
    
    if taxa_esgotamento >= 80:
        return 10.0
    elif taxa_esgotamento >= 50:
        return 7.0
    elif taxa_esgotamento > 0:
        return 4.0
    else:
        return 1.0


def calcular_score_tipo(nome_evento: str) -> float:
    """Calcula score baseado no tipo de evento (peso 20%)."""
    tipo = obter_tipos_evento(nome_evento)
    
    if tipo == "festival":
        return 10.0
    elif tipo == "turnê":
        return 6.0
    else:
        return 3.0


def calcular_score_urgencia(data_evento: str) -> float:
    """Calcula score baseado na proximidade do evento (peso 10%)."""
    try:
        evento_date = datetime.fromisoformat(data_evento.replace("T", " "))
        hoje = datetime.now()
        dias_ate_evento = (evento_date - hoje).days
        
        if dias_ate_evento <= 7:
            return 10.0
        elif dias_ate_evento <= 30:
            return 7.0
        elif dias_ate_evento <= 90:
            return 4.0
        else:
            return 2.0
    except:
        return 5.0


def calcular_probabilidade_esgotar(nota_final: float, nome_artista: str, nome_evento: str, data_evento: str) -> float:
    """Calcula probabilidade de esgotamento do evento."""
    stats = obter_estatisticas_artista(nome_artista)
    
    prob_base = 30
    
    if nota_final >= 8:
        prob_base += 30
    elif nota_final >= 7:
        prob_base += 15
    
    if stats["total_eventos"] > 0:
        if stats["taxa_esgotamento"] >= 80:
            prob_base += 20
        elif stats["taxa_esgotamento"] >= 50:
            prob_base += 10
    
    tipo = obter_tipos_evento(nome_evento)
    if tipo == "festival":
        prob_base += 15
    elif tipo == "turnê":
        prob_base += 5
    
    try:
        evento_date = datetime.fromisoformat(data_evento.replace("T", " "))
        dias_ate = (evento_date - datetime.now()).days
        if 0 < dias_ate <= 30:
            prob_base += 10
    except:
        pass
    
    return min(prob_base, 95)


def determinar_volume(nota_final: float, prob_esgotar: float, score_valorizacao: float) -> str:
    """Determina recomendação de volume de compra."""
    if score_valorizacao >= 8 and prob_esgotar >= 70:
        return "alto"
    elif score_valorizacao >= 6 or prob_esgotar >= 50:
        return "médio"
    else:
        return "baixo"


def prever_valorizacao(evento: Dict) -> Dict:
    """
    Preve potencial de valorização de um evento.
    
    Args:
        evento: Dicionário com dados do evento
        
    Returns:
        Dicionário com:
        - score_valorizacao (0-10): Score de valorização
        - probabilidade_esgotar (%): Probabilidade de esgotar
        - recomendacao_volume: "baixo", "médio" ou "alto"
    """
    evento_info = evento.get("evento", {})
    analise = evento.get("analise", {})
    
    nome_evento = evento_info.get("nome", "")
    nome_artista = evento_info.get("artista", "Various Artists")
    data_evento = evento_info.get("data", "")
    nota_final = analise.get("nota_final", 5.0)
    
    score_nota = calcular_score_nota(nota_final) * 0.40
    score_historico = calcular_score_historico(nome_artista) * 0.30
    score_tipo = calcular_score_tipo(nome_evento) * 0.20
    score_urgencia = calcular_score_urgencia(data_evento) * 0.10
    
    score_valorizacao = score_nota + score_historico + score_tipo + score_urgencia
    
    probabilidade_esgotar = calcular_probabilidade_esgotar(
        nota_final, nome_artista, nome_evento, data_evento
    )
    
    recomendacao_volume = determinar_volume(
        nota_final, probabilidade_esgotar, score_valorizacao
    )
    
    return {
        "score_valorizacao": round(score_valorizacao, 1),
        "probabilidade_esgotar": round(probabilidade_esgotar, 1),
        "recomendacao_volume": recomendacao_volume
    }


def processar_previsoes(eventos: List[Dict]) -> List[Dict]:
    """Processa previsões para todos os eventos."""
    resultados = []
    
    for evento in eventos:
        evento_com_previsao = evento.copy()
        
        acao = evento.get("acao_final", "IGNORAR")
        if acao in ["COMPRAR", "MONITORAR"]:
            previsao = prever_valorizacao(evento)
            evento_com_previsao["previsao"] = previsao
        else:
            evento_com_previsao["previsao"] = {
                "score_valorizacao": 0,
                "probabilidade_esgotar": 0,
                "recomendacao_volume": "baixo"
            }
        
        resultados.append(evento_com_previsao)
    
    return resultados