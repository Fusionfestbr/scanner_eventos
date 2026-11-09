import requests

from agents.nome_parser import evento_padrao

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
    """Transforma evento da Livepass para o schema canônico do pipeline."""
    categories = item.get("categories", [])

    categoria = ""
    if len(categories) > 1:
        categoria = categories[1].get("name", "")
    elif categories:
        categoria = categories[0].get("name", "")

    # Link pode vir relativo ("/event/xyz") — normaliza para URL absoluta
    link = item.get("link", "") or ""
    if link and not link.startswith("http"):
        if link.startswith("//"):
            link = "https:" + link
        elif link.startswith("/"):
            link = "https://www.livepass.com.br" + link

    return evento_padrao(
        nome=item.get("name", ""),
        data=item.get("startDate", ""),
        preco=item.get("price", 0),
        imagem=item.get("imageUrl", ""),
        url=link,
        fonte="livepass",
        event_id=item.get("productGroupId", ""),
        categoria_fonte=categoria,
    )
