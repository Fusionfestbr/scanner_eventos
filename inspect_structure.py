from playwright.sync_api import sync_playwright

def inspect_html_structure(url, name):
    print(f"\n=== {name} ===")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(30000)
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(3000)
        
        # Try to find event cards/containers
        selectors = [
            "[class*='event']", "[class*='card']", "[data-id]", 
            "article", ".evento", ".event-card", ".agenda"
        ]
        
        for sel in selectors:
            elements = page.query_selector_all(sel)
            if elements:
                print(f"Selector '{sel}': {len(elements)} found")
                for i, el in enumerate(elements[:2]):
                    try:
                        text = el.inner_text().strip()[:200]
                        print(f"  [{i}]: {text}")
                    except:
                        pass
        
        # Look for JSON data in page
        scripts = page.query_selector_all("script[type='application/ld+json']")
        print(f"\nJSON-LD scripts: {len(scripts)}")
        
        # Get all div text for patterns
        divs = page.query_selector_all("div")
        print(f"\nTotal divs: {len(divs)}")
        
        # Look for event-like text in first 20 divs
        print("\nSample div texts:")
        for d in divs[:10]:
            try:
                text = d.inner_text().strip()[:100]
                if text and len(text) > 20:
                    print(f"  {text[:80]}")
            except:
                pass
        
        browser.close()

inspect_html_structure("https://www.ingresse.com/", "Ingresse")
inspect_html_structure("https://www.bilheteriadigital.com/", "Bilheteria Digital")
inspect_html_structure("https://www.guicheweb.com.br/", "Guicheweb")