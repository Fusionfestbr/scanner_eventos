"""
Agente validador de eventos.
Realiza limpeza e validação dos dados coletados.
"""
import unicodedata

from utils.date_utils import (
    validar_data,
    data_eh_futura,
    formatar_data_iso
)
from core.classificadores import (
    classificar_escopo,
    classificar_categoria,
    classificar_genero,
    extrair_pais,
    CATEGORIAS_NAO_MUSICAS,
)
from config import COLETA_SOMENTE_MUSICA


def _sem_acentos(texto: str) -> str:
    if not texto:
        return ""
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))


def validar_eventos(eventos: list[dict]) -> list[dict]:
    """
    Valida e limpa lista de eventos.

    Regras:
    - Remove eventos com data anterior ao dia atual
    - Remove eventos com data inválida
    - Remove duplicados (nome normalizado + data)
    - Padroniza data no formato YYYY-MM-DD
    - Adiciona campos de classificação: tipo_geografico, categoria, genero, pais
    - Preserva os campos ricos da coleta (local, preco, imagem, event_id)
    """
    eventos_validos = []
    seen = set()

    for evento in eventos:
        data_str = evento.get("data", "")

        if not validar_data(data_str):
            continue

        if not data_eh_futura(data_str):
            continue

        data_iso = formatar_data_iso(data_str)
        if not data_iso:
            continue

        nome_norm = _sem_acentos((evento.get("nome") or "").lower()).strip()
        nome_norm = " ".join(nome_norm.split())
        key = f"{nome_norm}|{data_iso}"
        if key in seen:
            continue
        seen.add(key)

        artista = (evento.get("artista") or "").strip()
        categoria = classificar_categoria(evento)

        if COLETA_SOMENTE_MUSICA and categoria in CATEGORIAS_NAO_MUSICAS:
            # não-música óbvia por regras: sai já no validador
            continue

        evento_limpo = {
            "nome": evento.get("nome", "").strip(),
            "artista": "" if artista == "Various Artists" else artista,
            "data": data_iso,
            "cidade": evento.get("cidade", "").strip(),
            "fonte": evento.get("fonte", "").strip(),
            "url": evento.get("url", "").strip(),
            # campos ricos (podem estar vazios — preenchidos na coleta quando a fonte fornece)
            "estado": evento.get("estado", "").strip(),
            "local": evento.get("local", "").strip(),
            "preco": evento.get("preco", 0.0) or 0.0,
            "imagem": evento.get("imagem", "").strip(),
            "event_id": str(evento.get("event_id", "") or ""),
            "categoria_fonte": evento.get("categoria_fonte", "").strip(),
            # classificação
            "tipo_geografico": classificar_escopo(evento),
            "categoria": categoria,
            "genero": classificar_genero(evento),
            "pais": extrair_pais(evento)
        }
        eventos_validos.append(evento_limpo)

    return eventos_validos
