import sys
sys.path.insert(0, '.')

from agents.scraper import generic_stealth_scraper, generic_selenium_stealth_scraper, SITES_PROTEGIDOS
import time

print(f"Sites protegidos: {SITES_PROTEGIDOS}")

start = time.time()

print("\n=== Testando sites protegidos ===\n")

# Testar eventim
print("Testando eventim...")
try:
    eventos_eventim = generic_stealth_scraper("eventim")
    print(f"  Undetected: {len(eventos_eventim)} eventos")
except Exception as e:
    print(f"  Erro undetected: {e}")
    eventos_eventim = []

if not eventos_eventim:
    try:
        eventos_eventim = generic_selenium_stealth_scraper("eventim")
        print(f"  Selenium: {len(eventos_eventim)} eventos")
    except Exception as e:
        print(f"  Erro selenium: {e}")

print()

# Testar livepass
print("Testando livepass...")
try:
    eventos_livepass = generic_stealth_scraper("livepass")
    print(f"  Undetected: {len(eventos_livepass)} eventos")
except Exception as e:
    print(f"  Erro undetected: {e}")
    eventos_livepass = []

if not eventos_livepass:
    try:
        eventos_livepass = generic_selenium_stealth_scraper("livepass")
        print(f"  Selenium: {len(eventos_livepass)} eventos")
    except Exception as e:
        print(f"  Erro selenium: {e}")

print(f"\nTempo total: {time.time()-start:.1f}s")

if eventos_eventim:
    print(f"\n=== Eventim ({len(eventos_eventim)}) ===")
    for e in eventos_eventim[:3]:
        print(f"  {e['nome'][:50]}")
        print(f"    URL: {e['url'][:60]}")

if eventos_livepass:
    print(f"\n=== Livepass ({len(eventos_livepass)}) ===")
    for e in eventos_livepass[:3]:
        print(f"  {e['nome'][:50]}")
        print(f"    URL: {e['url'][:60]}")