"""
Agregador de eventos de múltiplas fontes.
Executa chamadas às APIs individuais e combina os resultados.
"""
from typing import List, Dict

import agents.eventim_api
import agents.ingresse_api
import agents.livepass_api
import agents.q2ingressos_api
import agents.zigtickets_api
import agents.guicheweb_api


def get_all_events() -> List[Dict]:
    """Busca eventos de todas as fontes e retorna no formato padronizado."""
    print("\n  Buscando eventos de todas as fontes...")

    eventos = []

    print("  - Eventim...")
    try:
        eventim = agents.eventim_api.get_eventim_events()
        print(f"    -> {len(eventim)} eventos")
        eventos.extend(eventim)
    except Exception as e:
        print(f"    -> ERRO: {e}")

    print("  - Ingresse...")
    try:
        ingresse = agents.ingresse_api.get_ingresse_events()
        print(f"    -> {len(ingresse)} eventos")
        eventos.extend(ingresse)
    except Exception as e:
        print(f"    -> ERRO: {e}")

    print("  - Livepass...")
    try:
        livepass = agents.livepass_api.get_livepass_events()
        print(f"    -> {len(livepass)} eventos")
        eventos.extend(livepass)
    except Exception as e:
        print(f"    -> ERRO: {e}")

    print("  - Q2 Ingressos...")
    try:
        q2 = agents.q2ingressos_api.get_q2ingressos_events()
        print(f"    -> {len(q2)} eventos")
        eventos.extend(q2)
    except Exception as e:
        print(f"    -> ERRO: {e}")

    print("  - Zig Tickets...")
    try:
        zig = agents.zigtickets_api.get_zigtickets_events()
        print(f"    -> {len(zig)} eventos")
        eventos.extend(zig)
    except Exception as e:
        print(f"    -> ERRO: {e}")

    print("  - GuichêWeb...")
    try:
        gw = agents.guicheweb_api.get_guicheweb_events()
        print(f"    -> {len(gw)} eventos")
        eventos.extend(gw)
    except Exception as e:
        print(f"    -> ERRO: {e}")

    print(f"\n  Total: {len(eventos)} eventos")

    return eventos