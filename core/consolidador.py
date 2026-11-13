"""
Consolidação de eventos duplicados.
Agrupa eventos idênticos coletados de múltiplas fontes ou zonas de uma
mesma plataforma: mesmo evento (nome normalizado + cidade + data) vira
um grupo com N membros, cada um com sua fonte/URL.

Contrato:
- anotar_grupos(eventos) -> anota em cada item:
    grupo_id, grupo_count, grupo_repr (bool), grupo_membros (lista de
    {fonte, url, preco, event_id}) — o client agrupa por grupo_id.
- consolidar(eventos) -> lista de grupos (representante + membros).
"""
import re
import unicodedata
from typing import List, Dict

_MESES = "JAN|FEV|MAR|ABR|MAI|JUN|JUL|AGO|SET|OUT|NOV|DEZ"

# Padrões de sujeira em títulos que não alteram a identidade do evento
_RE_BRACKETS = re.compile(r"\[[^\]]*\]")                          # "[Data E..." truncado
_RE_DATA_EXTRA = re.compile(r"\bDATA\s*(?:EXTRA|ADICIONAL)\b")
_RE_MES_ANTES = re.compile(rf"\b\d{{1,2}}\s*[\.\-]?\s*(?:{_MESES})\b\s*\.?", re.IGNORECASE)   # "20.NOV", "20 NOV"
_RE_MES_DEPOIS = re.compile(rf"\b(?:{_MESES})\s*[\.\-]?\s*\d{{1,2}}\b\s*\.?", re.IGNORECASE)  # "NOV.20"
_RE_DATA_NUM = re.compile(r"\b\d{1,2}\s*[/\.\-]\s*\d{1,2}(?:\s*[/\.\-]\s*\d{2,4})?\b")        # "13/11", "13.11", "13-11-26"
_RE_NAO_ALNUM = re.compile(r"[^A-Z0-9 ]+")
_RE_ESPACOS = re.compile(r"\s+")


def normalizar_texto(txt) -> str:
    """Normaliza título p/ dedupe: sem acento, maiúsculo, datas removidas,
    pontuação colapsada em espaço."""
    if not txt:
        return ""
    s = unicodedata.normalize("NFKD", str(txt))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.upper()
    s = re.sub(r"[–—―−]", "-", s)
    s = _RE_BRACKETS.sub(" ", s)
    s = _RE_DATA_EXTRA.sub(" ", s)
    s = _RE_MES_ANTES.sub(" ", s)
    s = _RE_MES_DEPOIS.sub(" ", s)
    s = _RE_DATA_NUM.sub(" ", s)
    s = _RE_NAO_ALNUM.sub(" ", s)   # pontuação (&, -, ., :, !) vira espaço
    s = _RE_ESPACOS.sub(" ", s)
    return s.strip()


def _ev_de(item: dict) -> dict:
    ev = item.get("evento")
    return ev if isinstance(ev, dict) else item


def chave_grupo(item: dict) -> str:
    """Chave de dedupe: nome normalizado (sem cidade no fim) + cidade + data."""
    ev = _ev_de(item)
    nome = normalizar_texto(ev.get("nome"))
    cidade = normalizar_texto(ev.get("cidade"))
    # remove cidade repetida no fim do nome ("... - RIO DE JANEIRO")
    if cidade and nome.endswith(" " + cidade):
        nome = nome[: -len(cidade) - 1].strip(" -,")
    data = str(ev.get("data") or "")[:10]
    return f"{nome}|{cidade}|{data}"


_PRIORIDADE_ACAO = {"COMPRAR": 0, "MONITORAR": 1, "IGNORAR": 2}


def _chave_representacao(item: dict):
    ev = _ev_de(item)
    analise = item.get("analise") or {}
    acao = item.get("acao_final") or "ZZZ"
    prio = _PRIORIDADE_ACAO.get(acao, 3)
    nota = analise.get("nota_final") or 0
    return (prio, -float(nota))


def anotar_grupos(eventos: List[dict]) -> List[dict]:
    """Anota grupo_id/grupo_count/grupo_repr/grupo_membros em cada item (in place)."""
    grupos: Dict[str, List[int]] = {}
    for i, item in enumerate(eventos):
        gid = chave_grupo(item)
        item["grupo_id"] = gid
        grupos.setdefault(gid, []).append(i)

    for gid, idxs in grupos.items():
        membros = []
        for i in idxs:
            it = eventos[i]
            ev = _ev_de(it)
            membros.append({
                "fonte": ev.get("fonte") or "",
                "url": ev.get("url") or "",
                "preco": ev.get("preco"),
                "event_id": ev.get("event_id") or "",
                "nome": ev.get("nome") or "",
            })
        rep_idx = min(idxs, key=lambda i: _chave_representacao(eventos[i]))
        for i in idxs:
            it = eventos[i]
            it["grupo_count"] = len(idxs)
            it["grupo_repr"] = (i == rep_idx)
            it["grupo_membros"] = membros
    return eventos


def consolidar(eventos: List[dict]) -> List[dict]:
    """Retorna lista de grupos: cada grupo é o item representante anotado
    com grupo_count/grupo_membros. Ordem: representante já escolhido."""
    anotar_grupos(eventos)
    vistos = set()
    grupos = []
    for item in eventos:
        gid = item.get("grupo_id")
        if item.get("grupo_repr") and gid not in vistos:
            vistos.add(gid)
            grupos.append(item)
    return grupos
