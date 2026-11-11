"""
Retomada do pipeline a partir de data/analyzed.json.

Repete exatamente as etapas 6-14 do core.orchestrator (auditoria em diante),
sem repetir coleta/validação/enriquecimento/análise IA — úteis quando o
processo morreu no meio (ex.: reboot da máquina durante a auditoria).

Uso:  python retomar_pos_analise.py
"""
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.orchestrator import (
    salvar_json,
    carregar_json,
    log,
    _iniciar_etapa,
    _concluir_etapa,
)
from agents.auditor import auditar_eventos
from core.decision import processar_decisoes
from core.learning import salvar_evento_no_historico
from core.ranking import gerar_ranking, salvar_ranking
from core.notifier import verificar_e_enviar_alerta
from core.predictor import processar_previsoes
from core.executor import processar_planos_acao
from core.arbitrage import processar_arbitragem
from agents.scraper import buscar_precos_revenda
from core.executor_real import gerar_execucao_real
from core.cache import mesclar_resultados, adicionar_lote_ao_cache

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def _p(nome):
    return os.path.join(DATA, nome)


def retomar():
    eventos_analisados = carregar_json(_p("analyzed.json"))
    if not eventos_analisados:
        log("   [RETOMA] analyzed.json vazio/ausente — nada a retomar")
        return
    eventos_validados_novos = carregar_json(_p("clean.json"))
    log(f"   [RETOMA] {len(eventos_analisados)} eventos de analyzed.json "
        f"+ {len(eventos_validados_novos)} de clean.json")

    eventos_do_cache = []
    eventos_para_processar = eventos_analisados

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

    # Etapa 8: Previsões
    t = _iniciar_etapa(8, "Gerando previsões...")
    log("Gerando previsões de valorização...")
    eventos_finais = processar_previsoes(eventos_finais)
    log(f"   -> Previsões geradas para {len(eventos_finais)} eventos")
    _concluir_etapa(8, "Gerando previsões", t)

    # Etapa 9: Planos de ação
    t = _iniciar_etapa(9, "Gerando planos de ação...")
    log("Gerando planos de ação...")
    eventos_finais = processar_planos_acao(eventos_finais)
    log(f"   -> Planos de ação gerados para {len(eventos_finais)} eventos")
    _concluir_etapa(9, "Gerando planos de ação", t)

    # Etapa 10: Arbitragem
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
                    precos_revenda.insert(0, {
                        "plataforma": evento_original.get("fonte", "original"),
                        "preco": preco_original,
                    })
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

    # Etapa 11: Preços revenda
    t = _iniciar_etapa(11, "Buscando preços revenda...")
    log("Gerando execuções reais...")
    eventos_comprar = [i for i in eventos_finais if i.get("acao_final") == "COMPRAR"]
    count_exec = 0
    _concluir_etapa(11, "Buscando preços revenda", t)

    # Etapa 12: Execuções
    t = _iniciar_etapa(12, "Gerando execuções...")

    def gerar_execucao_para_item(item):
        evento = item.get("evento", {})
        analise = item.get("analise", {})
        previsao = item.get("previsao", {})
        plano_acao = item.get("plano_acao", {})
        execucao = gerar_execucao_real(evento, analise, previsao, plano_acao)
        return item.get("evento", {}).get("nome", ""), execucao

    if not eventos_comprar:
        log("   -> Nenhum evento para COMPRAR, pulando geração de execuções")
    else:
        max_workers = max(1, min(4, len(eventos_comprar)))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(gerar_execucao_para_item, item): item for item in eventos_comprar}
            for future in as_completed(futures):
                item = futures[future]
                nome_ev, execucao = future.result()
                item["execucao"] = execucao
                count_exec += 1
                log(f"   -> Execução {count_exec}/{len(eventos_comprar)}: {nome_ev[:50]}")

    final_path = _p("final.json")
    salvar_json(eventos_finais, final_path)
    log(f"   -> Salvo em {final_path}")
    _concluir_etapa(12, "Gerando execuções", t)

    # Mesclagem de cache
    log("   -> Mesclando eventos do cache...")
    eventos_finais = mesclar_resultados(eventos_do_cache, eventos_finais)
    log(f"   -> Total: {len(eventos_finais)} eventos")

    if eventos_finais:
        adicionar_lote_ao_cache(eventos_finais)
        log(f"   -> Cache atualizado com {len(eventos_finais)} eventos")

    # clean.json (mantém o que já existe — eventos_validados_novos)
    clean_path = _p("clean.json")
    salvar_json(eventos_validados_novos, clean_path)
    log(f"   -> clean.json atualizado com {len(eventos_validados_novos)} eventos")

    # final.json mesclado
    salvar_json(eventos_finais, final_path)

    # Etapa 13: Ranking
    t = _iniciar_etapa(13, "Gerando ranking...")
    log("Gerando ranking...")
    ranking = gerar_ranking(eventos_finais)
    salvar_ranking(ranking)
    log(f"   -> Ranking gerado com {len(ranking)} eventos")
    _concluir_etapa(13, "Gerando ranking", t)

    # Etapa 14: Histórico + Telegram
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

    # Etapa 15
    t = _iniciar_etapa(15, "Enviando alertas...")
    _concluir_etapa(15, "Enviando alertas", t)

    log("=== RETOMADA CONCLUÍDA ===")


if __name__ == "__main__":
    retomar()
