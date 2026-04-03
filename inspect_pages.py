from playwright.sync_api import sync_playwright

def inspect_page(url, name):
    print(f"\n=== {name} ===")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(30000)
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)
        
        # Find all links with event patterns
        links = page.query_selector_all("a[href]")
        print(f"Total links: {len(links)}")
        
        event_links = []
        for link in links:
            try:
                href = link.get_attribute("href")
                if href and ("evento" in href.lower() or "/e/" in href or "/event/" in href):
                    event_links.append(href)
            except:
                pass
        
        print(f"Event links found: {len(event_links)}")
        for h in event_links[:5]:
            print(f"  {h[:80]}")
        
        # Get sample text from links
        sample_links = page.query_selector_all("a")[:10]
        print("\nSample link texts:")
        for l in sample_links:
            try:
                text = l.inner_text().strip()[:60]
                href = l.get_attribute("href", "")[:50]
                if text:
                    print(f"  [{text}] -> {href}")
            except:
                pass
        
        browser.close()

inspect_page("https://www.ingresse.com/", "Ingresse")
inspect_page("https://www.bilheteriadigital.com/", "Bilheteria Digital")
inspect_page("https://www.guicheweb.com.br/", "Guicheweb")