import requests

from agents.nome_parser import evento_padrao

API_URL = "https://zigtickets-static-zig-tickets.s3.us-east-1.amazonaws.com/domains/zig.tickets/new-events.json"

HEADERS = {
    "accept": "application/json"
}

TIMEOUT = 10


def get_zigtickets_events() -> list[dict]:
    """Busca eventos da API Zig Tickets e retorna no formato padronizado."""
    try:
        response = requests.get(
            API_URL,
            headers=HEADERS,
            timeout=TIMEOUT
        )

        if response.status_code != 200:
            return []

        data = response.json()
        events = data.get("events", [])

        eventos = []
        for item in events:
            evento = _transform_event(item)
            eventos.append(evento)

        return eventos

    except Exception:
        return []


def _transform_event(item: dict) -> dict:
    """Transforma evento do Zig Tickets para o schema canônico do pipeline."""
    location = item.get("event_location", {})
    banner = item.get("banner") or item.get("thumb") or ""

    return evento_padrao(
        nome=item.get("name", ""),
        data=item.get("start_date", ""),
        cidade=location.get("city", ""),
        estado=location.get("state", ""),
        local=location.get("name", ""),
        imagem=banner,
        # A rota real do site é /eventos/ (com "s"): /event/{slug} dá 404
        url=f"https://zig.tickets/eventos/{item.get('slug', '')}",
        fonte="zigtickets",
        event_id=str(item.get("id", "")),
    )
