import requests

from agents.nome_parser import evento_padrao

API_URL = "https://www.guicheweb.com.br/webservices/api/api.php"

HEADERS = {
    "accept": "application/json",
    "origin": "https://www.guicheweb.com.br",
    "referer": "https://www.guicheweb.com.br/",
    "user-agent": "Mozilla/5.0 (Linux; Android 8.0.0; SM-G955U Build/R16NW) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Mobile Safari/537.36"
}

TIMEOUT = 10


def get_guicheweb_events() -> list[dict]:
    """Busca eventos da API GuichêWeb e retorna no formato padronizado."""
    try:
        response = requests.post(
            API_URL,
            data={"a": "carregar_home"},
            headers=HEADERS,
            timeout=TIMEOUT
        )

        if response.status_code != 200:
            return []

        data = response.json()
        events = data.get("item_eventos", [])

        eventos = []
        for item in events:
            evento = _transform_event(item)
            eventos.append(evento)

        return eventos

    except Exception:
        return []


def _transform_event(item: dict) -> dict:
    """Transforma evento do GuichêWeb para o schema canônico do pipeline."""
    cidade = item.get("cidade", "")
    cidade_parts = cidade.split("/")
    city = cidade_parts[0].strip() if len(cidade_parts) > 0 else ""
    state = cidade_parts[1].strip() if len(cidade_parts) > 1 else ""

    img = item.get("img", "")
    image = f"https://cdn.guicheweb.com.br/gw-bucket/imagens/eventos/{img}" if img else ""

    url_amigavel = item.get("url_amigavel", "") or ""
    if url_amigavel and not url_amigavel.startswith("http"):
        # URL relativa ("/evento/xyz") → absoluta
        url_amigavel = f"https://www.guicheweb.com.br/{url_amigavel.lstrip('/')}"

    return evento_padrao(
        nome=item.get("nome", ""),
        data=item.get("data", ""),
        cidade=city,
        estado=state,
        local=item.get("local", ""),
        imagem=image,
        url=url_amigavel,
        fonte="guicheweb",
        event_id=str(item.get("id_evento", "")),
    )
