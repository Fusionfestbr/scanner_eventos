from agents.scraper import buscar_ingresse, buscar_bilheteriadigital, buscar_guicheweb

print("=== INGRESSE ===")
eventos = buscar_ingresse()
print(f"Encontrados: {len(eventos)}")
for e in eventos[:3]:
    print(f'  - {e.get("nome", "SEM NOME")[:50]} | {e.get("cidade", "SEM CIDADE")}')

print("\n=== BILHETERIADIGITAL ===")
eventos = buscar_bilheteriadigital()
print(f"Encontrados: {len(eventos)}")
for e in eventos[:3]:
    print(f'  - {e.get("nome", "SEM NOME")[:50]} | {e.get("cidade", "SEM CIDADE")}')

print("\n=== GUICHEWEB ===")
eventos = buscar_guicheweb()
print(f"Encontrados: {len(eventos)}")
for e in eventos[:3]:
    print(f'  - {e.get("nome", "SEM NOME")[:50]} | {e.get("cidade", "SEM CIDADE")}')