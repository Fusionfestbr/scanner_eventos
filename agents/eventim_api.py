import requests

from agents.nome_parser import evento_padrao

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
    """Busca eventos da API Eventim e retorna no formato interno."""
    try:
        response = requests.get(
            API_URL,
            params=PARAMS,
            headers=HEADERS,
            timeout=TIMEOUT
        )

        if response.status_code != 200:
            print(f"   [ERRO] Eventim API: status {response.status_code}")
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

    except requests.exceptions.Timeout:
        print("   [ERRO] Eventim API: timeout")
        return []
    except Exception as e:
        print(f"   [ERRO] Eventim API: {e}")
        return []


def _transform_event(item: dict) -> dict:
    """Transforma resposta da API para o schema canônico do pipeline."""
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
            link = "https://www.eventim.com.br" + link

    return evento_padrao(
        nome=item.get("name", ""),
        data=item.get("startDate", ""),
        preco=item.get("price", 0),
        url=link,
        imagem=item.get("imageUrl", ""),
        fonte="eventim",
        event_id=item.get("productGroupId", ""),
        categoria_fonte=categoria,
    )
