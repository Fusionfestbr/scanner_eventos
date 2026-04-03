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
from core.learning import salvar_evento_no_historico, obter_thresholds, verificar_performance
from core.ranking import gerar_ranking, salvar_ranking
from core.data_quality import (
    filtrar_eventos_validos,
    calcular_score,
    verificar_qualidade,
    checar_fallback,
    salvar_rejeitados
)
from core.notifier import verificar_e_enviar_alerta
from config import FALLBACK_ENABLED
from core.predictor import processar_previsoes
from core.executor import processar_planos_acao
from core.arbitrage import processar_arbitragem
from agents.scraper import buscar_precos_revenda


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


def executar_pipeline() -> tuple[int, int, int, int, int]:
    """
    Executa o pipeline completo.
    
    Returns:
        Tupla com (qtd_coletados, qtd_validos_quality, qtd_analisados, qtd_finais, qualidade_score)
    """
    log("=== INICIANDO PIPELINE DE EVENTOS ===")
    
    thresholds = obter_thresholds()
    log(f"   -> Thresholds carregados: nota>={thresholds['min_nota_comprar']}, confianca>={thresholds['min_confianca']}")
    
    perf = verificar_performance()
    if perf.get("status") == "alerta":
        log(f"   [ALERTA] Performance caiu: {perf.get('mensagem')}")
    
    log("1/7 - Coletando eventos...")
    eventos_coletados = coletar_eventos()
    qtd_coletados = len(eventos_coletados)
    log(f"   -> Coletados {qtd_coletados} eventos")
    
    raw_path = os.path.join(os.path.dirname(__file__), "..", "data", "raw.json")
    salvar_json(eventos_coletados, raw_path)
    log(f"   -> Salvo em {raw_path}")
    
    log("2/7 - Verificando qualidade dos dados...")
    eventos_validos_qc, eventos_rejeitados = filtrar_eventos_validos(eventos_coletados)
    qtd_validos_qc = len(eventos_validos_qc)
    
    score = calcular_score(qtd_validos_qc, qtd_coletados)
    log(f"   -> {qtd_validos_qc}/{qtd_coletados} válidos ({score['score']}%)")
    
    if eventos_rejeitados:
        salvar_rejeitados(eventos_rejeitados)
        log(f"   -> {len(eventos_rejeitados)} eventos rejeitados salvos em rejected.json")
    
    qualidade_aceitavel, msg_qualidade = verificar_qualidade(qtd_validos_qc, qtd_coletados)
    print(f"   {msg_qualidade}")
    
    if not qualidade_aceitavel:
        print(f"   [ALERTA] Qualidade abaixo do mínimo! Processando apenas {qtd_validos_qc} eventos.")
    
    log("3/7 - Carregando dados para validação...")
    log(f"   -> {qtd_validos_qc} eventos para validar")
    
    log("4/7 - Validando eventos...")
    eventos_validados = validar_eventos(eventos_validos_qc)
    qtd_validados = len(eventos_validados)
    log(f"   -> {qtd_validados} eventos válidos")
    
    clean_path = os.path.join(os.path.dirname(__file__), "..", "data", "clean.json")
    salvar_json(eventos_validados, clean_path)
    log(f"   -> Salvo em {clean_path}")
    
    log("5/7 - Analisando eventos com IA...")
    eventos_analisados = analisar_eventos(eventos_validados)
    qtd_analisados = len(eventos_analisados)
    log(f"   -> {qtd_analisados} eventos analisados")
    
    analyzed_path = os.path.join(os.path.dirname(__file__), "..", "data", "analyzed.json")
    salvar_json(eventos_analisados, analyzed_path)
    log(f"   -> Salvo em {analyzed_path}")
    
    log("6/7 - Auditando eventos...")
    eventos_auditados = auditar_eventos(eventos_analisados)
    log(f"   -> {len(eventos_auditados)} eventos auditados")
    
    log("7/7 - Tomando decisões...")
    eventos_finais = processar_decisoes(eventos_auditados)
    qtd_finais = len(eventos_finais)
    log(f"   -> {qtd_finais} decisões tomadas")
    
    log("Gerando previsões de valorização...")
    eventos_finais = processar_previsoes(eventos_finais)
    log(f"   -> Previsões geradas para {len(eventos_finais)} eventos")
    
    log("Gerando planos de ação...")
    eventos_finais = processar_planos_acao(eventos_finais)
    log(f"   -> Planos de ação gerados para {len(eventos_finais)} eventos")
    
    log("Detectando oportunidades de arbitragem...")
    eventos_com_arbitragem = []
    for item in eventos_finais:
        evento_com_arbit = item.copy()
        
        if item.get("acao_final") == "COMPRAR":
            nome_evento = item.get("evento", {}).get("nome", "")
            if nome_evento:
                precos_revenda = buscar_precos_revenda(nome_evento)
                evento_original = item.get("evento", {})
                preco_original = evento_original.get("preco", 0)
                
                if preco_original > 0:
                    precos_revenda.insert(0, {"plataforma": evento_original.get("fonte", "original"), "preco": preco_original})
                
                evento_com_arbit["precos_encontrados"] = precos_revenda
                evento_com_arbit["evento"]["precos_encontrados"] = precos_revenda
        
        eventos_com_arbitragem.append(evento_com_arbit)
    
    eventos_finais = processar_arbitragem(eventos_com_arbitragem, apenas_comprar=True)
    log(f"   -> Arbitragem detectada para {len(eventos_finais)} eventos")
    
    final_path = os.path.join(os.path.dirname(__file__), "..", "data", "final.json")
    salvar_json(eventos_finais, final_path)
    log(f"   -> Salvo em {final_path}")
    
    log("Gerando ranking...")
    ranking = gerar_ranking(eventos_finais)
    salvar_ranking(ranking)
    log(f"   -> Ranking gerado com {len(ranking)} eventos")
    
    log("Salvando no histórico...")
    for item in eventos_finais:
        evento = item.get("evento", {})
        analise = item.get("analise", {})
        auditoria = item.get("auditoria", {})
        acao = item.get("acao_final", "IGNORAR")
        plano_acao = item.get("plano_acao", {})
        arbitragem = item.get("arbitragem", {})
        salvar_evento_no_historico(evento, analise, auditoria, acao)
        
        enviado = verificar_e_enviar_alerta(evento, analise, auditoria, acao, plano_acao, arbitragem)
        if enviado:
            log(f"   -> Alerta enviado para: {evento.get('nome', 'N/A')}")
    
    log(f"   -> {qtd_finais} eventos salvos no histórico")
    
    log("=== PIPELINE CONCLUÍDO ===")
    
    return qtd_coletados, qtd_validados, qtd_analisados, qtd_finais, score['score']
