"""
Main - Ponto de entrada do scanner_eventos.
Executa o pipeline completo de análise de eventos.
"""
import json
import os

from core.orchestrator import executar_pipeline


def main():
    """Executa o pipeline e exibe resultados."""
    print("\n" + "="*50)
    print("  SCANNER DE EVENTOS - Pipeline de Dados")
    print("="*50 + "\n")
    
    qtd_coletados, qtd_validados, qtd_analisados = executar_pipeline()
    
    analyzed_path = os.path.join(os.path.dirname(__file__), "data", "analyzed.json")
    if os.path.exists(analyzed_path):
        with open(analyzed_path, "r", encoding="utf-8") as f:
            eventos_analisados = json.load(f)
        
        print("\n" + "-"*50)
        print("ANÁLISE DE EVENTOS:")
        print("-"*50)
        for item in eventos_analisados:
            evento = item["evento"]
            analise = item["analise"]
            nome = evento.get("nome", "N/A")
            nota = analise.get("nota_final", 0)
            disponivel = "[OK]" if not analise.get("analise_indisponivel") else "[FALHA]"
            print(f"  {disponivel} {nome}")
            print(f"      Hype: {analise.get('hype', 0)} | Escassez: {analise.get('escassez', 0)} | Público: {analise.get('publico', 0)} | Revenda: {analise.get('potencial_revenda', 0)}")
            print(f"      Nota Final: {nota}/10")
            if analise.get("justificativa"):
                print(f"      Justificativa: {analise.get('justificativa', '')[:80]}...")
            print()
    
    print("-"*50)
    print("RESUMO:")
    print(f"  Eventos coletados:  {qtd_coletados}")
    print(f"  Eventos limpos:     {qtd_validados}")
    print(f"  Eventos analisados: {qtd_analisados}")
    print("-"*50 + "\n")


if __name__ == "__main__":
    main()