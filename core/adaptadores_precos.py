"""
Adaptadores de preço/esgotado por plataforma (preços no painel).

Roteamento por domínio em verificar_evento():

  zig.tickets   -> HTTP puro: página do evento em Markdown com seção
                   "## Ingressos" (preço, taxa, setor) e "Status:" de venda
  q2ingressos / ingresse / blueticket / sympla (SPA)
                -> Playwright: renderiza a página e extrai do HTML/texto final
  demais        -> None (o monitor_precos usa sua camada estática:
                   JSON-LD > itemprop > regex "R$")

Retorno padronizado do adaptador:
  {preco, esgotado, cancelado, status, erro, camada}
"""
import re
import threading
from urllib.parse import urlparse

import requests

from core.monitor_precos import (
    HEADERS,
    MONITOR_TIMEOUT,
    MIN_PRECO,
    MAX_PRECO,
    PALAVRAS_ESGOTADO,
    _jsonld_dados,
    _norm,
    _parse_br,
    _preco_regex,
    _RE_ITEMPROP,
    extrair_esgotado,
)

# SPAs: sem preço no HTML estático — só com render
DOMINIOS_PLAYWRIGHT = (
    "q2ingressos.com.br",
    "ingresse.com",
    "blueticket.com.br",
    "sympla.com.br",
)

# Playwright é pesado (1 chromium por chamada): limita páginas simultâneas
PLAYWRIGHT_CONCORRENCIA = int(__import__("os").environ.get("RADAR_PLAYWRIGHT_CONCORRENCIA", "3"))
PLAYWRIGHT_TIMEOUT_S = int(__import__("os").environ.get("RADAR_PLAYWRIGHT_TIMEOUT", "30"))
# espera de hidratação da SPA antes de extrair (ms)
PLAYWRIGHT_ESPERA_MS = int(__import__("os").environ.get("RADAR_PLAYWRIGHT_ESPERA_MS", "5000"))

_SEM_PLAYWRIGHT = threading.Semaphore(PLAYWRIGHT_CONCORRENCIA)

# "Geral [Inteira] Único: R$ 100,00 + R$ 10,00 de taxa - setor Geral"
_RE_ZIG_LINHA_PRECO = re.compile(r"R\$\s*([\d.,]+)")
_RE_ZIG_TAXA = re.compile(r"R\$\s*[\d.,]+\s*de\s+taxa", re.I)


# ==================== ROTEAMENTO ====================

def _dominio(url: str) -> str:
    try:
        return (urlparse(url).netloc or "").lower().replace("www.", "")
    except ValueError:
        return ""


def verificar_evento(url: str, nome: str = None):
    """Rotas com adaptador específico devolvem o resultado; demais -> None
    (o monitor_precos cai para a extração estática original)."""
    if not url:
        return None
    dom = _dominio(url)
    if dom == "zig.tickets":
        return _zig_verificar(url, nome)
    for dom_pw in DOMINIOS_PLAYWRIGHT:
        if dom == dom_pw or dom.endswith("." + dom_pw):
            return _playwright_verificar(url, nome)
    return None


# ==================== ZIG (Markdown) ====================

def _zig_url_eventos(url: str) -> str:
    """Força a rota correta /eventos/ (links antigos /event/ davam 404)."""
    return url.replace("zig.tickets/event/", "zig.tickets/eventos/")


def _zig_secao_ingressos(md: str) -> str:
    m = re.search(r"(?ms)^##\s*Ingressos\s*$\n(.*?)(?=^##\s|\Z)", md)
    return m.group(1) if m else ""


def _zig_markdown_dados(md: str) -> dict:
    """Extrai {preco, esgotado, cancelado} do markdown da página do evento.

    preco = menor preço-base dos ingressos listados (sem a taxa).
    esgotado = status de venda encerrada/esgotada ou 0 ingressos listados
    num evento com seção "## Ingressos" vazia.
    """
    out = {"preco": None, "esgotado": False, "cancelado": False}
    md_norm = _norm(md)

    if "cancelad" in md_norm or "postergad" in md_norm:
        out["cancelado"] = True

    st = re.search(r"(?m)^\s*-\s*Status:\s*(.+)$", md)
    status_txt = _norm(st.group(1)) if st else ""
    if status_txt and ("esgotad" in status_txt or "vendas encerradas" in status_txt
                       or "encerradas" in status_txt):
        out["esgotado"] = True

    secao = _zig_secao_ingressos(md)
    if secao:
        precos = []
        for linha in secao.splitlines():
            if "R$" not in linha:
                continue
            # preço-base = primeiro R$ da linha que NÃO seja "de taxa"
            sem_taxa = _RE_ZIG_TAXA.sub("", linha)
            m = _RE_ZIG_LINHA_PRECO.search(sem_taxa)
            if not m:
                continue
            p = _parse_br(m.group(1))
            if p and MIN_PRECO <= p <= MAX_PRECO:
                precos.append(p)
        if precos:
            out["preco"] = min(precos)
        elif not out["esgotado"]:
            # seção existe mas nenhum ingresso com preço: sem estoque
            out["esgotado"] = True

    # palavras fortes de esgotamento em qualquer lugar (com status/ingressos)
    if not out["esgotado"] and any(_norm(p) in md_norm for p in PALAVRAS_ESGOTADO):
        out["esgotado"] = True
    return out


def _zig_verificar(url: str, nome: str = None) -> dict:
    resultado = {"preco": None, "esgotado": False, "cancelado": False,
                 "status": None, "erro": None, "camada": "zig-markdown"}
    try:
        resp = requests.get(_zig_url_eventos(url), headers={
            **HEADERS, "Accept": "text/markdown",
        }, timeout=MONITOR_TIMEOUT)
        resultado["status"] = resp.status_code
        if resp.status_code != 200:
            resultado["erro"] = f"HTTP {resp.status_code}"
            return resultado
        texto = resp.text
        if texto.lstrip().startswith("<"):
            # veio HTML em vez de markdown: usa extração estática genérica
            return _extrair_estatico(texto, nome, camada="zig-html")
        resultado.update(_zig_markdown_dados(texto))
    except requests.exceptions.RequestException as e:
        resultado["erro"] = str(e)[:120]
    except Exception as e:
        resultado["erro"] = str(e)[:120]
    return resultado


# ==================== ESTÁTICO (HTML já baixado) ====================

def _extrair_estatico(texto: str, nome: str = None, camada: str = "estatico") -> dict:
    """JSON-LD > itemprop > regex 'R$' — mesma ordem do monitor_precos."""
    resultado = {"preco": None, "esgotado": False, "cancelado": False,
                 "status": None, "erro": None, "camada": camada}
    estrut = _jsonld_dados(texto)
    if estrut["precos"]:
        resultado["preco"] = min(estrut["precos"])
    if resultado["preco"] is None:
        for match in _RE_ITEMPROP.finditer(texto):
            p = _parse_br(match.group(1))
            if p and MIN_PRECO <= p <= MAX_PRECO:
                resultado["preco"] = p
                break
    if resultado["preco"] is None:
        resultado["preco"] = _preco_regex(texto)
    resultado["esgotado"] = bool(estrut["soldout"]) or extrair_esgotado(texto, nome)
    resultado["cancelado"] = estrut["cancelado"]
    return resultado


# ==================== PLAYWRIGHT (SPAs) ====================

def _playwright_verificar(url: str, nome: str = None) -> dict:
    resultado = {"preco": None, "esgotado": False, "cancelado": False,
                 "status": None, "erro": None, "camada": "playwright"}
    try:
        with _SEM_PLAYWRIGHT:
            html, texto_visivel = _renderizar(url)
    except Exception as e:
        resultado["erro"] = str(e)[:120]
        return resultado

    resultado["status"] = 200
    resultado.update(_extrair_de_render(html, texto_visivel, nome))
    return resultado


def _renderizar(url: str) -> tuple:
    """Renderiza a SPA e devolve (html_final, texto_visivel)."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(user_agent=HEADERS["User-Agent"],
                                    viewport={"width": 1280, "height": 900})
            page.set_default_timeout(PLAYWRIGHT_TIMEOUT_S * 1000)
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(PLAYWRIGHT_ESPERA_MS)
            return page.content(), page.inner_text("body")
        finally:
            browser.close()


def _extrair_de_render(html: str, texto_visivel: str, nome: str = None) -> dict:
    """Extrai preço/esgotado do HTML renderizado + texto visível da SPA.

    JSON-LD injetado no cliente aparece no page.content(); preços renderizados
    ("R$ 290,00" no DOM) aparecem no inner_text — ambos são varridos.
    """
    out = _extrair_estatico(html, nome, camada="playwright")
    # preço no texto visível (fallback quando JSON-LD não existe)
    if out["preco"] is None and texto_visivel:
        out["preco"] = _preco_regex(texto_visivel)
    # esgotado no texto visível (badges renderizados), com guarda do nome
    if not out["esgotado"] and texto_visivel:
        out["esgotado"] = extrair_esgotado(texto_visivel, nome)
    return out
