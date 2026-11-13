from agents.scraper import buscar_eventos_reais
import time

start = time.time()
eventos = buscar_eventos_reais()
elapsed = time.time() - start

print(f"\n=== RESULTADO ===")
print(f"Total: {len(eventos)} eventos")
print(f"Tempo: {elapsed:.1f}s")

# Check dates
print("\n=== Primeiros 10 eventos (DATA) ===")
for e in eventos[:10]:
    nome = e.get('nome', 'N/A')[:40]
    data = e.get('data', 'N/A')
    cidade = e.get('cidade', 'N/A')
    print(f"{nome}")
    print(f"  Data: {data} | Cidade: {cidade}")