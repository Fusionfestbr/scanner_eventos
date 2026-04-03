"""
Agente de scraping para coletar eventos de múltiplas fontes reais.
USA Playwright para renderizar JavaScript com selectors específicos por site.
"""
import re
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from config import SITES_CONFIG, SCRAPER_TIMEOUT


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}


SELECTORS = {
    "ticketmaster": {
        "container": "[data-testid='event-card'], .event-card, .EventCard, [class*='event-item'], li.event-item",
        "nome": "h3, [data-testid='event-title'], .event-title, .title",
        "data": "time, [data-testid='event-date'], .event-date, .date",
        "local": "[data-testid='event-venue'], .venue, .location, .local",
        "link": "a[href*='/event/']",
    },
    "ingresse": {
        "container": "[class*='evento'], [class*='card-evento'], .event-card, article",
        "nome": "h3, h2, [class*='titulo'], [class*='title']",
        "data": "time, [class*='data'], [class*='date'], [class*='date-text']",
        "local": "[class*='local'], [class*='localidade'], [class*='venue']",
        "link": "a[href*='/evento/'], a[href*='/e/']",
    },
    "sympla": {
        "container": "[data-testid='event-card'], .event-card, .event-item, li",
        "nome": "h3, [data-testid='event-name'], .event-name, .title",
        "data": "time, [data-testid='event-date'], .event-date, span:has-text('/')",
        "local": "[data-testid='venue-name'], .venue-name, .local",
        "link": "a[href*='/evento/']",
    },
    "ticket360": {
        "container": ".evento-card, .card-evento, [class*='event'], li",
        "nome": "h3, .titulo, .event-title, [class*='name']",
        "data": "time, .data, .date, .event-date",
        "local": ".local, .venue, .localidade",
        "link": "a[href*='/evento/']",
    },
    "eventim": {
        "container": ".event-item, .event-card, [class*='event']",
        "nome": "h3, .event-title, .title",
        "data": "time, .event-date, .date",
        "local": ".venue, .location, .local",
        "link": "a[href*='/event/']",
    },
    "blueticket": {
        "container": ".card-evento, .evento-card, .event-card, li.evento, article",
        "nome": "h3, .nome-evento, .event-name, .title",
        "data": "time, .data-evento, .date, .data",
        "local": ".local-evento, .local, .venue",
        "link": "a[href*='/evento/']",
    },
    "livepass": {
        "container": ".event-card, [class*='event-item'], li",
        "nome": "h3, .event-title, .title",
        "data": "time, .date, [class*='data']",
        "local": ".venue, .local, .location",
        "link": "a[href*='/evento/']",
    },
    "bilheteriadigital": {
        "container": ".event-card, [class*='event-item'], .card-evento",
        "nome": "h3, .event-name, .title, [class*='nome']",
        "data": "time, .date, [class*='data']",
        "local": ".venue, .local, .location",
        "link": "a[href*='/evento/']",
    },
    "ticketsforfun": {
        "container": ".event-card, .card-evento, [class*='event']",
        "nome": "h3, .title, .event-title",
        "data": "time, .date, [class*='data']",
        "local": ".local, .venue",
        "link": "a[href*='/evento/']",
    },
    "guicheweb": {
        "container": ".evento-card, .event-card, [class*='event-item']",
        "nome": "h3, .nome, .title",
        "data": "time, .data, .date",
        "local": ".local, .localidade",
        "link": "a[href*='/evento/']",
    },
    "q2ingressos": {
        "container": ".evento, .card-evento, [class*='event']",
        "nome": "h3, .nome-evento, .title",
        "data": "time, .data, .date",
        "local": ".local, .venue",
        "link": "a[href*='/evento/']",
    },
    "uhuu": {
        "container": ".event-card, .card-evento, [class*='event-item']",
        "nome": "h3, .title, [class*='nome']",
        "data": "time, .date, [class*='data']",
        "local": ".local, .venue",
        "link": "a[href*='/evento/']",
    },
    "zigtickets": {
        "container": ".event-card, [class*='event-item'], li",
        "nome": "h3, .event-title, .title",
        "data": "time, .date, [class*='data']",
        "local": ".venue, .location",
        "link": "a[href*='/event/']",
    },
    "betimelapse": {
        "container": ".evento, .card-evento, [class*='event']",
        "nome": "h3, .nome, .title",
        "data": "time, .data, .date",
        "local": ".local, .localidade",
        "link": "a[href*='/evento/']",
    },
}


def buscar_ticketmaster():
    return generic_playwright_scraper("ticketmaster")


def buscar_ingresse():
    return generic_playwright_scraper("ingresse")


def buscar_sympla():
    return generic_playwright_scraper("sympla")


def buscar_ticket360():
    return generic_playwright_scraper("ticket360")


def buscar_eventim():
    return generic_playwright_scraper("eventim")


def buscar_blueticket():
    return generic_playwright_scraper("blueticket")


def buscar_livepass():
    return generic_playwright_scraper("livepass")


def buscar_bilheteriadigital():
    return generic_playwright_scraper("bilheteriadigital")


def buscar_ticketsforfun():
    return generic_playwright_scraper("ticketsforfun")


def buscar_guicheweb():
    return generic_playwright_scraper("guicheweb")


def buscar_q2ingressos():
    return generic_playwright_scraper("q2ingressos")


def buscar_uhuu():
    return generic_playwright_scraper("uhuu")


def buscar_zigtickets():
    return generic_playwright_scraper("zigtickets")


def buscar_betimelapse():
    return generic_playwright_scraper("betimelapse")


def generic_playwright_scraper(fonte: str) -> list[dict]:
    """Scraper genérico usando Playwright com selectors específicos."""
    eventos = []
    config = SITES_CONFIG.get(fonte, {})
    url = config.get("url", "")
    
    if not url:
        return eventos
    
    selectors = SELECTORS.get(fonte, {})
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
            )
            context = browser.new_context(
                user_agent=HEADERS["User-Agent"],
                locale="pt-BR",
                viewport={"width": 1280, "height": 720}
            )
            page = context.new_page()
            page.set_default_timeout(15000)
            
            try:
                page.goto(url, wait_until="load", timeout=15000)
            except:
                pass
            
            page.wait_for_timeout(2000)
            
            _scroll_page(page)
            
            eventos.extend(_extract_with_selectors(page, selectors, fonte, url))
            
            if not eventos:
                eventos.extend(_extract_fallback(page, fonte, url))
            
            browser.close()
            
    except Exception as e:
        print(f"   [ERRO] {fonte}: {e}")
    
    return eventos


def _scroll_page(page):
    """Scrolla a página para carregar mais eventos."""
    try:
        for _ in range(2):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1000)
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(500)
    except:
        pass


def _extract_with_selectors(page, selectors: dict, fonte: str, base_url: str) -> list[dict]:
    """Extrai eventos usando selectors específicos."""
    eventos = []
    container_sel = selectors.get("container", "[class*='event']")
    
    try:
        containers = page.query_selector_all(container_sel)
    except:
        containers = []
    
    for item in containers:
        try:
            nome = _get_text(item, selectors.get("nome", "h3, h2"))
            data = _get_data(item, selectors.get("data", "time"))
            local = _get_text(item, selectors.get("local", "[class*='local']"))
            link = _get_link(item, selectors.get("link", "a"))
            
            if nome and len(nome) > 2:
                if not data:
                    data = _generate_future_date()
                
                cidade_extraida = _extract_cidade(local)
                
                eventos.append({
                    "nome": nome,
                    "artista": "Various Artists",
                    "data": data,
                    "cidade": local if not cidade_extraida else cidade_extraida,
                    "fonte": fonte,
                    "url": link if link and link.startswith("http") else (base_url + link if link else base_url)
                })
        except:
            continue
    
    return eventos


def _extract_fallback(page, fonte: str, base_url: str) -> list[dict]:
    """Fallback: extrai qualquer link que pareça ser evento."""
    eventos = []
    
    if fonte in ["ticketmaster", "ingresse", "uhuu"]:
        return eventos
    
    try:
        links = page.query_selector_all("a[href*='/evento'], a[href*='/event/'], a[href*='?id=']")
        
        for link in links[:20]:
            try:
                href = link.get_attribute("href")
                if not href or href.startswith("javascript"):
                    continue
                
                texto = link.inner_text().strip()
                if texto and len(texto) > 10:
                    data_match = re.search(r'(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})', texto)
                    data = ""
                    if data_match:
                        data = normalizar_data(data_match.group(1))
                    
                    if not data:
                        data = _generate_future_date()
                    
                    nome = re.sub(r'\s*[/\-]\s*\d{1,2}[/\-]\d{2,4}.*$', '', texto).strip()
                    nome = re.sub(r'\s+(COMPRAR|MONITORAR|IGNORAR)$', '', nome).strip()
                    
                    if nome and len(nome) > 5:
                        eventos.append({
                            "nome": nome[:100],
                            "artista": "Various Artists",
                            "data": data,
                            "cidade": "",
                            "fonte": fonte,
                            "url": href if href.startswith("http") else base_url
                        })
            except:
                continue
    except:
        pass
    
    return eventos


def _get_text(item, selectors: str) -> str:
    """Tenta obter texto de um elemento."""
    if not selectors:
        return ""
    
    for sel in selectors.split(","):
        sel = sel.strip()
        try:
            elem = item.query_selector(sel)
            if elem:
                text = elem.inner_text().strip()
                if text:
                    return text
        except:
            continue
    return ""


def _get_data(item, selectors: str) -> str:
    """Tenta obter data de um elemento."""
    if not selectors:
        return ""
    
    for sel in selectors.split(","):
        sel = sel.strip()
        try:
            elem = item.query_selector(sel)
            if elem:
                data = elem.get_attribute("datetime")
                if data:
                    return normalizar_data(data)
                text = elem.inner_text().strip()
                if text:
                    return normalizar_data(text)
        except:
            continue
    return ""


def _get_link(item, selectors: str) -> str:
    """Tenta obter link de um elemento."""
    if not selectors:
        return ""
    
    for sel in selectors.split(","):
        sel = sel.strip()
        try:
            elem = item.query_selector(sel)
            if elem:
                href = elem.get_attribute("href")
                if href:
                    return href
        except:
            continue
    return ""


def _extract_cidade(local: str) -> str:
    """Extrai cidade do texto do local."""
    if not local:
        return ""
    
    local = local.upper()
    
    capitais = [
        "SÃO PAULO", "RIO DE JANEIRO", "BELO HORIZONTE", "BRASÍLIA", "SALVADOR",
        "CURITIBA", "FORTALEZA", "RECIFE", "PORTO ALEGRE", "MANAUS",
        "RIO DE JANEIRO", "NITERÓI", "CAMPINAS", "VITÓRIA", "GOIÂNIA",
        "FLORIANÓPOLIS", "CAMPO GRANDE", "BELÉM", "JOÃO PESSOA", "ARACAJU"
    ]
    
    for cidade in capitais:
        if cidade in local:
            return cidade.title()
    
    match = re.search(r'([A-Z][A-Z]+)', local)
    if match:
        return match.group(1).title()
    
    return ""


def _generate_future_date() -> str:
    """Gera uma data futura padrão se não houver data."""
    data = datetime.now() + timedelta(days=30)
    return data.strftime("%Y-%m-%d")


def buscar_eventos_reais() -> list[dict]:
    """Busca eventos de TODOS os sites configurados usando Playwright."""
    print("   Buscando eventos de todas as fontes (Playwright)...")
    
    eventos = []
    
    funcoes_busca = [
        ("ticketmaster", buscar_ticketmaster),
        ("ingresse", buscar_ingresse),
        ("sympla", buscar_sympla),
        ("ticket360", buscar_ticket360),
        ("eventim", buscar_eventim),
        ("blueticket", buscar_blueticket),
        ("livepass", buscar_livepass),
        ("bilheteriadigital", buscar_bilheteriadigital),
        ("ticketsforfun", buscar_ticketsforfun),
        ("guicheweb", buscar_guicheweb),
        ("q2ingressos", buscar_q2ingressos),
        ("uhuu", buscar_uhuu),
        ("zigtickets", buscar_zigtickets),
        ("betimelapse", buscar_betimelapse),
    ]
    
    for nome_fonte, funcao_busca in funcoes_busca:
        print(f"   - Buscando {nome_fonte}...")
        try:
            eventos_fonte = funcao_busca()
            if eventos_fonte:
                print(f"     -> {len(eventos_fonte)} eventos")
            eventos.extend(eventos_fonte)
        except Exception as e:
            print(f"   [ERRO] {nome_fonte}: {e}")
    
    eventos = padronizar_eventos(eventos)
    
    print(f"   -> Total encontrado: {len(eventos)}")
    
    return eventos


def padronizar_eventos(eventos: list[dict]) -> list[dict]:
    """Padroniza formato dos eventos."""
    eventos_padronizados = []
    
    for evento in eventos:
        nome = evento.get("nome", "").strip()
        if not nome or len(nome) < 3:
            continue
        
        data = evento.get("data", "").strip()
        if data:
            data = normalizar_data(data)
            if not data:
                continue
        
        evento_padrao = {
            "nome": nome,
            "artista": evento.get("artista", "Various Artists"),
            "data": data,
            "cidade": evento.get("cidade", "Brasil"),
            "fonte": evento.get("fonte", "web"),
            "url": evento.get("url", "")
        }
        eventos_padronizados.append(evento_padrao)
    
    eventos_padronizados = _deduplicate_events(eventos_padronizados)
    
    return eventos_padronizados[:100]


def _deduplicate_events(eventos: list[dict]) -> list[dict]:
    """Remove eventos duplicados baseado no nome."""
    seen = set()
    unique = []
    for e in eventos:
        nome = e["nome"].lower()
        
        # Skip privacy/cookie notices
        if any(word in nome for word in ["privacidade", "cookies", "política", "politic", "privacy", "consent", "termos", "terms", "aviso legal"]):
            continue
        
        key = nome[:50]
        if key not in seen:
            seen.add(key)
            unique.append(e)
    return unique


def normalizar_data(data_str: str) -> str:
    """Normaliza formato de data para YYYY-MM-DD."""
    if not data_str:
        return ""
    
    try:
        data_str = str(data_str).strip()
    except:
        return ""
    
    patterns = [
        (r"(\d{4})-(\d{2})-(\d{2})", "%Y-%m-%d"),
        (r"(\d{2})/(\d{2})/(\d{4})", "%d/%m/%Y"),
        (r"(\d{2})-(\d{2})-(\d{4})", "%d-%m-%Y"),
    ]
    
    for pattern, fmt in patterns:
        match = re.search(pattern, data_str)
        if match:
            try:
                if fmt == "%Y-%m-%d":
                    return match.group()
                elif fmt == "%d/%m/%Y":
                    return f"{match.group(3)}-{match.group(2)}-{match.group(1)}"
                elif fmt == "%d-%m-%Y":
                    return f"{match.group(3)}-{match.group(2)}-{match.group(1)}"
            except:
                continue
    
    meses = {
        "janeiro": "01", "fevereiro": "02", "março": "03", "abril": "04",
        "maio": "05", "junho": "06", "julho": "07", "agosto": "08",
        "setembro": "09", "outubro": "10", "novembro": "11", "dezembro": "12"
    }
    
    data_lower = data_str.lower()
    for mes_pt, num in meses.items():
        if mes_pt in data_lower:
            match = re.search(r"(\d{1,2})", data_str)
            if match:
                dia = match.group(1).zfill(2)
                return f"2026-{num}-{dia}"
    
    return ""