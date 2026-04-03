"""
Main - Ponto de entrada do scanner_eventos.
Executa o pipeline completo de análise de eventos.
"""
from core.orchestrator import executar_pipeline


def main():
    """Executa o pipeline e exibe resultados."""
    print("\n" + "="*50)
    print("  SCANNER DE EVENTOS - Pipeline de Dados")
    print("="*50 + "\n")
    
    qtd_coletados, qtd_validados = executar_pipeline()
    
    print("\n" + "-"*50)
    print("RESUMO:")
    print(f"  Eventos coletados:  {qtd_coletados}")
    print(f"  Eventos limpos:     {qtd_validados}")
    print(f"  Eventos removidos:  {qtd_coletados - qtd_validados}")
    print("-"*50 + "\n")


if __name__ == "__main__":
    main()