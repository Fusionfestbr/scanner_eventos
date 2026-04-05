"""
Módulo de execução semi-automática.
Gera links diretos de compra validados para oportunidades detectadas.
"""
import requests
import json
import os
import time
from typing import Optional, Dict, List
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
from config import LLM_WORKERS

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}

CACHE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "links_cache.json")
MAX_VALIDACOES = 3
LINK_TIMEOUT = 5


def carregar_cache() -> dict:
    """Carrega cache de links validados."""
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def salvar_cache(cache: dict) -> None:
    """Salva cache de links validados."""
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def validar_link(url: str) -> bool:
    """
    Valida se link está ativo.
    
    Args:
        url: URL para validar
    
    Returns:
        True se link retorna 200-299
    """
    if not url or not url.startswith("http"):
        return False
    
    cache = carregar_cache()
    if url in cache:
        return cache[url]
    
    try:
        response = requests.head(url, headers=HEADERS, timeout=LINK_TIMEOUT, allow_redirects=True)
        valido = 200 <= response.status_code < 300
        
        cache[url] = valido
        salvar_cache(cache)
        return valido
    except requests.exceptions.RequestException:
        cache[url] = False
        salvar_cache(cache)
        return False


def buscar_links_viagogo(nome_evento: str) -> List[dict]:
    """Busca links do Viagogo."""
    if not PLAYWRIGHT_AVAILABLE:
        return []
    
    links = []
    base_url = "https://www.viagogo.com.br"
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_timeout(15000)
            
            search_url = f"{base_url}/?SearchText={nome_evento.replace(' ', '+')}"
            page.goto(search_url, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            
            resultados = page.query_selector_all("a[href*='/event/']")
            
            for link_elem in resultados[:3]:
                try:
                    href = link_elem.get_attribute("href")
                    if href and "/event/" in href:
                        url_completa = href if href.startswith("http") else f"{base_url}{href}"
                        links.append({
                            "plataforma": "viagogo",
                            "url": url_completa,
                            "preco": 0
                        })
                except Exception:
                    continue
            
            page.wait_for_timeout(500)
            
            precos = page.query_selector_all("text=R$")
            for i, el in enumerate(precos[:3]):
                if i < len(links):
                    try:
                        texto = el.inner_text()
                        preco_match = re.search(r'R\$\s*([\d.,]+)', texto)
                        if preco_match:
                            preco_str = preco_match.group(1).replace('.', '').replace(',', '.')
                            links[i]["preco"] = float(preco_str)
                    except Exception:
                        pass
            
            browser.close()
    except Exception:
        pass
    
    return links


def buscar_links_buyticketbrasil(nome_evento: str) -> List[dict]:
    """Busca links do Buy Ticket Brasil."""
    if not PLAYWRIGHT_AVAILABLE:
        return []
    
    links = []
    base_url = "https://buyticketbrasil.com"
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_timeout(15000)
            
            search_url = f"{base_url}/?s={nome_evento.replace(' ', '+')}"
            page.goto(search_url, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            
            resultados = page.query_selector_all("a[href*='/produto/']")
            
            for link_elem in resultados[:3]:
                try:
                    href = link_elem.get_attribute("href")
                    if href:
                        url_completa = href if href.startswith("http") else f"{base_url}{href}"
                        links.append({
                            "plataforma": "buyticketbrasil",
                            "url": url_completa,
                            "preco": 0
                        })
                except Exception:
                    continue
            
            precos = page.query_selector_all("text=R$")
            for i, el in enumerate(precos[:3]):
                if i < len(links):
                    try:
                        texto = el.inner_text()
                        preco_match = re.search(r'R\$\s*([\d.,]+)', texto)
                        if preco_match:
                            preco_str = preco_match.group(1).replace('.', '').replace(',', '.')
                            links[i]["preco"] = float(preco_str)
                    except Exception:
                        pass
            
            browser.close()
    except Exception:
        pass
    
    return links


def buscar_links_revenda(nome_evento: str) -> List[dict]:
    """Busca links de todas as plataformas de revenda em paralelo."""
    links = []
    
    def buscar_viagogo():
        return buscar_links_viagogo(nome_evento)
    
    def buscar_buyticket():
        return buscar_links_buyticketbrasil(nome_evento)
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        f_viagogo = executor.submit(buscar_viagogo)
        f_buyticket = executor.submit(buscar_buyticket)
        
        links.extend(f_viagogo.result(timeout=30))
        links.extend(f_buyticket.result(timeout=30))
    
    return links


def validar_links(lista_links: List[dict]) -> List[dict]:
    """Valida lista de links e retorna apenas os válidos."""
    links_validos = []
    
    for link in lista_links[:MAX_VALIDACOES]:
        url = link.get("url", "")
        if url and validar_link(url):
            links_validos.append(link)
    
    return links_validos


def selecionar_melhor_link(oficial_url: str, links_revenda: List[dict]) -> dict:
    """
    Seleciona melhor link (válido + menor preço).
    
    Args:
        oficial_url: URL oficial do evento
        links_revenda: Lista de links de revenda
    
    Returns:
        Dicionário com melhor link selecionado
    """
    candidatos = []
    
    if oficial_url and validar_link(oficial_url):
        candidatos.append({
            "plataforma": "oficial",
            "url": oficial_url,
            "preco": 0,
            "tipo": "oficial"
        })
    
    links_validos = validar_links(links_revenda)
    for link in links_validos:
        link["tipo"] = "revenda"
        candidatos.append(link)
    
    if not candidatos:
        return {
            "url": oficial_url if oficial_url else "",
            "plataforma": "oficial",
            "preco": 0,
            "valido": False
        }
    
    candidatos.sort(key=lambda x: x.get("preco", 999999))
    melhor = candidatos[0]
    
    return {
        "url": melhor["url"],
        "plataforma": melhor["plataforma"],
        "preco": melhor.get("preco", 0),
        "tipo": melhor["tipo"],
        "valido": True
    }


def determinar_prioridade(nota: float, score: float, prob_esgotar: int) -> str:
    """Determina prioridade da execução."""
    if nota >= 8.5 and score >= 8:
        return "alta"
    elif nota >= 7.5 and score >= 7:
        return "média"
    else:
        return "baixa"


def gerar_execucao_real(
    evento: dict,
    analise: Optional[dict] = None,
    previsao: Optional[dict] = None,
    plano_acao: Optional[dict] = None
) -> dict:
    """
    Gera dados para execução real de compra.
    
    Args:
        evento: Dicionário do evento
        analise: Dados da análise (opcional)
        previsao: Dados da previsão (opcional)
        plano_acao: Plano de ação gerado (opcional)
    
    Returns:
        Dicionário com dados de execução
    """
    nome = evento.get("nome", "")
    oficial_url = evento.get("url", "")
    
    if not nome:
        return {
            "disponivel": False,
            "motivo": "Evento sem nome"
        }
    
    nota = analise.get("nota_final", 0) if analise else 0
    score = previsao.get("score_valorizacao", 0) if previsao else 0
    prob_esgotar = previsao.get("probabilidade_esgotar", 0) if previsao else 0
    
    quantidade = 1
    if plano_acao and plano_acao.get("quantidade"):
        qt = plano_acao["quantidade"]
        quantidade = qt.get("recomendado", qt.get("min", 1))
    
    links_revenda = buscar_links_revenda(nome)
    
    melhor_link = selecionar_melhor_link(oficial_url, links_revenda)
    
    prioridade = determinar_prioridade(nota, score, prob_esgotar)
    
    urgencia = prob_esgotar >= 70 or prioridade == "alta"
    
    return {
        "disponivel": True,
        "acao": "COMPRAR",
        "quantidade": quantidade,
        "link_direto": melhor_link["url"],
        "melhor_plataforma": melhor_link["plataforma"],
        "preco_estimado": melhor_link.get("preco", 0),
        "prioridade": prioridade,
        "urgencia": urgencia,
        "links": {
            "oficial": oficial_url,
            "revenda": links_revenda
        },
        "nota": nota,
        "score": score,
        "probabilidade_esgotar": prob_esgotar
    }


def gerar_link_telegram(url: str, texto: str = "COMPRAR AGORA") -> str:
    """Gera link formatado para Telegram (Markdown)."""
    if not url:
        return ""
    return f"[{texto}]({url})"


def limpar_cache() -> None:
    """Limpa cache de links validados."""
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)


def status_cache() -> dict:
    """Retorna status do cache."""
    cache = carregar_cache()
    validos = sum(1 for v in cache.values() if v)
    return {
        "total_links": len(cache),
        "validos": validos,
        "invalidos": len(cache) - validos
    }