"""
Main - Ponto de entrada do scanner_eventos.
Executa o pipeline completo de análise de eventos.
"""
import json
import os
import sys

from core.orchestrator import executar_pipeline
from core.scheduler import executar_loop, stop_scheduler
from core.learning import (
    calcular_metricas,
    obter_thresholds,
    mostrar_historico,
    registrar_resultado,
    registrar_operacao,
    calcular_metricas_financeiras,
    mostrar_resultados_operacoes
)
from core.ranking import gerar_ranking, salvar_ranking
from core.notifier import testar_conexao, enviar_alerta
from core.filtros import (
    filtrar_por_periodo,
    filtrar_por_escopo,
    filtrar_por_categoria,
    filtrar_por_cidade,
    filtrar_por_artista,
    buscar,
    resumo_estatistico,
    ordenar_por_data
)
from core.classificadores import enriquecer_lista
from config import INTERVALO_MINUTOS


def main():
    """Executa o pipeline e exibe resultados."""
    args = sys.argv[1:]
    
    if "--eventim" in args:
        from agents.eventim_api import get_eventim_events
        eventos = get_eventim_events()
        print(f"\n  Eventos Eventim: {len(eventos)}")
        for e in eventos[:10]:
            print(f"  - {e['nome']} | {e['data_inicio'][:10]} | R${e['preco_base']}")
        return
    
    if "--ingresse" in args:
        from agents.ingresse_api import get_ingresse_events
        eventos = get_ingresse_events()
        print(f"\n  Eventos Ingresse: {len(eventos)}")
        for e in eventos[:10]:
            print(f"  - {e['name']} | {e['date'][:10]}")
        return
    
    if "--all-events" in args:
        from agents.aggregator import get_all_events
        eventos = get_all_events()
        for e in eventos[:10]:
            print(f"  [{e['source']}] {e['name']} | {e['date'][:10]}")
        return
    
    if "--livepass" in args:
        from agents.livepass_api import get_livepass_events
        eventos = get_livepass_events()
        print(f"\n  Eventos Livepass: {len(eventos)}")
        for e in eventos[:10]:
            print(f"  - {e['name']} | {e['date'][:10]}")
        return
    
    if "--q2ingressos" in args:
        from agents.q2ingressos_api import get_q2ingressos_events
        eventos = get_q2ingressos_events()
        print(f"\n  Eventos Q2 Ingressos: {len(eventos)}")
        for e in eventos[:10]:
            print(f"  - {e['name']} | {e['date'][:10]}")
        return
    
    if "--zigtickets" in args:
        from agents.zigtickets_api import get_zigtickets_events
        eventos = get_zigtickets_events()
        print(f"\n  Eventos Zig Tickets: {len(eventos)}")
        for e in eventos[:10]:
            print(f"  - {e['name']} | {e['date'][:10]}")
        return
    
    if "--guicheweb" in args:
        from agents.guicheweb_api import get_guicheweb_events
        eventos = get_guicheweb_events()
        print(f"\n  Eventos GuichêWeb: {len(eventos)}")
        for e in eventos[:10]:
            print(f"  - {e['name']} | {e['date'][:10]}")
        return
    
    if "--metrics" in args:
        mostrar_metricas()
        return
    
    if "--history" in args:
        mostrar_historico(resumido=False)
        return
    
    if "--register" in args:
        registrar_resultado_manual()
        return
    
    if "--register-op" in args:
        registrar_operacao_manual()
        return
    
    if "--results" in args:
        mostrar_resultados()
        return
    
    if "--test-telegram" in args:
        testar_conexao_telegram()
        return
    
    if "--daemon" in args:
        idx = args.index("--daemon")
        intervalo = int(args[idx + 1]) if idx + 1 < len(args) else INTERVALO_MINUTOS
        executar_loop(intervalo)
        return
    
    if "--stop" in args:
        stop_scheduler()
        return
    
    if "--brutos" in args:
        listar_eventos_brutos()
        return
    
    if "--limpos" in args:
        listar_eventos_limpos()
        return
    
    if "--semana" in args:
        listar_filtrados(periodo="semana")
        return
    
    if "--mes" in args:
        listar_filtrados(periodo="mes")
        return
    
    if "--ano" in args:
        listar_filtrados(periodo="ano")
        return
    
    if "--nacional" in args:
        listar_filtrados(escopo="nacional")
        return
    
    if "--internacional" in args:
        listar_filtrados(escopo="internacional")
        return
    
    if "--categoria" in args:
        idx = args.index("--categoria")
        cat = args[idx + 1] if idx + 1 < len(args) else ""
        listar_filtrados(categoria=cat)
        return
    
    if "--artista" in args:
        idx = args.index("--artista")
        nome = args[idx + 1] if idx + 1 < len(args) else ""
        listar_filtrados(artista=nome)
        return
    
    if "--cidade" in args:
        idx = args.index("--cidade")
        cidade = args[idx + 1] if idx + 1 < len(args) else ""
        listar_filtrados(cidade=cidade)
        return
    
    if "--busca" in args:
        idx = args.index("--busca")
        termo = args[idx + 1] if idx + 1 < len(args) else ""
        listar_filtrados(busca=termo)
        return
    
    if "--resumo" in args:
        mostrar_resumo()
        return
    
    executar_pipeline_normal()


def mostrar_metricas():
    """Mostra métricas do aprendizado."""
    print("\n" + "="*50)
    print("  MÉTRICAS DE APRENDIZADO")
    print("="*50 + "\n")
    
    metricas = calcular_metricas()
    thresholds = obter_thresholds()
    
    print(f"  Total de eventos no histórico: {metricas.get('total_eventos', 0)}")
    print(f"  Eventos com resultado: {metricas.get('eventos_com_resultado', 0)}")
    
    if metricas.get("sem_dados"):
        print("\n  Sem dados suficientes para métricas.")
    else:
        print("\n  TAXAS DE ACERTO:")
        print(f"    Geral:         {metricas.get('taxa_acerto_geral', 0)}%")
        print(f"    COMPRAR:       {metricas.get('taxa_acerto_comprar', 0)}%")
        print(f"    MONITORAR:     {metricas.get('taxa_acerto_monitorar', 0)}%")
        
        print("\n  DETALHES COMPRAR:")
        print(f"    Total: {metricas.get('comprar_total', 0)}")
        print(f"    Sucesso: {metricas.get('comprar_sucesso', 0)}")
        print(f"    Falha: {metricas.get('comprar_falha', 0)}")
        
        if metricas.get("eventos_falharam"):
            print("\n  EVENTOS QUE FALHARAM:")
            for nome in metricas["eventos_falharam"]:
                print(f"    - {nome}")
    
    print("\n  THRESHOLDS ATUAIS:")
    print(f"    min_nota_comprar: {thresholds.get('min_nota_comprar', 8.0)}")
    print(f"    min_confianca:   {thresholds.get('min_confianca', 7.0)}")
    print("-"*50 + "\n")


def registrar_resultado_manual():
    """Permite registrar resultado manualmente."""
    print("\n" + "="*50)
    print("  REGISTRAR RESULTADO")
    print("="*50 + "\n")
    
    nome = input("  Nome do evento: ").strip()
    data = input("  Data do evento (YYYY-MM-DD): ").strip()
    resultado = input("  Resultado (valorizou/nao_valorizou): ").strip()
    
    if resultado not in ["valorizou", "nao_valorizou"]:
        print("  Resultado inválido. Use: valorizou ou nao_valorizou")
        return
    
    sucesso = registrar_resultado(nome, data, resultado)
    
    if sucesso:
        print(f"\n  Resultado registrado: {resultado}")
    else:
        print("\n  Evento não encontrado no histórico.")
    
    print("-"*50 + "\n")


def registrar_operacao_manual():
    """Registra uma operação de compra/venda concretizada."""
    print("\n" + "="*50)
    print("  REGISTRAR OPERAÇÃO (COMPRA/VENDA)")
    print("="*50 + "\n")
    
    nome = input("  Nome do evento: ").strip()
    data_evento = input("  Data do evento (YYYY-MM-DD): ").strip()
    artista = input("  Artista: ").strip()
    preco_compra = float(input("  Preço de compra (R$): ").strip().replace(",", "."))
    preco_venda = float(input("  Preço de venda (R$): ").strip().replace(",", "."))
    data_compra = input("  Data de compra (YYYY-MM-DD): ").strip()
    data_venda = input("  Data de venda (YYYY-MM-DD): ").strip()
    fonte_compra = input("  Fonte de compra (ticketmaster/sympla/etc): ").strip()
    fonte_venda = input("  Fonte de venda (viagogo/buyticket/etc): ").strip()
    nota = input("  Nota da decisão original (ex: 8.5): ").strip()
    estrategia = input("  Estratégia (conservativa/moderada/arriscada): ").strip()
    
    nota_float = float(nota) if nota else 0
    estrategia_valida = estrategia if estrategia in ["conservativa", "moderada", "arriscada"] else "conservativa"
    
    sucesso = registrar_operacao(
        nome_evento=nome,
        data_evento=data_evento,
        artista=artista,
        preco_compra=preco_compra,
        preco_venda=preco_venda,
        data_compra=data_compra,
        data_venda=data_venda,
        fonte_compra=fonte_compra,
        fonte_venda=fonte_venda,
        nota_decisao=nota_float,
        estrategia=estrategia_valida
    )
    
    if sucesso:
        lucro = preco_venda - preco_compra
        lucro_pct = (lucro / preco_compra * 100) if preco_compra > 0 else 0
        print(f"\n  Operação registrada!")
        print(f"  Lucro: R$ {lucro:.2f} ({lucro_pct:.1f}%)")
    else:
        print("\n  Erro ao registrar operação.")
    
    print("-"*50 + "\n")


def mostrar_resultados():
    """Mostra métricas financeiras."""
    print("\n" + "="*50)
    print("  RESULTADOS FINANCEIROS")
    print("="*50 + "\n")
    
    mostrar_resultados_operacoes(resumido=False)
    print("-"*50 + "\n")


def testar_conexao_telegram():
    """Testa conexão com Telegram."""
    print("\n" + "="*50)
    print("  TESTE DE CONEXÃO TELEGRAM")
    print("="*50 + "\n")
    
    from core.notifier import testar_conexao
    
    sucesso = testar_conexao()
    
    if sucesso:
        print("\n  Telegram conectado com sucesso!")
    else:
        print("\n  Falha na conexão com Telegram.")
    
    print("-"*50 + "\n")


def listar_eventos_brutos():
    """Lista todos os eventos brutos (antes de qualquer filtro)."""
    raw_path = os.path.join(os.path.dirname(__file__), "data", "raw.json")
    if not os.path.exists(raw_path):
        print("\n  Nenhum evento bruto encontrado. Execute o pipeline primeiro.")
        return
    
    with open(raw_path, "r", encoding="utf-8") as f:
        eventos = json.load(f)
    
    eventos_enriquecidos = enriquecer_lista(eventos)
    eventos_ordenados = ordenar_por_data(eventos_enriquecidos, crescente=True)
    
    print(f"\n{'='*60}")
    print(f"  EVENTOS BRUTOS ({len(eventos_ordenados)} eventos)")
    print(f"{'='*60}\n")
    
    for i, e in enumerate(eventos_ordenados, 1):
        nome = e.get("nome", "N/A")
        data = e.get("data", "N/A")
        cidade = e.get("cidade", "")
        fonte = e.get("fonte", "")
        cat = e.get("categoria", enriquecer_lista([e])[0].get("categoria", ""))
        print(f"  {i:3d}. {nome[:50]}")
        print(f"       Data: {data[:10]} | Cidade: {cidade} | Fonte: {fonte} | Cat: {cat}")
        print()
    
    print(f"{'='*60}\n")


def listar_eventos_limpos():
    """Lista eventos válidos (após validação)."""
    clean_path = os.path.join(os.path.dirname(__file__), "data", "clean.json")
    if not os.path.exists(clean_path):
        print("\n  Nenhum evento limpo encontrado. Execute o pipeline primeiro.")
        return
    
    with open(clean_path, "r", encoding="utf-8") as f:
        eventos = json.load(f)
    
    eventos_ordenados = ordenar_por_data(eventos, crescente=True)
    
    print(f"\n{'='*60}")
    print(f"  EVENTOS VÁLIDOS ({len(eventos_ordenados)} eventos)")
    print(f"{'='*60}\n")
    
    for i, e in enumerate(eventos_ordenados, 1):
        nome = e.get("nome", "N/A")
        data = e.get("data", "N/A")
        cidade = e.get("cidade", "")
        fonte = e.get("fonte", "")
        cat = e.get("categoria", "")
        geo = e.get("tipo_geografico", "")
        pais = e.get("pais", "")
        print(f"  {i:3d}. {nome[:50]}")
        print(f"       Data: {data[:10]} | Cidade: {cidade} | Fonte: {fonte}")
        print(f"       Categoria: {cat} | Escopo: {geo} | País: {pais}")
        print()
    
    print(f"{'='*60}\n")


def listar_filtrados(periodo="todos", escopo="todos", categoria="todos", cidade="", artista="", busca=""):
    """Lista eventos do ranking com filtros aplicados."""
    ranking_path = os.path.join(os.path.dirname(__file__), "data", "ranking.json")
    if not os.path.exists(ranking_path):
        print("\n  Nenhum ranking encontrado. Execute o pipeline primeiro.")
        return
    
    with open(ranking_path, "r", encoding="utf-8") as f:
        eventos = json.load(f)
    
    eventos_filtrados = eventos
    
    if periodo != "todos":
        eventos_filtrados = filtrar_por_periodo(eventos_filtrados, periodo)
    if escopo != "todos":
        eventos_filtrados = filtrar_por_escopo(eventos_filtrados, escopo)
    if categoria != "todos":
        eventos_filtrados = filtrar_por_categoria(eventos_filtrados, categoria)
    if cidade:
        eventos_filtrados = filtrar_por_cidade(eventos_filtrados, cidade)
    if artista:
        eventos_filtrados = filtrar_por_artista(eventos_filtrados, artista)
    if busca:
        eventos_filtrados = buscar(eventos_filtrados, busca)
    
    if not eventos_filtrados:
        print("\n  Nenhum evento encontrado com os filtros aplicados.")
        return
    
    titulo = "EVENTOS FILTRADOS"
    filtros_ativos = []
    if periodo != "todos": filtros_ativos.append(f"período={periodo}")
    if escopo != "todos": filtros_ativos.append(f"escopo={escopo}")
    if categoria != "todos": filtros_ativos.append(f"categoria={categoria}")
    if cidade: filtros_ativos.append(f"cidade={cidade}")
    if artista: filtros_ativos.append(f"artista={artista}")
    if busca: filtros_ativos.append(f"busca={busca}")
    
    if filtros_ativos:
        titulo += f" ({', '.join(filtros_ativos)})"
    
    print(f"\n{'='*60}")
    print(f"  {titulo}")
    print(f"  {len(eventos_filtrados)} eventos encontrados")
    print(f"{'='*60}\n")
    
    for i, item in enumerate(eventos_filtrados, 1):
        evento = item.get("evento", {})
        analise = item.get("analise", {})
        acao = item.get("acao_final", "N/A")
        nome = evento.get("nome", "N/A")
        data = evento.get("data", "N/A")
        cidade_ev = evento.get("cidade", "")
        nota = analise.get("nota_final", 0)
        cat = evento.get("categoria", "")
        geo = evento.get("tipo_geografico", "")
        
        emoji = {"COMPRAR": "[!]", "MONITORAR": "[?]", "IGNORAR": "[-]"}.get(acao, "[ ]")
        print(f"  {i:3d}. {emoji} {nome[:50]}")
        print(f"       Data: {data[:10]} | Cidade: {cidade_ev} | Nota: {nota}/10 | Ação: {acao}")
        print(f"       Categoria: {cat} | Escopo: {geo}")
        print()
    
    print(f"{'='*60}\n")


def mostrar_resumo():
    """Mostra resumo estatístico dos eventos no ranking."""
    ranking_path = os.path.join(os.path.dirname(__file__), "data", "ranking.json")
    if not os.path.exists(ranking_path):
        print("\n  Nenhum ranking encontrado. Execute o pipeline primeiro.")
        return
    
    with open(ranking_path, "r", encoding="utf-8") as f:
        eventos = json.load(f)
    
    resumo = resumo_estatistico(eventos)
    
    print(f"\n{'='*60}")
    print(f"  RESUMO ESTATÍSTICO")
    print(f"{'='*60}\n")
    
    print(f"  Total de eventos: {resumo.get('total', 0)}")
    
    print(f"\n  Por ação:")
    for acao, qtd in resumo.get("por_acao", {}).items():
        print(f"    {acao}: {qtd}")
    
    print(f"\n  Por categoria:")
    for cat, qtd in resumo.get("por_categoria", {}).items():
        print(f"    {cat}: {qtd}")
    
    print(f"\n  Por escopo:")
    for escopo, qtd in resumo.get("por_escopo", {}).items():
        print(f"    {escopo}: {qtd}")
    
    print(f"\n  Top 10 cidades:")
    for cidade, qtd in resumo.get("por_cidade", {}).items():
        print(f"    {cidade}: {qtd}")
    
    print(f"\n  Por fonte:")
    for fonte, qtd in resumo.get("por_fonte", {}).items():
        print(f"    {fonte}: {qtd}")
    
    print(f"\n{'='*60}\n")


def executar_pipeline_normal():
    """Executa o pipeline normal."""
    print("\n" + "="*50)
    print("  Fusion Revenda Master - Pipeline de Dados")
    print("="*50 + "\n")
    
    qtd_coletados, qtd_validados, qtd_analisados, qtd_finais, score = executar_pipeline()
    
    final_path = os.path.join(os.path.dirname(__file__), "data", "final.json")
    if os.path.exists(final_path):
        with open(final_path, "r", encoding="utf-8") as f:
            eventos_finais = json.load(f)
        
        print("\n" + "-"*50)
        print("DECISÕES FINAIS:")
        print("-"*50)
        
        compras = []
        monitorar = []
        ignorar = []
        
        for item in eventos_finais:
            evento = item["evento"]
            analise = item["analise"]
            auditoria = item["auditoria"]
            acao = item.get("acao_final", "IGNORAR")
            nome = evento.get("nome", "N/A")
            nota = analise.get("nota_final", 0)
            decisao = auditoria.get("decisao", "N/A")
            
            if acao == "COMPRAR":
                compras.append(item)
            elif acao == "MONITORAR":
                monitorar.append(item)
            else:
                ignorar.append(item)
            
            emoji = {"COMPRAR": "[!]", "MONITORAR": "[?]", "IGNORAR": "[-]"}.get(acao, "[ ]")
            print(f"  {emoji} {nome}")
            print(f"      Nota: {nota}/10 | Auditor: {decisao} | Acao: {acao}")
            print()
        
        print("-"*50)
        print("RESUMO DE AÇÕES:")
        print(f"  COMPRAR:  {len(compras)}")
        print(f"  MONITORAR: {len(monitorar)}")
        print(f"  IGNORAR:   {len(ignorar)}")
        print("-"*50)
        
        thresholds = obter_thresholds()
        print(f"\n  Thresholds usados: nota>={thresholds['min_nota_comprar']}, confianca>={thresholds['min_confianca']}")
        print(f"\n  Score de qualidade: {score}%")
    
    print("\n" + "-"*50)
    print("RESUMO DO PIPELINE:")
    print(f"  Eventos coletados:  {qtd_coletados}")
    print(f"  Eventos limpos:     {qtd_validados}")
    print(f"  Eventos analisados: {qtd_analisados}")
    print(f"  Decisoes tomadas:   {qtd_finais}")
    print(f"  Qualidade dados:    {score}%")
    print("-"*50 + "\n")
    
    final_path = os.path.join(os.path.dirname(__file__), "data", "final.json")
    if os.path.exists(final_path):
        with open(final_path, "r", encoding="utf-8") as f:
            eventos_finais = json.load(f)
        
        ranking = gerar_ranking(eventos_finais)
        salvar_ranking(ranking)
        print(f"  Ranking gerado com {len(ranking)} eventos")
        print(f"  Execute: python dashboard/app.py para iniciar o dashboard")


if __name__ == "__main__":
    main()
