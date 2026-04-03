"""
Agente de scraping para coletar eventos de fontes reais.
"""
import json
import re
import requests
from datetime import datetime
from bs4 import BeautifulSoup

from config import SCRAPER_TIMEOUT, SCRAPER_RETRY
from core.data_quality import extrair_data_de_texto


def buscar_sympla() -> list[dict]:
    """Busca eventos do Sympla."""
    eventos = []
    urls = [
        "https://www.sympla.com.br/eventos",
    ]
    
    for url in urls:
        try:
            response = requests.get(url, timeout=SCRAPER_TIMEOUT, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                
                for item in soup.select("[class*='event']"):
                    try:
                        nome = item.select_one("[class*='title']") or item.select_one("h3")
                        data_elem = item.select_one("[class*='date']") or item.select_one("time") or item.select_one("[datetime]")
                        local = item.select_one("[class*='location']") or item.select_one("[class*='venue']") or item.select_one("[itemprop='location']")
                        link = item.select_one("a")
                        
                        if nome:
                            nome_texto = nome.get_text(strip=True)
                            data = ""
                            if data_elem:
                                data = data_elem.get("datetime", "") or data_elem.get("data-date", "") or data_elem.get_text(strip=True)
                                if data:
                                    data = normalizar_data(data)
                            
                            if not data:
                                texto_item = item.get_text(strip=True)
                                data = extrair_data_de_texto(texto_item)
                            
                            eventos.append({
                                "nome": nome_texto,
                                "artista": "Various Artists",
                                "data": data,
                                "cidade": local.get_text(strip=True) if local else "Brasil",
                                "fonte": "sympla",
                                "url": link.get("href", "") if link else url
                            })
                    except Exception:
                        continue
        except Exception as e:
            print(f"   [WARN] Sympla error: {e}")
    
    return eventos


def buscar_eventbrite() -> list[dict]:
    """Busca eventos do Eventbrite."""
    eventos = []
    urls = [
        "https://www.eventbrite.com/d/brazil--rio-de-janeiro/events/",
    ]
    
    for url in urls:
        try:
            response = requests.get(url, timeout=SCRAPER_TIMEOUT, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                
                for item in soup.select("[class*='event-card']"):
                    try:
                        nome = item.select_one("[class*='title']") or item.select_one("h3")
                        data_elem = item.select_one("[class*='date']") or item.select_one("time") or item.select_one("[datetime]")
                        local = item.select_one("[class*='venue']") or item.select_one("[itemprop='location']")
                        link = item.select_one("a")
                        
                        if nome:
                            nome_texto = nome.get_text(strip=True)
                            data = ""
                            if data_elem:
                                data = data_elem.get("datetime", "") or data_elem.get("data-date", "") or data_elem.get_text(strip=True)
                                if data:
                                    data = normalizar_data(data)
                            
                            if not data:
                                texto_item = item.get_text(strip=True)
                                data = extrair_data_de_texto(texto_item)
                            
                            eventos.append({
                                "nome": nome_texto,
                                "artista": "Various Artists",
                                "data": data,
                                "cidade": local.get_text(strip=True) if local else "Brasil",
                                "fonte": "eventbrite",
                                "url": link.get("href", "") if link else url
                            })
                    except Exception:
                        continue
        except Exception as e:
            print(f"   [WARN] Eventbrite error: {e}")
    
    return eventos


def buscar_google_events() -> list[dict]:
    """Busca eventos do Google."""
    eventos = []
    
    query = "concertos Brasil 2026"
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    
    try:
        response = requests.get(url, timeout=SCRAPER_TIMEOUT, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            
            for item in soup.select("div[class*='event']"):
                try:
                    nome = item.select_one("h3") or item.select_one("[class*='title']")
                    data_elem = item.select_one("span[class*='date']")
                    
                    if nome:
                        nome_texto = nome.get_text(strip=True)
                        data = ""
                        if data_elem:
                            data = data_elem.get_text(strip=True)
                            data = normalizar_data(data)
                        
                        if not data:
                            texto_item = item.get_text(strip=True)
                            data = extrair_data_de_texto(texto_item)
                        
                        eventos.append({
                            "nome": nome_texto,
                            "artista": "Various Artists",
                            "data": data,
                            "cidade": "Brasil",
                            "fonte": "google",
                            "url": ""
                        })
                except Exception:
                    continue
    except Exception as e:
        print(f"   [WARN] Google events error: {e}")
    
    return eventos


def buscar_eventos_reais() -> list[dict]:
    """
    Busca eventos de múltiplas fontes.
    
    Returns:
        Lista de eventos padronizados
    """
    print("   Buscando eventos reais...")
    
    eventos = []
    
    print("   - Buscando Sympla...")
    eventos += buscar_sympla()
    
    print("   - Buscando Eventbrite...")
    eventos += buscar_eventbrite()
    
    print("   - Buscando Google...")
    eventos += buscar_google_events()
    
    eventos = padronizar_eventos(eventos)
    
    print(f"   -> Total encontrado: {len(eventos)}")
    
    return eventos


def padronizar_eventos(eventos: list[dict]) -> list[dict]:
    """Padroniza formato dos eventos."""
    eventos_padronizados = []
    
    for evento in eventos:
        nome = evento.get("nome", "").strip()
        if not nome:
            continue
        
        data = evento.get("data", "").strip()
        if data:
            data = normalizar_data(data)
        
        evento_padrao = {
            "nome": nome,
            "artista": evento.get("artista", "Various Artists"),
            "data": data,
            "cidade": evento.get("cidade", "Brasil"),
            "fonte": evento.get("fonte", "web"),
            "url": evento.get("url", "")
        }
        eventos_padronizados.append(evento_padrao)
    
    return eventos_padronizados


def normalizar_data(data_str: str) -> str:
    """Normaliza formato de data para YYYY-MM-DD."""
    if not data_str:
        return ""
    
    data_str = data_str.strip()
    
    data_str = extrair_data_de_texto(data_str)
    if data_str:
        return data_str
    
    formatos = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d"
    ]
    
    meses = {
        "janeiro": "01", "fevereiro": "02", "março": "03", "abril": "04",
        "maio": "05", "junho": "06", "julho": "07", "agosto": "08",
        "setembro": "09", "outubro": "10", "novembro": "11", "dezembro": "12"
    }
    
    for mes_pt, num in meses.items():
        data_str = data_str.lower().replace(mes_pt, num)
    
    for fmt in formatos:
        try:
            dt = datetime.strptime(data_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    return ""
