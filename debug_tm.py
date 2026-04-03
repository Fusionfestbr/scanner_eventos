import sys
sys.path.insert(0, '.')

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    page.goto("https://www.ticketmaster.com.br/", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(3000)
    
    # Get first 5 event links
    links = page.query_selector_all("a[href*='/event/']")[:5]
    
    print("=== First 5 events ===\n")
    
    for i, link in enumerate(links):
        href = link.get_attribute("href")
        
        # Try different ways to get the name
        nome = link.inner_text().strip()[:50]
        print(f"{i+1}. Nome: '{nome}'")
        print(f"   URL: {href}")
        
        # Get parent container's full text
        try:
            container = link
            for _ in range(3):  # Go up 3 levels
                container = container.evaluate("el => el.parentElement")
                if not container:
                    break
            
            if container:
                text = container.inner_text()
                # Show lines after the event name
                lines = text.split("\n")
                for line in lines[1:4]:
                    if line.strip():
                        print(f"   Line: '{line.strip()[:60]}'")
        except Exception as e:
            print(f"   Error: {e}")
        
        print()
    
    browser.close()