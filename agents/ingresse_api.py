import requests

API_URL = "https://api-site.ingresse.com/custom-categories/list/events"

PARAMS = {
    "iso_code": "BRA",
    "language": "pt_br"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

TIMEOUT = 10


def get_ingresse_events() -> list[dict]:
    """Busca eventos da API Ingresse e retorna no formato padronizado."""
    try:
        response = requests.get(
            API_URL,
            params=PARAMS,
            headers=HEADERS,
            timeout=TIMEOUT
        )

        if response.status_code != 200:
            print(f"   [ERRO] Ingresse API: status {response.status_code}")
            return []

        data = response.json()
        
        eventos = []
        for categoria in data:
            for evento in categoria.get("events", []):
                evento_padronizado = _transform_event(evento)
                eventos.append(evento_padronizado)

        return eventos

    except requests.exceptions.Timeout:
        print("   [ERRO] Ingresse API: timeout")
        return []
    except Exception as e:
        print(f"   [ERRO] Ingresse API: {e}")
        return []


def _transform_event(evento: dict) -> dict:
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
