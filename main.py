"""
Main - Ponto de entrada do scanner_eventos.
Executa o pipeline completo de análise de eventos.
"""
import json
import os
import sys

from core.orchestrator import executar_pipeline
from core.learning import (
    calcular_metricas,
    obter_thresholds,
    mostrar_historico,
    registrar_resultado
)


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


def executar_pipeline_normal():
    """Executa o pipeline normal."""
    print("\n" + "="*50)
    print("  SCANNER DE EVENTOS - Pipeline de Dados")
    print("="*50 + "\n")
    
    qtd_coletados, qtd_validados, qtd_analisados, qtd_finais = executar_pipeline()
    
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
    
    print("\n" + "-"*50)
    print("RESUMO DO PIPELINE:")
    print(f"  Eventos coletados:  {qtd_coletados}")
    print(f"  Eventos limpos:     {qtd_validados}")
    print(f"  Eventos analisados: {qtd_analisados}")
    print(f"  Decisoes tomadas:   {qtd_finais}")
    print("-"*50 + "\n")


if __name__ == "__main__":
    main()
