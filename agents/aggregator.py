import requests
from typing import Optional

API_URL = "https://public-api.eventim.com/websearch/search/api/exploration/v1/productGroups"

PARAMS = {
    "webId": "web__eventim-com-br",
    "language": "PT",
    "retail_partner": "BR1",
    "auto_suggest": "true",
    "sort": "Recommendation",
    "top": 50,
    "tags": "DISABLE_FBS"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

TIMEOUT = 10


def get_eventim_events() -> list[dict]:
    """Busca eventos da API Eventim e retorna no formato padronizado."""
    try:
        response = requests.get(
            API_URL,
            params=PARAMS,
            headers=HEADERS,
            timeout=TIMEOUT
        )

        if response.status_code != 200:
            return []

        data = response.json()
        product_groups = data.get("productGroups", [])

        eventos = []
        for item in product_groups:
            if not item.get("name") or not item.get("startDate"):
                continue

            evento = _transform_eventim(item)
            eventos.append(evento)

        return eventos

    except Exception:
        return []


def _transform_eventim(item: dict) -> dict:
    """Transforma evento do Eventim para formato padronizado."""
    categories = item.get("categories", [])

    categoria = ""
    if len(categories) > 1:
        categoria = categories[1].get("name", "")
    elif categories:
        categoria = categories[0].get("name", "")

    return {
        "source": "eventim",
        "event_id": item.get("productGroupId", ""),
        "name": item.get("name", ""),
        "date": item.get("startDate", ""),
        "city": "",
        "state": "",
        "venue": "",
        "image": item.get("imageUrl", ""),
        "url": item.get("link", "")
    }


def get_ingresse_events() -> list[dict]:
    """Busca eventos da API Ingresse e retorna no formato padronizado."""
    try:
        response = requests.get(
            "https://api-site.ingresse.com/custom-categories/list/events",
            params={"iso_code": "BRA", "language": "pt_br"},
            headers=HEADERS,
            timeout=TIMEOUT
        )

        if response.status_code != 200:
            return []

        data = response.json()

        eventos = []
        for categoria in data:
            for evento in categoria.get("events", []):
                evento_padronizado = _transform_ingresse(evento)
                eventos.append(evento_padronizado)

        return eventos

    except Exception:
        return []


def _transform_ingresse(evento: dict) -> dict:
    """Transforma evento da Ingresse para formato padronizado."""
    place = evento.get("place", {})
    images = evento.get("images", {})

    return {
        "source": "ingresse",
        "event_id": str(evento.get("event_id", "")),
        "name": evento.get("title", ""),
        "date": evento.get("event_date", ""),
        "city": place.get("city", ""),
        "state": place.get("state", ""),
        "venue": place.get("name", ""),
        "image": images.get("large", ""),
        "url": f"https://www.ingresse.com/event/{evento.get('slug', '')}"
    }


def get_livepass_events() -> list[dict]:
    """Busca eventos da API Livepass e retorna no formato padronizado."""
    try:
        response = requests.get(
            "https://public-api.eventim.com/websearch/search/api/exploration/v1/productGroups",
            params={
                "webId": "web__eventim-com-br",
                "language": "PT",
                "retail_partner": "LPS",
                "auto_suggest": "true",
                "sort": "Recommendation",
                "top": 50,
                "tags": "DISABLE_FBS"
            },
            headers={
                "accept": "*/*",
                "oidc-client-id": "web__eventim-com-br",
                "origin": "https://www.livepass.com.br",
                "referer": "https://www.livepass.com.br/",
                "user-agent": "Mozilla/5.0 (Linux; Android 8.0.0; SM-G955U Build/R16NW) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Mobile Safari/537.36",
                "x-requested-with": "XMLHttpRequest"
            },
            timeout=TIMEOUT
        )

        if response.status_code != 200:
            return []

        data = response.json()
        product_groups = data.get("productGroups", [])

        eventos = []
        for item in product_groups:
            if not item.get("name") or not item.get("startDate"):
                continue

            evento = _transform_livepass(item)
            eventos.append(evento)

        return eventos

    except Exception:
        return []


def _transform_livepass(item: dict) -> dict:
    """Transforma evento da Livepass para formato padronizado."""
    categories = item.get("categories", [])

    categoria = ""
    if len(categories) > 1:
        categoria = categories[1].get("name", "")
    elif categories:
        categoria = categories[0].get("name", "")

    return {
        "source": "livepass",
        "event_id": item.get("productGroupId", ""),
        "name": item.get("name", ""),
        "date": item.get("startDate", ""),
        "city": "",
        "state": "",
        "venue": "",
        "image": item.get("imageUrl", ""),
        "url": item.get("link", "")
    }


def get_q2ingressos_events() -> list[dict]:
    """Busca eventos da API Q2 Ingressos e retorna no formato padronizado."""
    try:
        response = requests.get(
            "https://cdn.q2ingressos.com.br/assets/api/nextEvents.json",
            headers={
                "accept": "application/json",
                "origin": "https://q2ingressos.com.br",
                "referer": "https://q2ingressos.com.br/",
                "user-agent": "Mozilla/5.0 (Linux; Android 8.0.0; SM-G955U Build/R16NW) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Mobile Safari/537.36"
            },
            timeout=TIMEOUT
        )

        if response.status_code != 200:
            return []

        data = response.json()

        eventos = []
        for item in data:
            evento = _transform_q2ingressos(item)
            eventos.append(evento)

        return eventos

    except Exception:
        return []


def _transform_q2ingressos(item: dict) -> dict:
    """Transforma evento do Q2 Ingressos para formato padronizado."""
    return {
        "source": "q2ingressos",
        "event_id": str(item.get("Id", "")),
        "name": item.get("Name", ""),
        "date": item.get("StartDate", ""),
        "city": item.get("City", ""),
        "state": item.get("State", ""),
        "venue": item.get("Place", ""),
        "image": item.get("ImageEvent", ""),
        "url": f"https://q2ingressos.com.br/evento/{item.get('Slug', '')}"
    }


def get_zigtickets_events() -> list[dict]:
    """Busca eventos da API Zig Tickets e retorna no formato padronizado."""
    try:
        response = requests.get(
            "https://zigtickets-static-zig-tickets.s3.us-east-1.amazonaws.com/domains/zig.tickets/new-events.json",
            headers={"accept": "application/json"},
            timeout=TIMEOUT
        )

        if response.status_code != 200:
            return []

        data = response.json()
        events = data.get("events", [])

        eventos = []
        for item in events:
            evento = _transform_zigtickets(item)
            eventos.append(evento)

        return eventos

    except Exception:
        return []


def _transform_zigtickets(item: dict) -> dict:
    """Transforma evento do Zig Tickets para formato padronizado."""
    location = item.get("event_location", {})
    banner = item.get("banner") or item.get("thumb") or ""

    return {
        "source": "zigtickets",
        "event_id": str(item.get("id", "")),
        "name": item.get("name", ""),
        "date": item.get("start_date", ""),
        "city": location.get("city", ""),
        "state": location.get("state", ""),
        "venue": location.get("name", ""),
        "image": banner,
        "url": f"https://zig.tickets/event/{item.get('slug', '')}"
    }


def get_guicheweb_events() -> list[dict]:
    """Busca eventos da API GuichêWeb e retorna no formato padronizado."""
    try:
        response = requests.post(
            "https://www.guicheweb.com.br/webservices/api/api.php",
            data={"a": "carregar_home"},
            headers={
                "accept": "application/json",
                "origin": "https://www.guicheweb.com.br",
                "referer": "https://www.guicheweb.com.br/",
                "user-agent": "Mozilla/5.0 (Linux; Android 8.0.0; SM-G955U Build/R16NW) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Mobile Safari/537.36"
            },
            timeout=TIMEOUT
        )

        if response.status_code != 200:
            return []

        data = response.json()
        events = data.get("item_eventos", [])

        eventos = []
        for item in events:
            evento = _transform_guicheweb(item)
            eventos.append(evento)

        return eventos

    except Exception:
        return []


def _transform_guicheweb(item: dict) -> dict:
    """Transforma evento do GuichêWeb para formato padronizado."""
    cidade = item.get("cidade", "")
    cidade_parts = cidade.split("/")
    city = cidade_parts[0] if len(cidade_parts) > 0 else ""
    state = cidade_parts[1] if len(cidade_parts) > 1 else ""

    img = item.get("img", "")
    image = f"https://cdn.guicheweb.com.br/gw-bucket/imagens/eventos/{img}" if img else ""

    return {
        "source": "guicheweb",
        "event_id": item.get("id_evento", ""),
        "name": item.get("nome", ""),
        "date": item.get("data", ""),
        "city": city,
        "state": state,
        "venue": item.get("local", ""),
        "image": image,
        "url": item.get("url_amigavel", "")
    }


def get_all_events() -> list[dict]:
    """Busca eventos de todas as fontes e retorna no formato padronizado."""
    print("\n  Buscando eventos de todas as fontes...")

    eventos = []

    print("  - Eventim...")
    eventim = get_eventim_events()
    print(f"    -> {len(eventim)} eventos")
    eventos.extend(eventim)

    print("  - Ingresse...")
    ingresse = get_ingresse_events()
    print(f"    -> {len(ingresse)} eventos")
    eventos.extend(ingresse)

    print("  - Livepass...")
    livepass = get_livepass_events()
    print(f"    -> {len(livepass)} eventos")
    eventos.extend(livepass)

    print("  - Q2 Ingressos...")
    q2 = get_q2ingressos_events()
    print(f"    -> {len(q2)} eventos")
    eventos.extend(q2)

    print("  - Zig Tickets...")
    zig = get_zigtickets_events()
    print(f"    -> {len(zig)} eventos")
    eventos.extend(zig)

    print("  - GuichêWeb...")
    gw = get_guicheweb_events()
    print(f"    -> {len(gw)} eventos")
    eventos.extend(gw)

    print(f"\n  Total: {len(eventos)} eventos")

    return eventos
