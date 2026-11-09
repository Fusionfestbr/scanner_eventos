"""
Enriquecimento híbrido de eventos (regras + IA) — Fase 4.

Estratégia:
    1. Preenche com REGRAS o mais barato possível:
       artista do título, gênero por palavras-chave, categoria
    2. Chama o LLM (LM Studio) SOMENTE para o que as regras não resolveram:
       artista ausente, categoria "outros" (musical ou não?)
       — e na mesma chamada pede gênero + descrição curta
    3. Marca não-musicais (quando COLETA_SOMENTE_MUSICA ativo)

Não substitui a análise COMPRAR/MONITORAR — roda antes dela,
deixando o prompt do analista todo mais rico.
"""
import re
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from config import LLM_WORKERS, COLETA_SOMENTE_MUSICA, ENRIQUECER_COM_IA
from core.classificadores import (
    classificar_categoria,
    classificar_genero,
    CATEGORIAS_MUSICAIS,
    parece_nao_musical,
)
from agents.nome_parser import limpar_e_extrair
from utils.logger import logger

_lock = threading.Lock()
_contador = 0


def _incrementa() -> int:
    global _contador
    with _lock:
        _contador += 1
        return _contador


def _precisa_ia(evento: dict) -> bool:
    """Chamada de IA só quando as regras não resolverem algo importante."""
    if not ENRIQUECER_COM_IA:
        return False
    precisa_artista = not (evento.get("artista") or "").strip()
    categoria = evento.get("categoria", "outros")
    precisa_categoria = categoria == "outros" and not evento.get("nao_musical")
    # gênero/descrição vêm de graça na mesma chamada — nunca disparam IA sozinhos
    return precisa_artista or precisa_categoria


def _mensagens_extracao(evento: dict) -> list[dict]:
    """Prompt de extração: JSON único com artista/gênero/musical/descrição."""
    nome = evento.get("nome", "")
    artista = evento.get("artista", "")
    data = evento.get("data", "")
    cidade = evento.get("cidade", "")
    local = evento.get("local", "")
    fonte_cat = evento.get("categoria_fonte", "")

    info = (
        f"Evento:\n"
        f"Nome: {nome}\n"
        f"Artista: {artista or '(vazio)'}\n"
        f"Data: {data or '(vazio)'}\n"
        f"Cidade: {cidade or '(vazio)'}\n"
        f"Local: {local or '(vazio)'}\n"
        f"Categoria da fonte: {fonte_cat or '(vazio)'}\n\n"
        "Preencha o que falta a partir do NOME do evento e do contexto:\n"
        "- artista: nome real do artista/banda principal "
        "(se for festival com vários artistas use 'Vários artistas')\n"
        "- genero: um exatamente entre: sertanejo, funk, rap, trap, rock, pop, "
        "eletronica, samba, pagode, mpb, forro, gospel, reggae, jazz, axe, outros\n"
        "- e_musical: true/false (é show ou festival de MÚSICA para público pagante? "
        "Workshop, curso, congresso, esporte e teatro = false)\n"
        "- descricao: uma frase em português (máx ~100 caracteres) que "
        "descreva o evento de forma natural\n\n"
        'Responda SOMENTE: {"artista": "...", "genero": "...", "e_musical": true, "descricao": "..."}'
    )
    return [
        {"role": "system", "content": "Você é um extrator de metadados de eventos musicais brasileiros. Responda APENAS com um JSON válido, sem texto a mais."},
        {"role": "user", "content": info},
    ]


def _parse_json_llm(resposta: str) -> dict | None:
    if not resposta:
        return None
    m = re.search(r"\{.*\}", resposta, re.DOTALL)
    if not m:
        return None
    try:
        dados = json.loads(m.group())
        if isinstance(dados, dict):
            return dados
    except json.JSONDecodeError:
        pass
    # fallback: campos soltos
    resultado = {}
    artista = re.search(r'"artista"\s*:\s*"([^"]*)"', resposta)
    genero = re.search(r'"genero"\s*:\s*"([^"]*)"', resposta)
    descricao = re.search(r'"descricao"\s*:\s*"([^"]*)"', resposta)
    musical = re.search(r'"e_musical"\s*:\s*(true|false)', resposta, re.IGNORECASE)
    if artista:
        resultado["artista"] = artista.group(1)
    if genero:
        resultado["genero"] = genero.group(1)
    if descricao:
        resultado["descricao"] = descricao.group(1)
    if musical:
        resultado["e_musical"] = musical.group(1).lower() == "true"
    return resultado or None


def _descricao_regras(evento: dict) -> str:
    """Descrição curta montada dos dados estruturados (sem IA)."""
    partes = []

    artista = (evento.get("artista") or "").strip()
    genero = (evento.get("genero") or "").strip()
    destino = ""

    local = (evento.get("local") or "").strip()
    cidade = (evento.get("cidade") or "").strip()
    estado = (evento.get("estado") or "").strip()

    onde = cidade
    if estado and estado.lower() not in cidade.lower():
        onde = f"{cidade} - {estado}" if cidade else estado

    if artista and genero:
        mapa_label = {
            "show": "Show", "festival": "Festival",
        }
        prefixo = mapa_label.get(evento.get("categoria", "show"), "Show")
        partes.append(f"{prefixo} de {genero} com {artista}")
    elif genero:
        mapa_label = {
            "show": "Show", "festival": "Festival",
        }
        prefixo = mapa_label.get(evento.get("categoria", "show"), "Show")
        partes.append(f"{prefixo} de {genero}")
    elif local:
        partes.append(local)

    if onde:
        partes.append(onde)
    fonte_cat = (evento.get("categoria_fonte") or "").strip()
    if fonte_cat and fonte_cat not in partes:
        partes.append(fonte_cat)
    return " • ".join(p for p in partes if p)


def enriquecer_evento(evento: dict) -> dict:
    """Enriquece um evento (regras; IA quando necessário)."""
    # 1) Gênero por regras
    if not (evento.get("genero") or "").strip():
        evento["genero"] = classificar_genero(evento)

    # 2) Categoria (podia vir vazia se validador não passou) + heurística de não-música
    if not (evento.get("categoria") or "").strip():
        evento["categoria"] = classificar_categoria(evento)

    if COLETA_SOMENTE_MUSICA:
        categoria = evento.get("categoria", "")
        if categoria in {"esporte", "teatro", "standup", "conferencia", "religioso"}:
            evento["nao_musical"] = True
        elif categoria != "show" and categoria != "festival" and parece_nao_musical(evento):
            evento["nao_musical"] = True

    artista_atual = (evento.get("artista") or "").strip()

    # 3) Artista por regras (título), se ainda vazio
    if not artista_atual:
        parsed = limpar_e_extrair(evento.get("nome", ""))
        if parsed["artista"]:
            evento["artista"] = parsed["artista"]
            artista_atual = parsed["artista"]

    # 4) IA: só se algo relevante faltar
    if _precisa_ia(evento):
        try:
            from agents.analista import chamar_llm
            resposta = chamar_llm(_mensagens_extracao(evento))
            dados = _parse_json_llm(resposta)
            if dados:
                novo_artista = (dados.get("artista") or "").strip()
                if not artista_atual and novo_artista and novo_artista.lower() not in {"vários artistas", "varios artistas"}:
                    evento["artista"] = novo_artista
                elif not artista_atual and novo_artista:
                    evento["artista"] = "Vários artistas"
                if not (evento.get("genero") or "").strip():
                    novo_genero = (dados.get("genero") or "").strip().lower()
                    if novo_genero and novo_genero != "outros":
                        evento["genero"] = novo_genero
                if COLETA_SOMENTE_MUSICA and "e_musical" in dados:
                    evento["e_musical_ia"] = bool(dados.get("e_musical"))
                    if evento["e_musical_ia"] is False:
                        evento["nao_musical"] = True
                descricao_ia = (dados.get("descricao") or "").strip()
                if descricao_ia:
                    evento["descricao"] = descricao_ia[:150]
                evento["enriquecido_ia"] = True
        except Exception as e:
            logger.warning(f"Enriquecimento IA falhou para '{evento.get('nome', '?')[:50]}': {e}")

    # 5) Descrição fallback (estruturada) quando IA não produziu
    if not (evento.get("descricao") or "").strip():
        evento["descricao"] = _descricao_regras(evento)

    return evento


def enriquecer_eventos(eventos: list[dict]) -> list[dict]:
    """
    Enriquece em paralelo (mesmo pool de workers do analista).
    Eventos que não precisam de IA são enriquecidos por regras.
    """
    global _contador
    _contador = 0
    total = len(eventos)
    if total == 0:
        return eventos

    with ThreadPoolExecutor(max_workers=LLM_WORKERS) as executor:
        futures = {}
        for idx, evento in enumerate(eventos):
            if _precisa_ia(evento):
                futures[executor.submit(_enriquecer_com_log, idx, evento)] = idx
            else:
                eventos[idx] = enriquecer_evento(evento)

        for future in as_completed(futures):
            idx, enriquecido = future.result()
            eventos[idx] = enriquecido

    return eventos


def _enriquecer_com_log(idx: int, evento: dict):
    enriquecido = enriquecer_evento(evento)
    count = _incrementa()
    nome = evento.get("nome", "?")[:45]
    pendentes = ""
    print(f"   [IA {count}] {nome} -> artista: {enriquecido.get('artista') or '-'}")
    return idx, enriquecido


def filtrar_musicos(eventos: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Separa musicais × não-musicais.
    Eventos sem verificação (IA falhou/'outros') ficam do lado musical
    (falsos rejeitados custam mais que falsos mantidos).
    """
    musicos = []
    nao_musicos = []
    for e in eventos:
        if COLETA_SOMENTE_MUSICA and e.get("nao_musical"):
            nao_musicos.append(e)
        else:
            musicos.append(e)
    return musicos, nao_musicos
