import threading
import time

from agents.scraper import generic_playwright_scraper

sites = ["ingresse", "bilheteriadigital", "guicheweb"]
results = {}

def test_site(site):
    try:
        eventos = generic_playwright_scraper(site, max_retries=1)
        results[site] = eventos
    except Exception as e:
        results[site] = f"ERRO: {e}"

for site in sites:
    print(f"\n=== {site.upper()} ===")
    t = threading.Thread(target=test_site, args=(site,))
    t.daemon = True
    t.start()
    t.join(timeout=40)
    
    if t.is_alive():
        print("TIMEOUT: Site não respondeu em 40s")
        results[site] = []
    else:
        eventos = results.get(site, [])
        if isinstance(eventos, list):
            print(f"Encontrados: {len(eventos)}")
            for e in eventos[:2]:
                print(f'  - {e.get("nome", "SEM NOME")[:40]}')
        else:
            print(eventos)