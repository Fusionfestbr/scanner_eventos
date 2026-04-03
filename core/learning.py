"""
Módulo de aprendizado baseado em histórico.
Registra decisões passadas e evolve com base em acertos/erros.
"""
import json
import os
from datetime import datetime, timedelta
from typing import Optional

HISTORY_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "history.json")
RESULTADOS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "resultados_operacoes.json")

MOVING_AVG_WINDOW = 30
MIN_OPERACOES_FOR_LEARNING = 5

DEFAULT_THRESHOLDS = {
    "min_nota_comprar": 8.0,
    "min_confianca": 7.0,
    "estrategia": "conservativa"
}

ESTRATEGIAS = {
    "conservativa": {"min_nota": 8.5, "descricao": "Apenas eventos com nota alta"},
    "moderada": {"min_nota": 7.5, "descricao": "Eventos com nota média-alta"},
    "arriscada": {"min_nota": 6.5, "descricao": "Eventos com nota moderada"}
}


def carregar_historico() -> list:
    """Carrega histórico do arquivo JSON."""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, IOError):
        return []


def salvar_historico(historico: list) -> None:
    """Salva histórico no arquivo JSON."""
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(historico, f, ensure_ascii=False, indent=2)


def carregar_resultados() -> list:
    """Carrega resultados de operações do arquivo JSON."""
    if not os.path.exists(RESULTADOS_FILE):
        return []
    try:
        with open(RESULTADOS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, IOError):
        return []


def salvar_resultados(resultados: list) -> None:
    """Salva resultados de operações no arquivo JSON."""
    os.makedirs(os.path.dirname(RESULTADOS_FILE), exist_ok=True)
    with open(RESULTADOS_FILE, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)


def gerar_id_evento(evento: dict) -> str:
    """Gera ID único para o evento."""
    nome = evento.get("nome", "")
    data = evento.get("data", "")
    return f"{nome}_{data}".replace(" ", "_")


def registrar_resultado(nome_evento: str, data: str, resultado: str) -> bool:
    """
    Registra resultado real de um evento.
    
    Args:
        nome_evento: Nome do evento
        data: Data do evento
        resultado: "valorizou" ou "nao_valorizou"
    
    Returns:
        True se registrado com sucesso
    """
    historico = carregar_historico()
    
    for item in historico:
        if item.get("evento") == nome_evento and item.get("data") == data:
            item["resultado_real"] = resultado
            item["data_registro"] = datetime.now().isoformat()
            salvar_historico(historico)
            return True
    
    return False


def registrar_operacao(
    nome_evento: str,
    data_evento: str,
    artista: str,
    preco_compra: float,
    preco_venda: float,
    data_compra: str,
    data_venda: str,
    fonte_compra: str = "",
    fonte_venda: str = "",
    nota_decisao: float = 0,
    estrategia: str = "conservativa"
) -> bool:
    """
    Registra uma operação de compra/venda concretizada.
    
    Args:
        nome_evento: Nome do evento
        data_evento: Data do evento
        artista: Artista do evento
        preco_compra: Preço pago pelo ingresso
        preco_venda: Preço recebido pela venda
        data_compra: Data da compra (YYYY-MM-DD)
        data_venda: Data da venda (YYYY-MM-DD)
        fonte_compra: Site onde comprou
        fonte_venda: Site onde vendeu
        nota_decisao: Nota que levou à decisão de compra
        estrategia: Estratégia usada (conservativa/moderada/arriscada)
    
    Returns:
        True se registrado com sucesso
    """
    lucro = preco_venda - preco_compra
    lucro_percentual = (lucro / preco_compra * 100) if preco_compra > 0 else 0
    
    try:
        data_compra_dt = datetime.strptime(data_compra, "%Y-%m-%d")
        data_venda_dt = datetime.strptime(data_venda, "%Y-%m-%d")
        tempo_venda = (data_venda_dt - data_compra_dt).days
    except:
        tempo_venda = 0
    
    resultado = "sucesso" if lucro > 0 else "fracasso"
    
    operacao = {
        "evento_id": f"{nome_evento}_{data_evento}".replace(" ", "_"),
        "nome_evento": nome_evento,
        "artista": artista,
        "data_evento": data_evento,
        "data_compra": data_compra,
        "data_venda": data_venda,
        "preco_compra": round(preco_compra, 2),
        "preco_venda": round(preco_venda, 2),
        "lucro": round(lucro, 2),
        "lucro_percentual": round(lucro_percentual, 1),
        "tempo_venda_dias": tempo_venda,
        "nota_decisao": nota_decisao,
        "estrategia": estrategia,
        "resultado": resultado,
        "fonte_compra": fonte_compra,
        "fonte_venda": fonte_venda,
        "data_registro": datetime.now().isoformat()
    }
    
    resultados = carregar_resultados()
    resultados.append(operacao)
    salvar_resultados(resultados)
    
    return True


def calcular_metricas_financeiras() -> dict:
    """
    Calcula métricas financeiras das operações.
    
    Returns:
        Dicionário com métricas financeiras
    """
    resultados = carregar_resultados()
    
    if not resultados:
        return {
            "total_operacoes": 0,
            "sem_dados": True,
            "lucro_medio": 0,
            "roi_medio": 0,
            "taxa_sucesso": 0,
            "tempo_medio_venda": 0
        }
    
    total = len(resultados)
    lucro_total = sum(r.get("lucro", 0) for r in resultados)
    investimento_total = sum(r.get("preco_compra", 0) for r in resultados)
    lucros = [r.get("lucro_percentual", 0) for r in resultados]
    tempos = [r.get("tempo_venda_dias", 0) for r in resultados]
    
    sucesso = sum(1 for r in resultados if r.get("resultado") == "sucesso")
    fracasso = total - sucesso
    
    roi_medio = (lucro_total / investimento_total * 100) if investimento_total > 0 else 0
    
    return {
        "total_operacoes": total,
        "lucro_total": round(lucro_total, 2),
        "lucro_medio": round(sum(lucros) / total, 1) if total > 0 else 0,
        "roi_medio": round(roi_medio, 1),
        "taxa_sucesso": round(sucesso / total * 100, 1) if total > 0 else 0,
        "tempo_medio_venda": round(sum(tempos) / total, 1) if total > 0 else 0,
        "operacoes_sucesso": sucesso,
        "operacoes_fracasso": fracasso,
        "investimento_total": round(investimento_total, 2)
    }


def calcular_metricas_moving_average(window: int = MOVING_AVG_WINDOW) -> dict:
    """
    Calcula métricas usando janela móvel (últimas N operações).
    
    Args:
        window: Número de operações para média móvel
    
    Returns:
        Métricas baseadas em média móvel
    """
    resultados = carregar_resultados()
    
    if len(resultados) < MIN_OPERACOES_FOR_LEARNING:
        return {
            "tem_dados_suficientes": False,
            "operacoesnecessarias": MIN_OPERACOES_FOR_LEARNING
        }
    
    ultimos = resultados[-window:]
    total = len(ultimos)
    
    lucro_medio = sum(r.get("lucro_percentual", 0) for r in ultimos) / total
    sucesso = sum(1 for r in ultimos if r.get("resultado") == "sucesso")
    tempo_medio = sum(r.get("tempo_venda_dias", 0) for r in ultimos) / total
    
    return {
        "tem_dados_suficientes": True,
        "janela_usada": total,
        "lucro_medio_moving_avg": round(lucro_medio, 1),
        "taxa_sucesso_moving_avg": round(sucesso / total * 100, 1),
        "tempo_medio_venda_moving_avg": round(tempo_medio, 1),
        "ultima_atualizacao": resultados[-1].get("data_registro", "")
    }


def analisar_padroes() -> dict:
    """
    Analisa padrões de sucesso e falha.
    
    Returns:
        Dicionário com padrões identificados
    """
    resultados = carregar_resultados()
    
    if len(resultados) < MIN_OPERACOES_FOR_LEARNING:
        return {"sem_dados": True}
    
    por_estrategia = {}
    por_nota = {}
    
    for r in resultados:
        est = r.get("estrategia", "desconhecida")
        if est not in por_estrategia:
            por_estrategia[est] = {"total": 0, "sucesso": 0, "lucros": []}
        por_estrategia[est]["total"] += 1
        if r.get("resultado") == "sucesso":
            por_estrategia[est]["sucesso"] += 1
        por_estrategia[est]["lucros"].append(r.get("lucro_percentual", 0))
        
        nota = r.get("nota_decisao", 0)
        if nota > 0:
            nota_range = int(nota)
            if nota_range not in por_nota:
                por_nota[nota_range] = {"total": 0, "sucesso": 0}
            por_nota[nota_range]["total"] += 1
            if r.get("resultado") == "sucesso":
                por_nota[nota_range]["sucesso"] += 1
    
    melhores_estrategias = []
    for est, dados in por_estrategia.items():
        if dados["total"] >= 2:
            taxa = dados["sucesso"] / dados["total"] * 100
            lucro_medio = sum(dados["lucros"]) / len(dados["lucros"])
            melhores_estrategias.append({
                "estrategia": est,
                "taxa_sucesso": round(taxa, 1),
                "lucro_medio": round(lucro_medio, 1),
                "total": dados["total"]
            })
    
    melhores_estrategias.sort(key=lambda x: x["taxa_sucesso"], reverse=True)
    
    melhores_notas = []
    for nota, dados in sorted(por_nota.items()):
        if dados["total"] >= 2:
            taxa = dados["sucesso"] / dados["total"] * 100
            melhores_notas.append({
                "nota_range": nota,
                "taxa_sucesso": round(taxa, 1),
                "total": dados["total"]
            })
    
    melhores_notas.sort(key=lambda x: x["taxa_sucesso"], reverse=True)
    
    return {
        "por_estrategia": melhores_estrategias,
        "por_nota": melhores_notas,
        "melhor_estrategia": melhores_estrategias[0] if melhores_estrategias else None,
        "melhor_nota_range": melhores_notas[0] if melhores_notas else None
    }


def ajustar_parametros_com_moving_average() -> dict:
    """
    Ajusta thresholds usando média móvel (evita overfitting).
    
    Returns:
        Novos thresholds ajustados
    """
    metricas = calcular_metricas_moving_average()
    
    if not metricas.get("tem_dados_suficientes"):
        return DEFAULT_THRESHOLDS.copy()
    
    taxa_sucesso = metricas.get("taxa_sucesso_moving_avg", 0)
    lucro_medio = metricas.get("lucro_medio_moving_avg", 0)
    tempo_medio = metricas.get("tempo_medio_venda_moving_avg", 0)
    
    min_nota = DEFAULT_THRESHOLDS["min_nota_comprar"]
    estrategia = DEFAULT_THRESHOLDS["estrategia"]
    
    if taxa_sucesso < 40:
        min_nota += 0.5
    elif taxa_sucesso < 50:
        min_nota += 0.3
    
    if lucro_medio < 10:
        min_nota += 0.3
    elif lucro_medio > 30:
        min_nota = max(7.0, min_nota - 0.2)
    
    if tempo_medio > 30:
        min_nota += 0.2
    
    min_nota = min(10.0, min_nota)
    min_nota = max(6.0, min_nota)
    
    padroes = analisar_padroes()
    if padroes.get("melhor_estrategia"):
        estrategia = padroes["melhor_estrategia"]["estrategia"]
    
    return {
        "min_nota_comprar": round(min_nota, 1),
        "min_confianca": DEFAULT_THRESHOLDS["min_confianca"],
        "estrategia": estrategia
    }


def obter_thresholds() -> dict:
    """
    Retorna thresholds (ajustados ou padrão).
    
    Returns:
        Dicionário com thresholds
    """
    try:
        return ajustar_parametros_com_moving_average()
    except Exception:
        return DEFAULT_THRESHOLDS.copy()


def verificar_performance() -> dict:
    """
    Verifica se performance caiu significativamente.
    
    Returns:
        Dicionário com resultado da verificação
    """
    resultados = carregar_resultados()
    
    if len(resultados) < 10:
        return {"status": "insuficiente", "mensagem": "Dados insuficientes para análise"}
    
    window = MOVING_AVG_WINDOW
    if len(resultados) < window * 2:
        return {"status": "insuficiente", "mensagem": "Necessário mais histórico"}
    
    anterior = resultados[-window * 2:-window]
    atual = resultados[-window:]
    
    taxa_anterior = sum(1 for r in anterior if r.get("resultado") == "sucesso") / len(anterior) * 100
    taxa_atual = sum(1 for r in atual if r.get("resultado") == "sucesso") / len(atual) * 100
    
    diferenca = taxa_anterior - taxa_atual
    
    if diferenca > 20:
        return {
            "status": "alerta",
            "mensagem": f"Performance caiu {round(diferenca, 1)}%",
            "taxa_anterior": round(taxa_anterior, 1),
            "taxa_atual": round(taxa_atual, 1),
            "acao": "revisar_parametros"
        }
    
    return {
        "status": "ok",
        "mensagem": "Performance estável",
        "taxa_anterior": round(taxa_anterior, 1),
        "taxa_atual": round(taxa_atual, 1)
    }


def obter_estrategia_otima() -> dict:
    """
    Determina a melhor estratégia baseada em dados históricos.
    
    Returns:
        Dicionário com estratégia recomendada
    """
    padroes = analisar_padroes()
    
    if padroes.get("sem_dados"):
        return {
            "estrategia": "conservativa",
            "min_nota": 8.0,
            "motivo": "Sem dados suficientes, usando padrão"
        }
    
    if padroes.get("melhor_estrategia"):
        melhor = padroes["melhor_estrategia"]
        estrategia_info = ESTRATEGIAS.get(melhor["estrategia"], {})
        return {
            "estrategia": melhor["estrategia"],
            "min_nota": estrategia_info.get("min_nota", 8.0),
            "taxa_sucesso": melhor["taxa_sucesso"],
            "lucro_medio": melhor["lucro_medio"],
            "motivo": f"Baseado em {melhor['total']} operações"
        }
    
    return {
        "estrategia": "conservativa",
        "min_nota": 8.0,
        "motivo": "Padrão"
    }


def calcular_metricas() -> dict:
    """
    Calcula métricas do histórico.
    
    Returns:
        Dicionário com métricas
    """
    historico = carregar_historico()
    
    if not historico:
        return {
            "total_eventos": 0,
            "taxa_acerto_geral": 0,
            "taxa_acerto_comprar": 0,
            "taxa_acerto_monitorar": 0,
            "eventos_falharam": [],
            "eventos_sucesso": []
        }
    
    eventos_com_resultado = [h for h in historico if h.get("resultado_real")]
    
    if not eventos_com_resultado:
        return {
            "total_eventos": len(historico),
            "eventos_com_resultado": 0,
            "sem_dados": True
        }
    
    comprar = [h for h in eventos_com_resultado if h.get("acao_final") == "COMPRAR"]
    monitorar = [h for h in eventos_com_resultado if h.get("acao_final") == "MONITORAR"]
    
    def calcular_taxa(lista):
        if not lista:
            return 0
        acertos = sum(1 for h in lista if h.get("resultado_real") == "valorizou")
        return round(acertos / len(lista) * 100, 1)
    
    comprar_sucesso = [h for h in comprar if h.get("resultado_real") == "valorizou"]
    comprar_falha = [h for h in comprar if h.get("resultado_real") == "nao_valorizou"]
    monitorar_sucesso = [h for h in monitorar if h.get("resultado_real") == "valorizou"]
    monitorar_falha = [h for h in monitorar if h.get("resultado_real") == "nao_valorizou"]
    
    todos_acertos = calcular_taxa(eventos_com_resultado)
    
    return {
        "total_eventos": len(historico),
        "eventos_com_resultado": len(eventos_com_resultado),
        "taxa_acerto_geral": todos_acertos,
        "taxa_acerto_comprar": calcular_taxa(comprar),
        "taxa_acerto_monitorar": calcular_taxa(monitorar),
        "comprar_total": len(comprar),
        "comprar_sucesso": len(comprar_sucesso),
        "comprar_falha": len(comprar_falha),
        "monitorar_total": len(monitorar),
        "monitorar_sucesso": len(monitorar_sucesso),
        "monitorar_falha": len(monitorar_falha),
        "eventos_falharam": [h.get("evento") for h in comprar_falha],
        "eventos_sucesso": [h.get("evento") for h in comprar_sucesso]
    }


def ajustar_pesos() -> dict:
    """
    Ajusta thresholds baseado no histórico (legado).
    
    Returns:
        Novos thresholds ajustados
    """
    metricas = calcular_metricas()
    
    if metricas.get("sem_dados"):
        return DEFAULT_THRESHOLDS.copy()
    
    taxa_geral = metricas.get("taxa_acerto_geral", 0)
    taxa_comprar = metricas.get("taxa_acerto_comprar", 0)
    taxa_monitorar = metricas.get("taxa_acerto_monitorar", 0)
    
    min_nota = DEFAULT_THRESHOLDS["min_nota_comprar"]
    min_confianca = DEFAULT_THRESHOLDS["min_confianca"]
    
    if taxa_comprar < 50 and metricas.get("comprar_falha", 0) >= 2:
        min_nota += 0.5
    
    if taxa_comprar > 70:
        min_nota = max(7.0, min_nota - 0.3)
    
    if taxa_monitorar > 70:
        min_nota = max(7.0, min_nota - 0.2)
    
    min_nota = min(10.0, min_nota)
    min_confianca = min(10.0, min_confianca)
    
    return {
        "min_nota_comprar": min_nota,
        "min_confianca": min_confianca
    }


def salvar_evento_no_historico(evento: dict, analise: dict, auditoria: dict, acao: str) -> None:
    """Salva evento no histórico após decisão."""
    historico = carregar_historico()
    
    item = {
        "id": gerar_id_evento(evento),
        "evento": evento.get("nome", ""),
        "artista": evento.get("artista", ""),
        "data": evento.get("data", ""),
        "cidade": evento.get("cidade", ""),
        "nota_final": analise.get("nota_final", 0),
        "decisao": auditoria.get("decisao", ""),
        "confianca": auditoria.get("confianca", 0),
        "acao_final": acao,
        "resultado_real": None,
        "data_decisao": datetime.now().isoformat(),
        "data_registro": datetime.now().isoformat()
    }
    
    duplicado = any(
        h.get("id") == item["id"] for h in historico
    )
    
    if not duplicado:
        historico.append(item)
        salvar_historico(historico)


def mostrar_historico(resumido: bool = True) -> None:
    """Mostra histórico no terminal."""
    historico = carregar_historico()
    
    if not historico:
        print("  Histórico vazio.")
        return
    
    print(f"\n  Total de eventos: {len(historico)}")
    
    if resumido:
        print("\n  Últimos 5 eventos:")
        for item in historico[-5:]:
            nome = item.get("evento", "N/A")
            acao = item.get("acao_final", "N/A")
            resultado = item.get("resultado_real", "PENDENTE")
            print(f"    - {nome}: {acao} ({resultado})")
    else:
        print("\n  Histórico completo:")
        for item in historico:
            nome = item.get("evento", "N/A")
            nota = item.get("nota_final", 0)
            acao = item.get("acao_final", "N/A")
            resultado = item.get("resultado_real", "PENDENTE")
            print(f"    - {nome} | Nota: {nota} | Ação: {acao} | Resultado: {resultado}")


def mostrar_resultados_operacoes(resumido: bool = True) -> None:
    """Mostra resultados de operações no terminal."""
    resultados = carregar_resultados()
    
    if not resultados:
        print("\n  Nenhuma operação registrada.")
        return
    
    metricas = calcular_metricas_financeiras()
    print(f"\n  === MÉTRICAS FINANCEIRAS ===")
    print(f"  Total de operações: {metricas['total_operacoes']}")
    print(f"  Lucro total: R$ {metricas['lucro_total']:.2f}")
    print(f"  Lucro médio: {metricas['lucro_medio']:.1f}%")
    print(f"  ROI médio: {metricas['roi_medio']:.1f}%")
    print(f"  Taxa de sucesso: {metricas['taxa_sucesso']:.1f}%")
    print(f"  Tempo médio venda: {metricas['tempo_medio_venda']:.1f} dias")
    
    if resumido:
        print("\n  Últimas 5 operações:")
        for item in resultados[-5:]:
            nome = item.get("nome_evento", "N/A")
            lucro = item.get("lucro", 0)
            resultado = item.get("resultado", "N/A")
            print(f"    - {nome[:40]}: R$ {lucro:.2f} ({resultado})")


def carregar_historico() -> list:
    """Carrega histórico do arquivo JSON."""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, IOError):
        return []


def salvar_historico(historico: list) -> None:
    """Salva histórico no arquivo JSON."""
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(historico, f, ensure_ascii=False, indent=2)


def gerar_id_evento(evento: dict) -> str:
    """Gera ID único para o evento."""
    nome = evento.get("nome", "")
    data = evento.get("data", "")
    return f"{nome}_{data}".replace(" ", "_")


def registrar_resultado(nome_evento: str, data: str, resultado: str) -> bool:
    """
    Registra resultado real de um evento.
    
    Args:
        nome_evento: Nome do evento
        data: Data do evento
        resultado: "valorizou" ou "nao_valorizou"
    
    Returns:
        True se registrado com sucesso
    """
    historico = carregar_historico()
    
    for item in historico:
        if item.get("evento") == nome_evento and item.get("data") == data:
            item["resultado_real"] = resultado
            item["data_registro"] = datetime.now().isoformat()
            salvar_historico(historico)
            return True
    
    return False


def calcular_metricas() -> dict:
    """
    Calcula métricas do histórico.
    
    Returns:
        Dicionário com métricas
    """
    historico = carregar_historico()
    
    if not historico:
        return {
            "total_eventos": 0,
            "taxa_acerto_geral": 0,
            "taxa_acerto_comprar": 0,
            "taxa_acerto_monitorar": 0,
            "eventos_falharam": [],
            "eventos_sucesso": []
        }
    
    eventos_com_resultado = [h for h in historico if h.get("resultado_real")]
    
    if not eventos_com_resultado:
        return {
            "total_eventos": len(historico),
            "eventos_com_resultado": 0,
            "sem_dados": True
        }
    
    comprar = [h for h in eventos_com_resultado if h.get("acao_final") == "COMPRAR"]
    monitorar = [h for h in eventos_com_resultado if h.get("acao_final") == "MONITORAR"]
    
    def calcular_taxa(lista):
        if not lista:
            return 0
        acertos = sum(1 for h in lista if h.get("resultado_real") == "valorizou")
        return round(acertos / len(lista) * 100, 1)
    
    comprar_sucesso = [h for h in comprar if h.get("resultado_real") == "valorizou"]
    comprar_falha = [h for h in comprar if h.get("resultado_real") == "nao_valorizou"]
    monitorar_sucesso = [h for h in monitorar if h.get("resultado_real") == "valorizou"]
    monitorar_falha = [h for h in monitorar if h.get("resultado_real") == "nao_valorizou"]
    
    todos_acertos = calcular_taxa(eventos_com_resultado)
    
    return {
        "total_eventos": len(historico),
        "eventos_com_resultado": len(eventos_com_resultado),
        "taxa_acerto_geral": todos_acertos,
        "taxa_acerto_comprar": calcular_taxa(comprar),
        "taxa_acerto_monitorar": calcular_taxa(monitorar),
        "comprar_total": len(comprar),
        "comprar_sucesso": len(comprar_sucesso),
        "comprar_falha": len(comprar_falha),
        "monitorar_total": len(monitorar),
        "monitorar_sucesso": len(monitorar_sucesso),
        "monitorar_falha": len(monitorar_falha),
        "eventos_falharam": [h.get("evento") for h in comprar_falha],
        "eventos_sucesso": [h.get("evento") for h in comprar_sucesso]
    }


def ajustar_pesos() -> dict:
    """
    Ajusta thresholds baseado no histórico.
    
    Returns:
        Novos thresholds ajustados
    """
    metricas = calcular_metricas()
    
    if metricas.get("sem_dados"):
        return DEFAULT_THRESHOLDS.copy()
    
    taxa_geral = metricas.get("taxa_acerto_geral", 0)
    taxa_comprar = metricas.get("taxa_acerto_comprar", 0)
    taxa_monitorar = metricas.get("taxa_acerto_monitorar", 0)
    
    min_nota = DEFAULT_THRESHOLDS["min_nota_comprar"]
    min_confianca = DEFAULT_THRESHOLDS["min_confianca"]
    
    if taxa_comprar < 50 and metricas.get("comprar_falha", 0) >= 2:
        min_nota += 0.5
    
    if taxa_comprar > 70:
        min_nota = max(7.0, min_nota - 0.3)
    
    if taxa_monitorar > 70:
        min_nota = max(7.0, min_nota - 0.2)
    
    min_nota = min(10.0, min_nota)
    min_confianca = min(10.0, min_confianca)
    
    return {
        "min_nota_comprar": min_nota,
        "min_confianca": min_confianca
    }


def obter_thresholds() -> dict:
    """
    Retorna thresholds (ajustados ou padrão).
    
    Returns:
        Dicionário com thresholds
    """
    try:
        return ajustar_pesos()
    except Exception:
        return DEFAULT_THRESHOLDS.copy()


def salvar_evento_no_historico(evento: dict, analise: dict, auditoria: dict, acao: str) -> None:
    """Salva evento no histórico após decisão."""
    historico = carregar_historico()
    
    item = {
        "id": gerar_id_evento(evento),
        "evento": evento.get("nome", ""),
        "artista": evento.get("artista", ""),
        "data": evento.get("data", ""),
        "cidade": evento.get("cidade", ""),
        "nota_final": analise.get("nota_final", 0),
        "decisao": auditoria.get("decisao", ""),
        "confianca": auditoria.get("confianca", 0),
        "acao_final": acao,
        "resultado_real": None,
        "data_decisao": datetime.now().isoformat(),
        "data_registro": datetime.now().isoformat()
    }
    
    duplicado = any(
        h.get("id") == item["id"] for h in historico
    )
    
    if not duplicado:
        historico.append(item)
        salvar_historico(historico)


def mostrar_historico(resumido: bool = True) -> None:
    """Mostra histórico no terminal."""
    historico = carregar_historico()
    
    if not historico:
        print("  Histórico vazio.")
        return
    
    print(f"\n  Total de eventos: {len(historico)}")
    
    if resumido:
        print("\n  Últimos 5 eventos:")
        for item in historico[-5:]:
            nome = item.get("evento", "N/A")
            acao = item.get("acao_final", "N/A")
            resultado = item.get("resultado_real", "PENDENTE")
            print(f"    - {nome}: {acao} ({resultado})")
    else:
        print("\n  Histórico completo:")
        for item in historico:
            nome = item.get("evento", "N/A")
            nota = item.get("nota_final", 0)
            acao = item.get("acao_final", "N/A")
            resultado = item.get("resultado_real", "PENDENTE")
            print(f"    - {nome} | Nota: {nota} | Ação: {acao} | Resultado: {resultado}")
