"""
Módulo de decisão automática.
Aplica regras de negócio para definir ações.
"""
from core.learning import obter_thresholds


def tomar_decisao(item: dict) -> dict:
    """
    Aplica regras de decisão com thresholds dinâmicos.
    
    Regras:
    - nota_final >= min_nota_comprar e confianca >= min_confianca → COMPRAR
    - nota_final >= 6 → MONITORAR
    - erro_detectado = true → IGNORAR
    - caso contrário → IGNORAR
    
    Ajustes por previsão:
    - score_valorizacao >= 8 e probabilidade >= 70% → COMPRA_AGGRESSIVA
    """
    analise = item.get("analise", {})
    auditoria = item.get("auditoria", {})
    previsao = item.get("previsao", {})
    
    nota_final = analise.get("nota_final", 0)
    confianca = auditoria.get("confianca", 0)
    erro_detectado = auditoria.get("erro_detectado", False)
    
    score_valorizacao = previsao.get("score_valorizacao", 0)
    probabilidade_esgotar = previsao.get("probabilidade_esgotar", 0)
    
    thresholds = obter_thresholds()
    min_nota = thresholds["min_nota_comprar"]
    min_confianca = thresholds["min_confianca"]
    
    if erro_detectado:
        acao = "IGNORAR"
        razao = "Erro detectado na análise"
    elif nota_final >= min_nota and confianca >= min_confianca:
        acao = "COMPRAR"
        razao = f"Alta nota e confiança (nota>={min_nota}, confianca>={min_confianca})"
    elif nota_final >= 6:
        acao = "MONITORAR"
        razao = "Nota média"
    else:
        acao = "IGNORAR"
        razao = "Nota insuficiente"
    
    compra_agressiva = False
    if acao == "COMPRAR" and score_valorizacao >= 8 and probabilidade_esgotar >= 70:
        compra_agressiva = True
        razao += " | Compra agressiva recomendada (alta valorização + alto risco de esgotamento)"
    
    item["acao_final"] = acao
    item["razao"] = razao
    item["thresholds_usados"] = thresholds
    item["compra_agressiva"] = compra_agressiva
    
    return item


def processar_decisoes(eventos_auditados: list[dict]) -> list[dict]:
    """Processa decisões para todos os eventos."""
    resultados = []
    
    for item in eventos_auditados:
        resultado = tomar_decisao(item)
        resultados.append(resultado)
    
    return resultados
