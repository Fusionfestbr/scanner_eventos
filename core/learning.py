"""
Módulo de aprendizado baseado em histórico.
Registra decisões passadas e evolve com base em acertos/erros.
"""
import json
import os
from datetime import datetime

HISTORY_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "history.json")

DEFAULT_THRESHOLDS = {
    "min_nota_comprar": 8.0,
    "min_confianca": 7.0
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
