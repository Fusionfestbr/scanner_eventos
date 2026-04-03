"""
Módulo Executor - Transformação de decisões em ações operacionais.
Gera planos de ação concretos para compra e venda de ingressos.
"""
from datetime import datetime
from typing import Dict, List, Optional


def calcular_quantidade(score_valorizacao: float, probabilidade_esgotar: float) -> Dict:
    """
    Calcula quantidade recomendada de compra.
    
    Returns:
        Dicionário com quantidade textual e numérica
    """
    if score_valorizacao >= 8 and probabilidade_esgotar >= 75:
        return {"nivel": "alto", "min": 6, "max": 10, "recomendado": 8}
    elif score_valorizacao >= 7 and probabilidade_esgotar >= 60:
        return {"nivel": "médio", "min": 3, "max": 5, "recomendado": 4}
    elif score_valorizacao >= 6 and probabilidade_esgotar >= 50:
        return {"nivel": "baixo", "min": 1, "max": 2, "recomendado": 2}
    else:
        return {"nivel": "mínimo", "min": 1, "max": 1, "recomendado": 1}


def calcular_momento(probabilidade_esgotar: float, nota_final: float) -> str:
    """
    Determina o momento ideal para compra.
    
    Returns:
        "agora", "monitorar" ou "aguardar"
    """
    if probabilidade_esgotar >= 75:
        return "agora"
    elif probabilidade_esgotar >= 50:
        return "monitorar"
    else:
        return "aguardar"


def calcular_estrategia_saida(probabilidade_esgotar: float, score_valorizacao: float) -> str:
    """
    Define estratégia de saída (venda).
    
    Returns:
        "premium", "gradual" ou "rápida"
    """
    if probabilidade_esgotar >= 80:
        return "premium"
    elif probabilidade_esgotar >= 60:
        return "gradual"
    else:
        return "rápida"


def calcular_preco_alvo(preco_inicial: float, score_valorizacao: float) -> float:
    """
    Estima preço alvo de venda baseado no score de valorização.
    
    Returns:
        Preço alvo estimado
    """
    if preco_inicial <= 0:
        return 0.0
    
    multiplicador = 1 + (score_valorizacao / 20)
    return round(preco_inicial * multiplicador, 2)


def estimar_margem(preco_inicial: float, preco_alvo: float) -> str:
    """
    Estima margem percentual de lucro.
    
    Returns:
        String com percentual
    """
    if preco_inicial <= 0 or preco_alvo <= 0:
        return "0%"
    
    margem = ((preco_alvo - preco_inicial) / preco_inicial) * 100
    return f"{margem:.0f}%"


def gerar_plano_acao(evento: dict) -> dict:
    """
    Gera plano de ação operacional para um evento.
    
    Args:
        evento: Dicionário completo do evento (com evento, analise, auditoria, previsao)
    
    Returns:
        Dicionário com plano de ação:
        - comprar: bool
        - quantidade: dict com nivel, min, max, recomendado
        - momento_compra: string
        - estrategia_saida: string
        - preco_alvo_venda: float
        - margem_estimada: string
    """
    acao_final = evento.get("acao_final", "IGNORAR")
    analise = evento.get("analise", {})
    previsao = evento.get("previsao", {})
    evento_info = evento.get("evento", {})
    
    score_valorizacao = previsao.get("score_valorizacao", 0)
    probabilidade_esgotar = previsao.get("probabilidade_esgotar", 0)
    nota_final = analise.get("nota_final", 0)
    preco_inicial = evento_info.get("preco", 0)
    
    comprar = False
    if acao_final == "COMPRAR":
        if score_valorizacao >= 6 or probabilidade_esgotar >= 60:
            comprar = True
    
    quantidade = calcular_quantidade(score_valorizacao, probabilidade_esgotar)
    momento_compra = calcular_momento(probabilidade_esgotar, nota_final)
    estrategia_saida = calcular_estrategia_saida(probabilidade_esgotar, score_valorizacao)
    preco_alvo_venda = calcular_preco_alvo(preco_inicial, score_valorizacao)
    margem_estimada = estimar_margem(preco_inicial, preco_alvo_venda)
    
    plano = {
        "comprar": comprar,
        "quantidade": quantidade,
        "momento_compra": momento_compra,
        "estrategia_saida": estrategia_saida,
        "preco_alvo_venda": preco_alvo_venda,
        "margem_estimada": margem_estimada,
        "gerado_em": datetime.now().isoformat()
    }
    
    return plano


def processar_planos_acao(eventos: List[dict]) -> List[dict]:
    """
    Processa planos de ação para todos os eventos.
    
    Args:
        eventos: Lista de eventos com dados completos
    
    Returns:
        Lista de eventos com campo 'plano_acao' adicionado
    """
    resultados = []
    
    for evento in eventos:
        evento_com_plano = evento.copy()
        plano = gerar_plano_acao(evento)
        evento_com_plano["plano_acao"] = plano
        resultados.append(evento_com_plano)
    
    return resultados


def reavaliar_planos(eventos_comprados: List[dict]) -> List[dict]:
    """
    Reavalia planos de eventos já comprados.
    Útil para execução periódica (ex: a cada 6h).
    
    Args:
        eventos_comprados: Lista de eventos com plano_acao
    
    Returns:
        Lista de eventos com planos atualizados
    """
    resultados = []
    
    for evento in eventos_comprados:
        evento_atualizado = evento.copy()
        
        plano_antigo = evento.get("plano_acao", {})
        if not plano_antigo:
            continue
        
        previsao = evento.get("previsao", {})
        analise = evento.get("analise", {})
        
        score = previsao.get("score_valorizacao", 0)
        prob = previsao.get("probabilidade_esgotar", 0)
        nota = analise.get("nota_final", 0)
        
        novo_momento = calcular_momento(prob, nota)
        nova_estrategia = calcular_estrategia_saida(prob, score)
        
        plano_atualizado = plano_antigo.copy()
        plano_atualizado["momento_compra"] = novo_momento
        plano_atualizado["estrategia_saida"] = nova_estrategia
        plano_atualizado["reavaliado_em"] = datetime.now().isoformat()
        plano_atualizado["alterou_estrategia"] = nova_estrategia != plano_antigo.get("estrategia_saida")
        
        evento_atualizado["plano_acao"] = plano_atualizado
        resultados.append(evento_atualizado)
    
    return resultados


def filtrar_oportunidades_comprar(eventos: List[dict]) -> List[dict]:
    """
    Filtra eventos com recomendação de compra.
    
    Args:
        eventos: Lista de eventos com plano_acao
    
    Returns:
        Lista de eventos com comprar=True
    """
    return [e for e in eventos if e.get("plano_acao", {}).get("comprar", False)]


def gerar_resumo_executor(eventos: List[dict]) -> dict:
    """
    Gera resumo estatístico dos planos de ação.
    
    Returns:
        Dicionário com estatísticas
    """
    total = len(eventos)
    
    comprar_true = sum(1 for e in eventos if e.get("plano_acao", {}).get("comprar", False))
    
    momentos = {}
    estrategias = {}
    
    for e in eventos:
        plano = e.get("plano_acao", {})
        momento = plano.get("momento_compra", "N/A")
        estrategia = plano.get("estrategia_saida", "N/A")
        
        momentos[momento] = momentos.get(momento, 0) + 1
        estrategias[estrategia] = estrategias.get(estrategia, 0) + 1
    
    return {
        "total_eventos": total,
        "oportunidades_comprar": comprar_true,
        "por_momento": momentos,
        "por_estrategia": estrategias
    }