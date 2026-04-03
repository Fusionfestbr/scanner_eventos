"""
Orquestrador do pipeline de eventos.
Coordena o fluxo entre coletor, validador e persistência.
"""
import json
import os
from datetime import datetime

from agents.coletor import coletar_eventos
from agents.validador import validar_eventos
from agents.analista import analisar_eventos
from agents.auditor import auditar_eventos
from core.decision import processar_decisoes
from core.learning import salvar_evento_no_historico


def log(msg: str) -> None:
    """Log simples para terminal."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")


def salvar_json(data: list, filepath: str) -> None:
    """Salva dados em arquivo JSON."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def carregar_json(filepath: str) -> list:
    """Carrega dados de arquivo JSON."""
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def executar_pipeline() -> tuple[int, int, int, int]:
    """
    Executa o pipeline completo.
    
    Returns:
        Tupla com (qtd_coletados, qtd_validados, qtd_analisados, qtd_finais)
    """
    log("=== INICIANDO PIPELINE DE EVENTOS ===")
    
    log("1/6 - Coletando eventos...")
    eventos_coletados = coletar_eventos()
    qtd_coletados = len(eventos_coletados)
    log(f"   -> Coletados {qtd_coletados} eventos")
    
    raw_path = os.path.join(os.path.dirname(__file__), "..", "data", "raw.json")
    salvar_json(eventos_coletados, raw_path)
    log(f"   -> Salvo em {raw_path}")
    
    log("2/6 - Carregando dados brutos...")
    eventos_brutos = carregar_json(raw_path)
    log(f"   -> Carregados {len(eventos_brutos)} eventos")
    
    log("3/6 - Validando eventos...")
    eventos_validados = validar_eventos(eventos_brutos)
    qtd_validados = len(eventos_validados)
    log(f"   -> {qtd_validados} eventos válidos")
    
    clean_path = os.path.join(os.path.dirname(__file__), "..", "data", "clean.json")
    salvar_json(eventos_validados, clean_path)
    log(f"   -> Salvo em {clean_path}")
    
    log("4/6 - Analisando eventos com IA...")
    eventos_analisados = analisar_eventos(eventos_validados)
    qtd_analisados = len(eventos_analisados)
    log(f"   -> {qtd_analisados} eventos analisados")
    
    analyzed_path = os.path.join(os.path.dirname(__file__), "..", "data", "analyzed.json")
    salvar_json(eventos_analisados, analyzed_path)
    log(f"   -> Salvo em {analyzed_path}")
    
    log("5/6 - Auditando eventos...")
    eventos_auditados = auditar_eventos(eventos_analisados)
    log(f"   -> {len(eventos_auditados)} eventos auditados")
    
    log("6/6 - Tomando decisões...")
    eventos_finais = processar_decisoes(eventos_auditados)
    qtd_finais = len(eventos_finais)
    log(f"   -> {qtd_finais} decisões tomadas")
    
    final_path = os.path.join(os.path.dirname(__file__), "..", "data", "final.json")
    salvar_json(eventos_finais, final_path)
    log(f"   -> Salvo em {final_path}")
    
    log("Salvando no histórico...")
    for item in eventos_finais:
        evento = item.get("evento", {})
        analise = item.get("analise", {})
        auditoria = item.get("auditoria", {})
        acao = item.get("acao_final", "IGNORAR")
        salvar_evento_no_historico(evento, analise, auditoria, acao)
    log(f"   -> {qtd_finais} eventos salvos no histórico")
    
    log("=== PIPELINE CONCLUÍDO ===")
    
    return qtd_coletados, qtd_validados, qtd_analisados, qtd_finais