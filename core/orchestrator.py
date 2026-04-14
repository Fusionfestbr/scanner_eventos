"""
Orquestrador do pipeline de eventos.
Coordena o fluxo entre coletor, validador e persistência.
"""
import json
import os
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.logger import logger
from utils.checkpoint import get_checkpoint, get_estado_pipeline

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
from config import FALLBACK_ENABLED, LLM_WORKERS
from core.predictor import processar_previsoes
from core.executor import processar_planos_acao
from core.arbitrage import processar_arbitragem
from agents.scraper import buscar_precos_revenda
from core.executor_real import gerar_execucao_real
from core.cache import (
    processar_com_cache,
    mesclar_resultados,
    adicionar_lote_ao_cache,
    get_cache_stats
)


PIPELINE_ETAPAS = [
    {"id": 1, "nome": "Coletando eventos", "status": "pendente", "tempo": "-", "icon": "fa-spider"},
    {"id": 2, "nome": "Verificando qualidade", "status": "pendente", "tempo": "-", "icon": "fa-clipboard-check"},
    {"id": 3, "nome": "Carregando para validação", "status": "pendente", "tempo": "-", "icon": "fa-database"},
    {"id": 4, "nome": "Validando eventos", "status": "pendente", "tempo": "-", "icon": "fa-check-double"},
    {"id": 5, "nome": "Analisando com IA", "status": "pendente", "tempo": "-", "icon": "fa-brain"},
    {"id": 6, "nome": "Auditando decisões", "status": "pendente", "tempo": "-", "icon": "fa-gavel"},
    {"id": 7, "nome": "Processando decisões", "status": "pendente", "tempo": "-", "icon": "fa-balance-scale"},
    {"id": 8, "nome": "Gerando previsões", "status": "pendente", "tempo": "-", "icon": "fa-chart-line"},
    {"id": 9, "nome": "Gerando planos de ação", "status": "pendente", "tempo": "-", "icon": "fa-tasks"},
    {"id": 10, "nome": "Detectando arbitragem", "status": "pendente", "tempo": "-", "icon": "fa-exchange-alt"},
    {"id": 11, "nome": "Buscando preços revenda", "status": "pendente", "tempo": "-", "icon": "fa-search-dollar"},
    {"id": 12, "nome": "Gerando execuções", "status": "pendente", "tempo": "-", "icon": "fa-play"},
    {"id": 13, "nome": "Gerando ranking", "status": "pendente", "tempo": "-", "icon": "fa-trophy"},
    {"id": 14, "nome": "Salvando histórico", "status": "pendente", "tempo": "-", "icon": "fa-save"},
    {"id": 15, "nome": "Enviando alertas", "status": "pendente", "tempo": "-", "icon": "fa-bell"},
]

_pipeline_status = {
    "ativo": False,
    "etapa_atual": "",
    "progresso_geral": 0,
    "etapas": [],
    "inicio": None,
    "ultima_atualizacao": None
}

def get_pipeline_status() -> dict:
    """Retorna o status atual do pipeline."""
    return _pipeline_status

def _iniciar_etapa(etapa_id: int, nome: str) -> float:
    """Marca uma etapa como em progresso e retorna timestamp."""
    global _pipeline_status
    _pipeline_status["ativo"] = True
    _pipeline_status["etapa_atual"] = nome
    _pipeline_status["progresso_geral"] = int((etapa_id / 15) * 100)
    _pipeline_status["ultima_atualizacao"] = datetime.now().isoformat()
    
    for etapa in _pipeline_status["etapas"]:
        if etapa["id"] == etapa_id:
            etapa["status"] = "em_progresso"
            break
    
    return time.time()

def _concluir_etapa(etapa_id: int, nome: str, tempo_inicio: float) -> None:
    """Marca uma etapa como concluída."""
    global _pipeline_status
    tempo_decorrido = time.time() - tempo_inicio
    tempo_str = f"{tempo_decorrido:.1f}s"
    
    for etapa in _pipeline_status["etapas"]:
        if etapa["id"] == etapa_id:
            etapa["status"] = "concluida"
            etapa["tempo"] = tempo_str
            etapa["icon"] = "fa-check"
            break
    
    _pipeline_status["ultima_atualizacao"] = datetime.now().isoformat()

def _iniciar_pipeline() -> None:
    """Inicia o tracking do pipeline."""
    global _pipeline_status
    _pipeline_status = {
        "ativo": True,
        "etapa_atual": "Iniciando...",
        "progresso_geral": 0,
        "etapas": [e.copy() for e in PIPELINE_ETAPAS],
        "inicio": datetime.now().isoformat(),
        "ultima_atualizacao": datetime.now().isoformat()
    }

def _concluir_pipeline() -> None:
    """Finaliza o tracking do pipeline."""
    global _pipeline_status
    _pipeline_status["ativo"] = False
    _pipeline_status["etapa_atual"] = "Concluído"
    _pipeline_status["progresso_geral"] = 100
    _pipeline_status["ultima_atualizacao"] = datetime.now().isoformat()


def log(msg: str) -> None:
    """Log simples para terminal e arquivo."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")
    logger.info(msg)


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


def executar_pipeline() -> tuple:
    """
    Executa o pipeline completo.
    
    Returns:
        Tupla com (qtd_coletados, qtd_validados, qtd_analisados, qtd_finais, qualidade_score, cache_stats)
    """
    checkpoint = get_checkpoint()
    estado = get_estado_pipeline()
    
    estado.iniciar()
    _iniciar_pipeline()
    log("=== INICIANDO PIPELINE DE EVENTOS ===")
    
    thresholds = obter_thresholds()
    log(f"   -> Thresholds carregados: nota>={thresholds['min_nota_comprar']}, confianca>={thresholds['min_confianca']}")
    
    perf = verificar_performance()
    if perf.get("status") == "alerta":
        log(f"   [ALERTA] Performance caiu: {perf.get('mensagem')}")
    
    # Etapa 1: Coletando eventos
    t = _iniciar_etapa(1, "Coletando eventos...")
    log("1/7 - Coletando eventos...")
    eventos_coletados = coletar_eventos()
    qtd_coletados = len(eventos_coletados)
    log(f"   -> Coletados {qtd_coletados} eventos")
    
    raw_path = os.path.join(os.path.dirname(__file__), "..", "data", "raw.json")
    salvar_json(eventos_coletados, raw_path)
    log(f"   -> Salvo em {raw_path}")
    
    checkpoint.salvar("coleta", {"qtd": qtd_coletados, "arquivo": raw_path})
    estado.etapa("coleta", 15)
    _concluir_etapa(1, "Coletando eventos", t)
    
    # Etapa 1.5: Verificando cache
    t = _iniciar_etapa(1, "Verificando cache...")
    log("   -> Verificando cache...")
    eventos_do_cache, eventos_para_processar, cache_stats = processar_com_cache(eventos_coletados)
    log(f"   -> Cache: {cache_stats['cache_hits']} hits, {cache_stats['cache_misses']} misses, {cache_stats['re_analises']} re-análises")
    log(f"   -> {len(eventos_do_cache)} eventos do cache, {len(eventos_para_processar)} para processar")
    _concluir_etapa(1, "Verificando cache", t)
    
    # Etapa 2: Verificando qualidade
    t = _iniciar_etapa(2, "Verificando qualidade...")
    log("2/7 - Verificando qualidade dos dados...")
    eventos_validos_qc, eventos_rejeitados = filtrar_eventos_validos(eventos_para_processar)
    qtd_validos_qc = len(eventos_validos_qc)
    
    score = calcular_score(qtd_validos_qc, len(eventos_para_processar))
    log(f"   -> {qtd_validos_qc}/{len(eventos_para_processar)} válidos ({score['score']}%)")
    
    if eventos_rejeitados:
        salvar_rejeitados(eventos_rejeitados)
        log(f"   -> {len(eventos_rejeitados)} eventos rejeitados salvos em rejected.json")
    
    qualidade_aceitavel, msg_qualidade = verificar_qualidade(qtd_validos_qc, len(eventos_para_processar))
    print(f"   {msg_qualidade}")
    
    if not qualidade_aceitavel:
        print(f"   [ALERTA] Qualidade abaixo do mínimo! Processando apenas {qtd_validos_qc} eventos.")
    _concluir_etapa(2, "Verificando qualidade", t)
    
    # Etapa 3: Carregando para validação
    t = _iniciar_etapa(3, "Carregando para validação...")
    log("3/7 - Carregando dados para validação...")
    log(f"   -> {qtd_validos_qc} eventos para validar")
    _concluir_etapa(3, "Carregando para validação", t)
    
    # Etapa 4: Validando eventos
    t = _iniciar_etapa(4, "Validando eventos...")
    log("4/7 - Validando eventos...")
    eventos_validados_novos = validar_eventos(eventos_validos_qc)
    qtd_validados = len(eventos_validados_novos)
    log(f"   -> {qtd_validados} eventos válidos")
    
    clean_path = os.path.join(os.path.dirname(__file__), "..", "data", "clean.json")
    salvar_json(eventos_validados_novos, clean_path)
    log(f"   -> Salvo em {clean_path}")
    _concluir_etapa(4, "Validando eventos", t)
    
    # Etapa 5: Analisando com IA (apenas eventos novos)
    t = _iniciar_etapa(5, "Analisando com IA...")
    log("5/7 - Analisando eventos com IA...")
    eventos_analisados = analisar_eventos(eventos_validados_novos)
    qtd_analisados = len(eventos_analisados)
    log(f"   -> {qtd_analisados} eventos analisados")
    
    analyzed_path = os.path.join(os.path.dirname(__file__), "..", "data", "analyzed.json")
    salvar_json(eventos_analisados, analyzed_path)
    log(f"   -> Salvo em {analyzed_path}")
    _concluir_etapa(5, "Analisando com IA", t)
    
    # Etapa 6: Auditando eventos
    t = _iniciar_etapa(6, "Auditando decisões...")
    log("6/7 - Auditando eventos...")
    eventos_auditados = auditar_eventos(eventos_analisados)
    log(f"   -> {len(eventos_auditados)} eventos auditados")
    _concluir_etapa(6, "Auditando decisões", t)
    
    # Etapa 7: Processando decisões
    t = _iniciar_etapa(7, "Processando decisões...")
    log("7/7 - Tomando decisões...")
    eventos_finais = processar_decisoes(eventos_auditados)
    qtd_finais = len(eventos_finais)
    log(f"   -> {qtd_finais} decisões tomadas")
    _concluir_etapa(7, "Processando decisões", t)
    
    # Etapa 8: Gerando previsões
    t = _iniciar_etapa(8, "Gerando previsões...")
    log("Gerando previsões de valorização...")
    eventos_finais = processar_previsoes(eventos_finais)
    log(f"   -> Previsões geradas para {len(eventos_finais)} eventos")
    _concluir_etapa(8, "Gerando previsões", t)
    
    # Etapa 9: Gerando planos de ação
    t = _iniciar_etapa(9, "Gerando planos de ação...")
    log("Gerando planos de ação...")
    eventos_finais = processar_planos_acao(eventos_finais)
    log(f"   -> Planos de ação gerados para {len(eventos_finais)} eventos")
    _concluir_etapa(9, "Gerando planos de ação", t)
    
    # Etapa 10: Detectando arbitragem
    t = _iniciar_etapa(10, "Detectando arbitragem...")
    log("Detectando oportunidades de arbitragem...")
    
    def buscar_precos_para_evento(item):
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
        return evento_com_arbit
    
    eventos_comprar = [i for i in eventos_finais if i.get("acao_final") == "COMPRAR"]
    if eventos_comprar:
        log(f"   -> Buscando precos de revenda para {len(eventos_comprar)} eventos...")
        with ThreadPoolExecutor(max_workers=min(4, len(eventos_comprar))) as executor:
            eventos_com_arbitragem = list(executor.map(buscar_precos_para_evento, eventos_comprar))
        idx_comprar = 0
        for i, item in enumerate(eventos_finais):
            if item.get("acao_final") == "COMPRAR":
                eventos_finais[i] = eventos_com_arbitragem[idx_comprar]
                idx_comprar += 1
            else:
                eventos_finais[i] = item.copy()
                eventos_finais[i]["precos_encontrados"] = []
    else:
        eventos_com_arbitragem = eventos_finais
    
    eventos_finais = processar_arbitragem(eventos_finais, apenas_comprar=True)
    log(f"   -> Arbitragem detectada para {len(eventos_finais)} eventos")
    _concluir_etapa(10, "Detectando arbitragem", t)
    
    # Etapa 11: Buscando preços de revenda
    t = _iniciar_etapa(11, "Buscando preços revenda...")
    log("Gerando execuções reais...")
    eventos_comprar = [i for i in eventos_finais if i.get("acao_final") == "COMPRAR"]
    count_exec = 0
    _concluir_etapa(11, "Buscando preços revenda", t)
    
    # Etapa 12: Gerando execuções
    t = _iniciar_etapa(12, "Gerando execuções...")
    
    def gerar_execucao_para_item(item):
        evento = item.get("evento", {})
        analise = item.get("analise", {})
        previsao = item.get("previsao", {})
        plano_acao = item.get("plano_acao", {})
        execucao = gerar_execucao_real(evento, analise, previsao, plano_acao)
        return item.get("evento", {}).get("nome", ""), execucao
    
    with ThreadPoolExecutor(max_workers=min(4, len(eventos_comprar))) as executor:
        futures = {executor.submit(gerar_execucao_para_item, item): item for item in eventos_comprar}
        for future in as_completed(futures):
            item = futures[future]
            nome_ev, execucao = future.result()
            item["execucao"] = execucao
            count_exec += 1
            log(f"   -> Execução {count_exec}/{len(eventos_comprar)}: {nome_ev[:50]}")
    
    final_path = os.path.join(os.path.dirname(__file__), "..", "data", "final.json")
    salvar_json(eventos_finais, final_path)
    log(f"   -> Salvo em {final_path}")
    _concluir_etapa(12, "Gerando execuções", t)
    
    # Mesclar eventos do cache com os processados
    log("   -> Mesclando eventos do cache...")
    eventos_finais = mesclar_resultados(eventos_do_cache, eventos_finais)
    log(f"   -> Total: {len(eventos_finais)} eventos ({len(eventos_do_cache)} do cache + {len(eventos_para_processar)} processados)")
    
    # Atualizar cache com eventos processados
    if eventos_finais:
        adicionar_lote_ao_cache(eventos_finais)
        log(f"   -> Cache atualizado com {len(eventos_finais)} eventos")
    
    # Atualizar clean.json com eventos do cache também
    clean_completo = []
    for item in eventos_do_cache:
        cache = item["cache"]
        clean_completo.append({
            "nome": cache.get("nome", ""),
            "artista": cache.get("artista", ""),
            "data": cache.get("data", ""),
            "cidade": cache.get("cidade", ""),
            "fonte": cache.get("fonte", ""),
            "url": cache.get("url", ""),
            "tipo_geografico": cache.get("tipo_geografico", ""),
            "categoria": cache.get("categoria", ""),
            "pais": cache.get("pais", "")
        })
    clean_completo.extend(eventos_validados_novos)
    salvar_json(clean_completo, clean_path)
    log(f"   -> clean.json atualizado com {len(clean_completo)} eventos")
    
    # Atualizar final.json com resultado mesclado
    salvar_json(eventos_finais, final_path)
    
    # Etapa 13: Gerando ranking
    t = _iniciar_etapa(13, "Gerando ranking...")
    log("Gerando ranking...")
    ranking = gerar_ranking(eventos_finais)
    salvar_ranking(ranking)
    log(f"   -> Ranking gerado com {len(ranking)} eventos")
    _concluir_etapa(13, "Gerando ranking", t)
    
    # Etapa 14: Salvando histórico
    t = _iniciar_etapa(14, "Salvando histórico...")
    log("Salvando no histórico...")
    enviados_telegram = 0
    for item in eventos_finais:
        evento = item.get("evento", {})
        analise = item.get("analise", {})
        auditoria = item.get("auditoria", {})
        acao = item.get("acao_final", "IGNORAR")
        plano_acao = item.get("plano_acao", {})
        arbitragem = item.get("arbitragem", {})
        execucao = item.get("execucao", {})
        salvar_evento_no_historico(evento, analise, auditoria, acao)
        
        try:
            enviado = verificar_e_enviar_alerta(evento, analise, auditoria, acao, plano_acao, arbitragem, execucao)
            if enviado:
                enviados_telegram += 1
                log(f"   -> Alerta Telegram enviado para: {evento.get('nome', 'N/A')}")
        except Exception as e:
            log(f"   [ERRO TELEGRAM] Falha ao notificar {evento.get('nome', '?')}: {e}")
    
    if enviados_telegram > 0:
        log(f"   -> {enviados_telegram} alertas enviados via Telegram")
    
    log(f"   -> {qtd_finais} eventos salvos no histórico")
    _concluir_etapa(14, "Salvando histórico", t)
    
    # Etapa 15: Enviando alertas
    t = _iniciar_etapa(15, "Enviando alertas...")
    _concluir_etapa(15, "Enviando alertas", t)
    
    log("=== PIPELINE CONCLUÍDO ===")
    _concluir_pipeline()
    
    checkpoint.salvar("concluido", {
        "qtd_coletados": qtd_coletados,
        "qtd_validados": qtd_validados,
        "qtd_analisados": qtd_analisados,
        "qtd_finais": len(eventos_finais),
        "score": score['score']
    })
    checkpoint.limpar()
    estado.etapa("concluido", 100)
    logger.info(f"Pipeline concluido com sucesso!")
    
    return qtd_coletados, qtd_validados, qtd_analisados, len(eventos_finais), score['score'], cache_stats
