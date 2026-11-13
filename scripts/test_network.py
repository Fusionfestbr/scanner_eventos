import requests
from playwright.sync_api import sync_playwright

def test_with_playwright(url, name):
    print(f"\n=== {name} ===")
    print(f"URL: {url}")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_timeout(30000)
            
            try:
                resp = page.goto(url, wait_until="domcontentloaded", timeout=30000)
                print(f"Status: {resp.status}")
                page.wait_for_timeout(3000)
                title = page.title()
                print(f"Title: {title[:100]}")
                
                # Check page content
                content = page.content()
                print(f"HTML length: {len(content)}")
                
            except Exception as e:
                print(f"ERRO: {e}")
            finally:
                browser.close()
    except Exception as e:
        print(f"ERRO browser: {e}")

test_with_playwright("https://www.ingresse.com/", "Ingresse")
test_with_playwright("https://www.bilheteriadigital.com/", "Bilheteria Digital")
test_with_playwright("https://www.guicheweb.com.br/", "Guicheweb")