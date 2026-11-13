from core.learning import registrar_operacao, calcular_metricas_financeiras

# Test: Register a sample operation
sucesso = registrar_operacao(
    nome_evento="Rock in Rio 2026",
    data_evento="2026-09-15",
    artista="Various Artists",
    preco_compra=800.00,
    preco_venda=1200.00,
    data_compra="2026-04-01",
    data_venda="2026-04-15",
    fonte_compra="ticketmaster",
    fonte_venda="viagogo",
    nota_decisao=8.5,
    estrategia="conservativa"
)

print(f"Registro: {'Sucesso' if sucesso else 'Falha'}")

metricas = calcular_metricas_financeiras()
print(f"\nMétricas: {metricas}")