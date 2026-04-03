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
from config import INTERVALO_MINUTOS


def main():
    """Executa o pipeline e exibe resultados."""
    args = sys.argv[1:]
    
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
