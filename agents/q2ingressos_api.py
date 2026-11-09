import requests

from agents.nome_parser import evento_padrao

API_URL = "https://cdn.q2ingressos.com.br/assets/api/nextEvents.json"

HEADERS = {
    "accept": "application/json",
    "origin": "https://q2ingressos.com.br",
    "referer": "https://q2ingressos.com.br/",
    "user-agent": "Mozilla/5.0 (Linux; Android 8.0.0; SM-G955U Build/R16NW) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Mobile Safari/537.36"
}

TIMEOUT = 10


def get_q2ingressos_events() -> list[dict]:
    """Busca eventos da API Q2 Ingressos e retorna no formato padronizado."""
    try:
        response = requests.get(
            API_URL,
            headers=HEADERS,
            timeout=TIMEOUT
        )

        if response.status_code != 200:
            return []

        data = response.json()

        eventos = []
        for item in data:
            evento = _transform_event(item)
            eventos.append(evento)

        return eventos

    except Exception:
        return []


def _transform_event(item: dict) -> dict:
    """Transforma evento do Q2 Ingressos para o schema canônico do pipeline."""
    return evento_padrao(
        nome=item.get("Name", ""),
        data=item.get("StartDate", ""),
        cidade=item.get("City", ""),
        estado=item.get("State", ""),
        local=item.get("Place", ""),
        imagem=item.get("ImageEvent", ""),
        url=f"https://q2ingressos.com.br/evento/{item.get('Slug', '')}",
        fonte="q2ingressos",
        event_id=str(item.get("Id", "")),
    )
