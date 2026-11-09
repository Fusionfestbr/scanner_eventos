"""
Agente coletor de eventos.

Estratégia de coleta:
    1. APIs JSON quando disponíveis (rápidas e ricas: cidade, estado,
       local, imagem e, quando há, preço)
    2. Scraper (Playwright/Selenium) complementar, só para fontes sem API
    3. Enriquecimento pelo título (artista/cidade/data embutidos no nome)
    4. Dedup global entre fontes

SEM FALLBACK — devolve apenas dados reais ou lista vazia.
"""
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed

from agents.nome_parser import enriquecer_do_nome
from agents.scraper import buscar_eventos_reais
from config import MAX_EVENTOS_POR_FONTE


# Fontes com API JSON dedicada (agents.<fonte>_api, função get_<fonte>_events)
_API_AGENTES = [
    "ingresse",
    "eventim",
    "livepass",
    "q2ingressos",
    "zigtickets",
    "guicheweb",
]

# Fontes sem API — sempre vão para o scraper
FONTES_SCRAPER = [
    "ticketmaster",
    "sympla",
    "ticket360",
    "blueticket",
    "bilheteriadigital",
    "ticketsforfun",
    "uhuu",
    "betimelapse",
]


def _sem_acentos(texto: str) -> str:
    if not texto:
        return ""
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))


def _chave_dedup(evento: dict) -> str:
    """Chave de deduplicação: nome (sem acento) + dia."""
    nome = _sem_acentos((evento.get("nome") or "").lower()).strip()
    nome = re.sub(r"\s+", " ", nome)
    data = (evento.get("data") or "")[:10]
    return f"{nome}|{data}"


def _coletar_via_api(fonte: str) -> list[dict]:
    """Importa agents.<fonte>_api e chama get_<fonte>_events()."""
    try:
        modulo = __import__(f"agents.{fonte}_api", fromlist=["_"])
        funcao = getattr(modulo, f"get_{fonte}_events", None)
        if funcao is None:
            return []
        return funcao() or []
    except Exception as e:
        print(f"   [ERRO] API {fonte}: {e}")
        return []


def coletar_eventos() -> list[dict]:
    """
    Coleta eventos de todas as fontes:

        APIs em paralelo -> scraper nas fontes sem API ->
        enriquecimento pelo título -> dedup global.
    """
    print("   Coletando eventos (6 APIs em paralelo)...")
    eventos: list[dict] = []

    with ThreadPoolExecutor(max_workers=len(_API_AGENTES)) as executor:
        futures = {executor.submit(_coletar_via_api, fonte): fonte for fonte in _API_AGENTES}
        for future in as_completed(futures):
            fonte = futures[future]
            try:
                lista = future.result()
                print(f"   - {fonte}: {len(lista)} eventos")
                eventos.extend(lista)
            except Exception as e:
                print(f"   [ERRO] {fonte}: {e}")

    print("   Coletando fontes sem API (scraper)...")
    eventos_scraper = buscar_eventos_reais(fontes=FONTES_SCRAPER)
    print(f"   - scraper: {len(eventos_scraper)} eventos")
    eventos.extend(eventos_scraper)

    # Enriquecimento: artista/cidade/data embutidos no título
    eventos = [enriquecer_do_nome(e) for e in eventos]

    # Dedup global (mesmo nome + mesmo dia, em qualquer fonte)
    vistos: set[str] = set()
    unicos: list[dict] = []
    for e in eventos:
        chave = _chave_dedup(e)
        if not nome_chave_valida(chave) or chave in vistos:
            continue
        vistos.add(chave)
        unicos.append(e)
    eventos = unicos

    # Limite por fonte (config), se configurado
    if MAX_EVENTOS_POR_FONTE > 0:
        contagem: dict[str, int] = {}
        limitados = []
        for e in eventos:
            fonte = e.get("fonte", "")
            contagem[fonte] = contagem.get(fonte, 0) + 1
            if contagem[fonte] <= MAX_EVENTOS_POR_FONTE:
                limitados.append(e)
        eventos = limitados

    if not eventos:
        print("   [ALERTA] Nenhum evento encontrado na varredura")
        print("   [INFO] Pipeline continua vazio (sem fallback)")

    return eventos


def nome_chave_valida(chave: str) -> bool:
    """Chave sem nome não é deduplicável."""
    return bool(chave and chave.split("|")[0])
