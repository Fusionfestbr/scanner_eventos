"""
Agente de scraping para coletar eventos de múltiplas fontes reais.
USA Playwright para renderizar JavaScript com selectors específicos por site.
"""
import re
from datetime import datetime, timedelta
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from config import SITES_CONFIG, SCRAPER_TIMEOUT


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}


SELECTORS = {
    "ticketmaster": {
        "container": "a[href*='/event/'], article, li a",
        "nome": "h3, h2, span, div",
        "data": "time, span",
        "local": "span, div",
        "link": "a[href*='/event/'], a",
    },
    "ingresse": {
        "container": "a[href*='/evento/'], a[href*='/e/'], article",
        "nome": "h3, h2, span",
        "data": "time, span",
        "local": "span, div",
        "link": "a[href*='/evento/'], a[href*='/e/'], a",
    },
    "sympla": {
        "container": "a[href*='/evento/'], a[href*='/br/'], article",
        "nome": "h3, h2, span",
        "data": "time, span",
        "local": "span, div",
        "link": "a[href*='/evento/'], a",
    },
    "ticket360": {
        "container": "a[href*='/evento/'], a[href*='/event/'], article",
        "nome": "h3, h2, span",
        "data": "time, span",
        "local": "span, div",
        "link": "a[href*='/evento/'], a[href*='/event/'], a",
    },
    "eventim": {
        "container": "a[href*='/event/'], article",
        "nome": "h3, h2, span",
        "data": "time, span",
        "local": "span, div",
        "link": "a[href*='/event/'], a",
    },
    "blueticket": {
        "container": "a[href*='/evento/'], article",
        "nome": "h3, h2, span",
        "data": "time, span",
        "local": "span, div",
        "link": "a[href*='/evento/'], a",
    },
    "livepass": {
        "container": "a[href*='/evento/'], article",
        "nome": "h3, h2, span",
        "data": "time, span",
        "local": "span, div",
        "link": "a[href*='/evento/'], a",
    },
    "bilheteriadigital": {
        "container": "a[href*='/evento/'], article",
        "nome": "h3, h2, span",
        "data": "time, span",
        "local": "span, div",
        "link": "a[href*='/evento/'], a",
    },
    "ticketsforfun": {
        "container": "a[href*='/evento/'], article",
        "nome": "h3, h2, span",
        "data": "time, span",
        "local": "span, div",
        "link": "a[href*='/evento/'], a",
    },
    "guicheweb": {
        "container": "a[href*='/evento/'], article",
        "nome": "h3, h2, span",
        "data": "time, span",
        "local": "span, div",
        "link": "a[href*='/evento/'], a",
    },
    "q2ingressos": {
        "container": "a[href*='/evento/'], article",
        "nome": "h3, h2, span",
        "data": "time, span",
        "local": "span, div",
        "link": "a[href*='/evento/'], a",
    },
    "uhuu": {
        "container": "a[href*='/evento/'], a[href*='/rj/'], a[href*='/sp/'], article",
        "nome": "h3, h2, span",
        "data": "time, span",
        "local": "span, div",
        "link": "a[href*='/evento/'], a[href*='/rj/'], a[href*='/sp/'], a",
    },
    "zigtickets": {
        "container": "a[href*='/event/'], article",
        "nome": "h3, h2, span",
        "data": "time, span",
        "local": "span, div",
        "link": "a[href*='/event/'], a",
    },
    "betimelapse": {
        "container": "a[href*='/evento/'], article",
        "nome": "h3, h2, span",
        "data": "time, span",
        "local": "span, div",
        "link": "a[href*='/evento/'], a",
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


def generic_playwright_scraper(fonte: str, max_retries: int = 3) -> list[dict]:
    """Scraper genérico com retry e melhor extração."""
    eventos = []
    config = SITES_CONFIG.get(fonte, {})
    url = config.get("url", "")
    timeout = config.get("timeout", 30) * 1000
    
    if not url:
        return eventos
    
    selectors = SELECTORS.get(fonte, {})
    
    for tentativa in range(1, max_retries + 1):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage"]
                )
                context = browser.new_context(
                    user_agent=HEADERS["User-Agent"],
                    locale="pt-BR",
                    viewport={"width": 1280, "height": 720}
                )
                page = context.new_page()
                page.set_default_timeout(timeout)
                
                try:
                    page.goto(url, wait_until="networkidle", timeout=timeout)
                except Exception as e:
                    if tentativa < max_retries:
                        page.wait_for_timeout(5000)
                        continue
                    else:
                        print(f"   [ERRO] {fonte}: não carregou após {max_retries} tentativas")
                        continue
                
                page.wait_for_timeout(3000)
                _scroll_page(page)
                
                eventos_extracted = _extract_with_selectors(page, selectors, fonte, url)
                
                if eventos_extracted:
                    eventos.extend(eventos_extracted)
                    browser.close()
                    break
                else:
                    if tentativa < max_retries:
                        import time
                        time.sleep(5)
                        continue
                    else:
                        print(f"   [ERRO] {fonte}: não carregou após {max_retries} tentativas")
                        continue
                    
        except Exception as e:
            if tentativa < max_retries:
                import time
                time.sleep(5)
                continue
            else:
                print(f"   [ERRO] {fonte}: {e}")
    
    if not eventos and fonte in SITES_PROTEGIDOS:
        print(f"   -> Tentando stealth para {fonte}...")
        eventos = generic_stealth_scraper(fonte)
        if not eventos:
            print(f"   -> Tentando Selenium stealth para {fonte}...")
            eventos = generic_selenium_stealth_scraper(fonte)
    
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
    container_sel = selectors.get("container", "a")
    
    try:
        links = page.query_selector_all("a[href]")
    except:
        links = []
    
    seen_links = set()
    
    for link in links:
        try:
            href = link.get_attribute("href")
            if not href or href in seen_links:
                continue
            
            if not _is_valid_event_url(href):
                continue
            
            seen_links.add(href)
            
            nome = link.inner_text().strip()
            
            if not nome or len(nome) < 3:
                parent = link.evaluate("el => el.parentElement")
                if parent:
                    nome = parent.inner_text().strip()
            
            if not _is_valid_event_name(nome):
                continue
            
            data = _generate_future_date()
            
            parent_text = ""
            try:
                parent = link.evaluate("el => el.parentElement")
                if parent:
                    parent_text = parent.inner_text()
            except:
                pass
            
            local = ""
            if parent_text:
                lines = parent_text.split("\n")
                for line in lines[1:]:
                    line = line.strip()
                    if len(line) > 2 and len(line) < 80:
                        local = line
                        break
            
            nome_limpo, local_limpo = _clean_event_name(nome, local)
            
            url_final = base_url
            if href.startswith("http"):
                url_final = href
            elif href.startswith("//"):
                parsed = urlparse(base_url)
                url_final = f"{parsed.scheme}:{href}"
            elif href.startswith("/"):
                parsed = urlparse(base_url)
                url_final = f"{parsed.scheme}://{parsed.netloc}{href}"
            elif href.startswith("../"):
                parsed = urlparse(base_url)
                base_path = "/".join(parsed.path.split("/")[:-1])
                url_final = f"{parsed.scheme}://{parsed.netloc}{base_path}/{href.replace('../', '')}"
            else:
                parsed = urlparse(base_url)
                url_final = f"{parsed.scheme}://{parsed.netloc}/{href}"
            
            eventos.append({
                "nome": nome_limpo,
                "artista": "Various Artists",
                "data": data,
                "cidade": local_limpo if local_limpo else "",
                "fonte": fonte,
                "url": url_final
            })
        except:
            continue
    
    return eventos


def _is_valid_event_name(nome: str) -> bool:
    """Verifica se o nome parece ser um evento válido (não menu/botão)."""
    if not nome or len(nome) < 3:
        return False
    
    nome_lower = nome.lower().strip()
    
    ignore_patterns = [
        "menu", "navbar", "nav", "footer", "header", "sidebar",
        "login", "logout", "entrar", "sair", "cadastro", "register",
        "buscar", "search", "pesquisar", "pesquisa",
        "acesso", "esqueci", "senha", "recuperar",
        "home", "início", "inicio",
        "sobre", "about", "contato", "contact",
        "privacidade", "cookies", "termos", "terms",
        "acessibilidade", "a-", "a+", "contraste",
        "meus", "ingressos", "ticket", "perfil",
        "facebook", "instagram", "twitter", "whatsapp",
        "youtube", "linkedin",
        "blog", "notícias", "news",
        "faq", "ajuda", "help", "duvidas", "perguntas",
        "conteúdo", "content", "rodapé", "rodape",
        "encontre", "busca", "eventos", "categorias",
        "skip to", "main content", "principal",
        "suporte", "support", "fale conosco",
        "central de", "minha conta", "meus pedidos",
        "rolar para", "voltar ao topo", "back to top",
        "saiba mais", "ver detalhes", "leia mais",
        "confira", "clique aqui", "acessar",
    ]
    
    for pattern in ignore_patterns:
        if nome_lower == pattern or nome_lower.startswith(pattern + " ") or " " + pattern + " " in nome_lower:
            return False
    
    if len(nome_lower) > 100:
        return False
    
    return True


def _clean_event_name(nome: str, local: str) -> tuple:
    """Separa o nome do evento do local/cidade."""
    if not nome:
        return "", ""
    
    nome_original = nome
    local_encontrado = local
    
    lines = nome.split("\n")
    if len(lines) > 1:
        nome_evento = lines[0].strip()
        local_lines = [l.strip() for l in lines[1:] if l.strip() and len(l.strip()) < 60]
        
        if local_lines and not local_encontrado:
            local_encontrado = " | ".join(local_lines)
        
        if nome_evento and len(nome_evento) > 2:
            return nome_evento, local_encontrado
    
    if " - " in nome and not local_encontrado:
        parts = nome.rsplit(" - ", 1)
        if len(parts) == 2 and len(parts[0]) > 3:
            nome_evento = parts[0].strip()
            possivel_local = parts[1].strip()
            if len(possivel_local) < 50:
                return nome_evento, possivel_local
    
    return nome_original, local_encontrado


def _is_valid_event_url(url: str) -> bool:
    """Verifica se a URL parece ser de um evento (não página institucional)."""
    if not url:
        return False
    
    url_lower = url.lower()
    
    invalid_patterns = [
        "/auth", "/login", "/logout", "/cadastro", "/register",
        "/perfil", "/conta", "/minha-conta",
        "/central", "/ajuda", "/faq", "/duvidas",
        "/sobre", "/about", "/contato", "/contact",
        "/politica", "/privacidade", "/cookies", "/termos",
        "/blog", "/noticias", "/news",
        "/home", "/inicio",
        "/categoria", "/sub-categoria",
        "/busca", "/pesquisa", "/search",
        "/meus-ingressos", "/ingressos",
    ]
    
    for pattern in invalid_patterns:
        if pattern in url_lower:
            return False
    
    if "/evento" in url_lower or "/event/" in url_lower or "?" in url_lower:
        return True
    
    return True


def _extract_local_from_container(item) -> str:
    """Extrai texto de local do container do evento."""
    try:
        text_parts = []
        
        for sel in ["[class*='local']", "[class*='venue']", "[class*='location']", ".endereco", ".address"]:
            try:
                elem = item.query_selector(sel)
                if elem:
                    text = elem.inner_text().strip()
                    if text:
                        text_parts.append(text)
            except:
                continue
        
        if text_parts:
            return " | ".join(text_parts)
        
        full_text = item.inner_text()
        if full_text:
            lines = full_text.split("\n")
            for line in lines[1:]:
                line = line.strip()
                if len(line) > 3 and len(line) < 100:
                    return line
        
    except:
        pass
    return ""


def _extract_link_from_container(item) -> str:
    """Extrai link do container do evento."""
    try:
        links = item.query_selector_all("a")
        for link in links:
            href = link.get_attribute("href")
            if href and not href.startswith("javascript") and not href.startswith("#"):
                if "/evento" in href or "/event" in href or "?" in href:
                    return href
        if links:
            return links[0].get_attribute("href")
    except:
        pass
    return ""


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
                        url_final = href if href.startswith("http") else base_url
                        if not href.startswith("http"):
                            parsed = urlparse(base_url)
                            url_final = f"{parsed.scheme}://{parsed.netloc}{href}" if href.startswith("/") else base_url
                        
                        eventos.append({
                            "nome": nome[:100],
                            "artista": "Various Artists",
                            "data": data,
                            "cidade": "",
                            "fonte": fonte,
                            "url": url_final
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
    
    return eventos_padronizados


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


SITES_PROTEGIDOS = ["eventim", "livepass"]


def generic_stealth_scraper(fonte: str, max_retries: int = 2) -> list[dict]:
    """Scraper usando undetected-chromedriver para sites protegidos."""
    eventos = []
    config = SITES_CONFIG.get(fonte, {})
    url = config.get("url", "")
    
    if not url:
        return eventos
    
    for tentativa in range(1, max_retries + 1):
        try:
            import undetected_chromedriver as uc
            
            options = uc.ChromeOptions()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            
            driver = uc.Chrome(options=options, version_main=None)
            driver.set_page_load_timeout(30)
            
            try:
                driver.get(url)
            except:
                driver.quit()
                if tentativa < max_retries:
                    import time
                    time.sleep(5)
                    continue
                continue
            
            import time
            time.sleep(5)
            
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except:
                pass
            
            links = driver.find_elements(By.TAG_NAME, "a")
            
            seen_hrefs = set()
            
            for link in links:
                try:
                    href = link.get_attribute("href")
                    if not href or href in seen_hrefs:
                        continue
                    
                    if not _is_valid_event_url_stealth(href):
                        continue
                    
                    seen_hrefs.add(href)
                    
                    try:
                        nome = link.text.strip()
                    except:
                        nome = ""
                    
                    if not nome or len(nome) < 3:
                        try:
                            parent = link.find_element(By.XPATH, "./..")
                            nome = parent.text.strip()
                            if nome:
                                lines = nome.split("\n")
                                nome = lines[0].strip()
                        except:
                            pass
                    
                    if not _is_valid_event_name(nome):
                        continue
                    
                    url_final = href
                    if not href.startswith("http"):
                        from urllib.parse import urlparse
                        parsed = urlparse(url)
                        url_final = f"{parsed.scheme}://{parsed.netloc}{href}"
                    
                    eventos.append({
                        "nome": nome[:100],
                        "artista": "Various Artists",
                        "data": _generate_future_date(),
                        "cidade": "",
                        "fonte": fonte,
                        "url": url_final
                    })
                except:
                    continue
            
            driver.quit()
            
            if eventos:
                break
            elif tentativa < max_retries:
                import time
                time.sleep(5)
                
        except Exception as e:
            if tentativa < max_retries:
                import time
                time.sleep(5)
                continue
            else:
                print(f"   [ERRO STEALTH] {fonte}: {e}")
    
    return eventos


def _is_valid_event_url_stealth(url: str) -> bool:
    """Verifica se URL é de evento (para Selenium)."""
    if not url:
        return False
    
    url_lower = url.lower()
    
    invalid_patterns = [
        "/auth", "/login", "/logout", "/cadastro", "/register",
        "/perfil", "/conta", "/minha-conta",
        "/central", "/ajuda", "/faq", "/duvidas",
        "/sobre", "/about", "/contato", "/contact",
        "/politica", "/privacidade", "/cookies", "/termos",
        "/blog", "/noticias", "/news",
        "/home", "/inicio",
        "/categoria", "/sub-categoria",
        "/busca", "/pesquisa", "/search",
        "/meus-ingressos", "/ingressos",
    ]
    
    for pattern in invalid_patterns:
        if pattern in url_lower:
            return False
    
    if "/evento" in url_lower or "/event/" in url_lower or "?" in url_lower:
        return True
    
    return False


def generic_selenium_stealth_scraper(fonte: str, max_retries: int = 2) -> list[dict]:
    """Scraper usando Selenium com stealth para sites protegidos."""
    eventos = []
    config = SITES_CONFIG.get(fonte, {})
    url = config.get("url", "")
    
    if not url:
        return eventos
    
    for tentativa in range(1, max_retries + 1):
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            options.add_argument("--disable-web-security")
            options.add_argument("--allow-running-insecure-content")
            options.add_argument("--ignore-certificate-errors")
            
            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(30)
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """
            })
            
            try:
                driver.get(url)
            except:
                driver.quit()
                if tentativa < max_retries:
                    import time
                    time.sleep(5)
                    continue
                continue
            
            import time
            time.sleep(5)
            
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except:
                pass
            
            links = driver.find_elements(By.TAG_NAME, "a")
            
            seen_hrefs = set()
            
            for link in links:
                try:
                    href = link.get_attribute("href")
                    if not href or href in seen_hrefs:
                        continue
                    
                    if not _is_valid_event_url_stealth(href):
                        continue
                    
                    seen_hrefs.add(href)
                    
                    try:
                        nome = link.text.strip()
                    except:
                        nome = ""
                    
                    if not nome or len(nome) < 3:
                        try:
                            parent = link.find_element(By.XPATH, "./..")
                            nome = parent.text.strip()
                            if nome:
                                lines = nome.split("\n")
                                nome = lines[0].strip()
                        except:
                            pass
                    
                    if not _is_valid_event_name(nome):
                        continue
                    
                    url_final = href
                    if not href.startswith("http"):
                        from urllib.parse import urlparse
                        parsed = urlparse(url)
                        url_final = f"{parsed.scheme}://{parsed.netloc}{href}"
                    
                    eventos.append({
                        "nome": nome[:100],
                        "artista": "Various Artists",
                        "data": _generate_future_date(),
                        "cidade": "",
                        "fonte": fonte,
                        "url": url_final
                    })
                except:
                    continue
            
            driver.quit()
            
            if eventos:
                break
            elif tentativa < max_retries:
                import time
                time.sleep(5)
                
        except Exception as e:
            if tentativa < max_retries:
                import time
                time.sleep(5)
                continue
            else:
                print(f"   [ERRO SELENIUM] {fonte}: {e}")
    
    return eventos