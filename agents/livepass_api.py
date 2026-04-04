import requests

API_URL = "https://public-api.eventim.com/websearch/search/api/exploration/v1/productGroups"

PARAMS = {
    "webId": "web__eventim-com-br",
    "language": "PT",
    "retail_partner": "LPS",
    "auto_suggest": "true",
    "sort": "Recommendation",
    "top": 50,
    "tags": "DISABLE_FBS"
}

HEADERS = {
    "accept": "*/*",
    "oidc-client-id": "web__eventim-com-br",
    "origin": "https://www.livepass.com.br",
    "referer": "https://www.livepass.com.br/",
    "user-agent": "Mozilla/5.0 (Linux; Android 8.0.0; SM-G955U Build/R16NW) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Mobile Safari/537.36",
    "x-requested-with": "XMLHttpRequest"
}

TIMEOUT = 10


def get_livepass_events() -> list[dict]:
    """Busca eventos da API Livepass e retorna no formato padronizado."""
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

            evento = _transform_event(item)
            eventos.append(evento)

        return eventos

    except Exception:
        return []


def _transform_event(item: dict) -> dict:
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
