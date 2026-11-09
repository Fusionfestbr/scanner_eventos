"""
Parser de nomes de eventos.

Os títulos chegam sujos das fontes, por exemplo:
    "The Rose - São Paulo - 21/06/2026 - Venda Geral"
    "Kid Abelha: Eu Tive Um Sonho"
    "ENHYPEN WORLD TOUR 'BLOOD SAGA'"

Este módulo separa artista, cidade e data embutidos no título,
remove lixo comercial ("Venda Geral", lotes, tier de ingresso) e
devolve o nome limpo. É a primeira camada de higiene — o LLM só
entra depois (Fase de enriquecimento), quando algo faltar.
"""
import re
import unicodedata

from core.classificadores import CIDADES_BRASILEIRAS

# ---------------------------------------------------------------------------
# Utilidades de texto
# ---------------------------------------------------------------------------

def _sem_acentos(texto: str) -> str:
    """Remove acentos ('São Paulo' -> 'Sao Paulo')."""
    if not texto:
        return ""
    normalizado = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in normalizado if not unicodedata.combining(c))


# Cidades em formato normalizado (sem acento, minúsculo).
# Só nomes com 3+ letras viram candidata a cidade ("sp"/"rj" sozinhos
# são ambíguos e são descartados aqui).
_CIDADES_NORM = {
    _sem_acentos(c).strip()
    for c in CIDADES_BRASILEIRAS
    if len(c.strip()) >= 3
}

_UFS = {
    "sp", "rj", "mg", "ba", "pr", "rs", "pe", "ce", "sc", "df", "es",
    "am", "pa", "go", "ma", "mt", "ms", "pb", "rn", "al", "se", "pi",
    "to", "ac", "rr", "ap", "ro",
}

# Lixos comerciais que às vezes aparecem como parte isolada do título.
# Comparação por IGUALDADE (de parte inteira), nunca por substring —
# assim "Camarote Salvador Carnaval" não é confundido com "Camarote".
_JUNK_PARTES = {
    "venda", "venda geral", "venda exclusiva", "venda oficial",
    "pre-venda", "pré-venda", "pre venda", "pré venda",
    "lote 1", "lote 2", "lote 3", "lote 4", "1 lote", "2 lote",
    "1º lote", "2º lote", "3º lote",
    "primeiro lote", "segundo lote", "terceiro lote",
    "combo", "pacote", "vip", "premium", "golden", "backstage",
    "pista", "arquibancada", "cadeira", "camarote", "meia entrada",
    "ingresso", "ingressos", "ticket", "tickets",
    "abertura", "show", "evento",
}

# Marcadores que costumam separar artista do resto no título.
_TOUR_MARKER = re.compile(
    r"\b(w[oô]rld\s*t[oô][uú]r|turn[êe]|turne|\btour\b|ao\s+vivo|live\s+in)\b",
    re.IGNORECASE,
)

# Quando a esquerda dos ':' é uma categoria e não um artista
# ("Stand-up Comedy: Danilo Gentili" -> artista é a direita)
_CATEGORIA_COLON = re.compile(
    r"^\s*(stand[\s-]?up|comedy|comédia|festival|show|musical|expo[sz]ição|workshop|curso|palestra|debate|turn[êe]|teatro|or\w*)\b",
    re.IGNORECASE,
)

SEPARADORES = re.compile(r"\s+[–—|]\s+|\s+-\s+")


# ---------------------------------------------------------------------------
# Extração de data dentro do título
# ---------------------------------------------------------------------------

_RE_DATA_SLASH = re.compile(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})")
_RE_DATA_POR_EXTENSO = re.compile(
    r"(\d{1,2})\s+de\s+(jan(eiro)?|fev(ereiro)?|mar([çc]o)?|abr(il)?|mai(o)?|jun(ho)?|jul(ho)?|ag(o|osto)?|set(embro)?|out(ubro)?|nov(embro)?|dez(embro)?)\s*(de)?\s*(\d{4})?",
    re.IGNORECASE,
)

_MESES = {
    "jan": "01", "janeiro": "01",
    "fev": "02", "fevereiro": "02",
    "mar": "03", "marco": "03", "março": "03",
    "abr": "04", "abril": "04",
    "mai": "05", "maio": "05",
    "jun": "06", "junho": "06",
    "jul": "07", "julho": "07",
    "ago": "08", "agosto": "08",
    "set": "09", "setembro": "09",
    "out": "10", "outubro": "10",
    "nov": "11", "novembro": "11",
    "dez": "12", "dezembro": "12",
}


def _ano_valido(ano: int) -> int:
    if ano < 100:
        return 2000 + ano if ano < 60 else 1900 + ano
    return ano


def parse_data_generica(texto: str) -> str:
    """
    Acha a primeira data em quase qualquer formato comum e devolve ISO (YYYY-MM-DD).

    Aceita: 2026-06-21(T...), 21/06/2026, 21-06-26, 21.06.2026,
    "21 de junho de 2026", "21 de junho", "junho de 2026".
    """
    if not texto:
        return ""
    texto = str(texto).strip()

    # ISO com hora (2026-06-21T20:00:00)
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", texto)
    if m:
        try:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        except Exception:
            pass

    # dd/mm/aaaa (ou dd.cm.aa, dd mm aa)
    m = _RE_DATA_SLASH.search(texto)
    if m:
        try:
            dia = int(m.group(1)).__str__().zfill(2)
            mes = int(m.group(2)).__str__().zfill(2)
            ano = _ano_valido(int(m.group(3)))
            if 1 <= int(mes) <= 12:
                return f"{ano}-{mes}-{dia}"
        except Exception:
            pass

    # Por extenso: 21 de junho de 2026 / 21 de junho
    m = _RE_DATA_POR_EXTENSO.search(texto)
    if m:
        try:
            dia = str(int(m.group(1))).zfill(2)
            mes_nome = _sem_acentos(m.group(2).lower())
            for chave in _MESES:
                if mes_nome.startswith(chave):
                    mes = _MESES[chave]
                    break
            else:
                mes = ""
            if mes:
                ano = int(m.group(5)) if m.group(5) else 0
                if ano >= 2000:
                    return f"{ano}-{mes}-{dia}"
                # sem ano: assume ano corrente (pasta de coleta recente)
                from datetime import datetime
                return f"{datetime.now().year}-{mes}-{dia}"
        except Exception:
            pass

    # "junho de 2026" (mês isolado) -> dia 01 do mês
    m = re.search(r"^(janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\s+de\s+(\d{4})$", texto.strip(), re.IGNORECASE)
    if m:
        mes = _MESES.get(m.group(1).lower(), "")
        if mes:
            return f"{m.group(2)}-{mes}-01"

    return ""


def _span_de_data(texto: str):
    """Retorna (inicio, fim) da primeira data no texto, ou None."""
    for regex in (_RE_DATA_SLASH, _RE_DATA_POR_EXTENSO):
        m = regex.search(texto)
        if m:
            return m.span()
    return None


# ---------------------------------------------------------------------------
# Extração de cidade
# ---------------------------------------------------------------------------

def _cidade_da_parte(parte: str) -> tuple[str, str]:
    """
    Tenta ler (cidade, estado) de uma parte do título.
    Devolve ("", "") se a parte não parece cidade.
    """
    if not parte:
        return "", ""

    limpa = parte.strip()
    # "São Paulo/SP", "Fortaleza - CE", "Belém, PA"
    m = re.match(r"^(.+?)[/\-,\s]+([A-Za-z]{2})$", limpa)
    if m:
        nome_cidade = m.group(1).strip()
        uf = _sem_acentos(m.group(2)).lower()
        if uf in _UFS:
            if _sem_acentos(nome_cidade).lower() in _CIDADES_NORM:
                return nome_cidade, m.group(2).upper()

    # Parte que é apenas UF ("ROBERTO CARLOS - SP" -> parte "SP")
    if re.match(r"^[A-Za-z]{2}$", limpa):
        uf = _sem_acentos(limpa).lower()
        if uf in _UFS:
            return "", limpa.upper()

    normalizada = _sem_acentos(limpa).lower()
    if normalizada in _CIDADES_NORM:
        return limpa, ""

    return "", ""


# ---------------------------------------------------------------------------
# Limpeza do título
# ---------------------------------------------------------------------------

def _eh_lixo(parte: str) -> bool:
    """Tiers de venda, lotes, etc. considerados lixo como parte inteira."""
    return _sem_acentos(parte).strip().lower() in _JUNK_PARTES


def _parece_hora(texto: str) -> bool:
    """Evita confundir 'Show 21:30' com separação de artista."""
    return bool(re.search(r"\d{1,2}[:h]\d{2}", texto))


def _plausivel_artista(texto: str) -> bool:
    if not texto:
        return False
    texto_limpo = texto.strip()
    if not (2 <= len(texto_limpo) <= 60):
        return False
    if len(texto_limpo.split()) > 7:
        return False
    if parse_data_generica(texto_limpo):
        return False
    return True


def _artista_de_partes(nome_partes: list[str]) -> str:
    """Quando o título é 'Artista - Nome da Turnê', devolve a primeira parte."""
    if len(nome_partes) < 2:
        return ""
    primeira = nome_partes[0].strip()
    resto = " - ".join(nome_partes[1:])
    if _plausivel_artista(primeira) and _TOUR_MARKER.search(resto):
        return primeira
    return ""


def _artista_pre_marker(nome: str) -> str:
    """
    'ENHYPEN WORLD TOUR BLOOD SAGA' -> 'ENHYPEN'
    (palavras ANTES do marcador de turnê, quando curtas e plausíveis)
    """
    m = _TOUR_MARKER.search(nome)
    if not m or m.start() == 0:
        return ""
    pre = nome[: m.start()].strip(" .:'\"-")
    if _plausivel_artista(pre) and len(pre.split()) <= 4:
        return pre
    return ""


def limpar_e_extrair(titulo: str) -> dict:
    """
    Limpa o título e extrai (artista, cidade, estado, data) nele embutidos.

    Returns:
        dict com chaves: nome, artista, cidade, estado, data.
    """
    resultado = {"nome": "", "artista": "", "cidade": "", "estado": "", "data": ""}
    if not titulo or not titulo.strip():
        return resultado

    titulo_limpo = titulo.strip()
    artista_hint = ""
    artista_da_direita = False

    # Padrão "Kid Abelha: Eu Tive Um Sonho" — esquerda é o artista.
    # Exceção: "Stand-up Comedy: Danilo Gentili" — esquerda é categoria,
    # então o artista visto aos direita.
    if ":" in titulo_limpo and not _parece_hora(titulo_limpo):
        esquerda, direita = titulo_limpo.split(":", 1)
        primeira_direita = re.split(r"\s+-\s+|\s+[|–—]\s+", direita.strip(), maxsplit=1)[0]
        if (
            esquerda
            and direita.strip()
            and _CATEGORIA_COLON.match(esquerda)
            and _plausivel_artista(primeira_direita)
        ):
            # categoria à esquerda ("Stand-up Comedy: Danilo Gentili"):
            # artista é a primeira parte à direita; título continua inteiro
            artista_da_direita = True
        elif _plausivel_artista(esquerda) and len(direita.strip()) >= 3:
            artista_hint = esquerda.strip()
            titulo_limpo = direita.strip()

    partes = [p.strip() for p in SEPARADORES.split(titulo_limpo) if p and p.strip()]

    cidade, estado, data_iso = "", "", ""
    nome_partes = []

    for parte in partes:
        # data isolada na parte ("21/06/2026")
        if parse_data_generica(parte) and not data_iso and _span_de_data(parte) == (0, len(parte)):
            data_iso = parse_data_generica(parte)
            continue

        # data embutida no meio do nome ("Turnê 21/06/2026 São Paulo")
        span = _span_de_data(parte)
        if span and not data_iso:
            data_iso = parse_data_generica(parte)
            parte_norm = (parte[: span[0]] + parte[span[1] :]).strip(" -,.|")
            parte = parte_norm if parte_norm else ""
            if not parte:
                continue

        cid, uf = _cidade_da_parte(parte)
        if (cid or uf) and not cidade:
            cidade, estado = cid, uf
            continue

        if _eh_lixo(parte):
            continue

        nome_partes.append(parte)

    # Artista: hint do separador ':' prevalece, senão padrão 'Artista - ... Tour ...'
    if artista_da_direita:
        artista = nome_partes[0].strip() if nome_partes else ""
        if artista and ":" in artista:
            artista = artista.split(":", 1)[1].strip()
    else:
        artista = artista_hint or _artista_de_partes(nome_partes)
        if not artista and len(nome_partes) == 1:
            artista = _artista_pre_marker(nome_partes[0])

    resultado["nome"] = " - ".join(nome_partes).strip() if nome_partes else titulo_limpo
    resultado["artista"] = artista
    resultado["cidade"] = cidade
    resultado["estado"] = estado
    resultado["data"] = data_iso
    return resultado


# ---------------------------------------------------------------------------
# Enriquecimento de evento (aplicado sobre dicts do pipeline)
# ---------------------------------------------------------------------------

def enriquecer_do_nome(evento: dict) -> dict:
    """
    Preenche artista/cidade/estado/data que estão faltando a partir do título.

    Regras:
        - nada sobrescreve informação real: só preenche campos vazios;
        - "Various Artists" é tratado como vazio;
        - o nome é atualizado quando a versão limpa difere (remove
          data/cidade/lixo embutidos no título).
    """
    if not isinstance(evento, dict):
        return evento

    titulo = evento.get("nome", "")
    if not titulo:
        return evento

    parsed = limpar_e_extrair(titulo)

    if parsed["nome"] and parsed["nome"] != titulo:
        evento["nome"] = parsed["nome"]

    artista_atual = (evento.get("artista") or "").strip()
    if (not artista_atual or artista_atual == "Various Artists") and parsed["artista"]:
        evento["artista"] = parsed["artista"]

    if not (evento.get("cidade") or "").strip() and parsed["cidade"]:
        evento["cidade"] = parsed["cidade"]
        if not (evento.get("estado") or "").strip() and parsed["estado"]:
            evento["estado"] = parsed["estado"]

    if not (evento.get("estado") or "").strip() and parsed["estado"] and not parsed["cidade"]:
        evento["estado"] = parsed["estado"]

    if not (evento.get("data") or "").strip() and parsed["data"]:
        evento["data"] = parsed["data"]

    return evento


def evento_padrao(
    nome: str = "",
    artista: str = "",
    data: str = "",
    cidade: str = "",
    estado: str = "",
    local: str = "",
    preco: float = 0.0,
    url: str = "",
    imagem: str = "",
    fonte: str = "",
    event_id: str = "",
    categoria_fonte: str = "",
) -> dict:
    """
    Copia o schema de evento do pipeline com valores de default únicos.

    Qualquer fonte (API ou scraper) deve montar o evento por aqui, para
    que a chave do schema fique definida um único lugar.
    """
    evento = {
        "nome": (nome or "").strip(),
        "artista": (artista or "").strip(),
        # normaliza datas com hora/timezone ("2026-12-12T20:30:00-03:00")
        "data": parse_data_generica(data) if data else "",
        "cidade": (cidade or "").strip(),
        "estado": (estado or "").strip(),
        "local": (local or "").strip(),
        "preco": _preco_float(preco),
        "url": (url or "").strip(),
        "imagem": (imagem or "").strip(),
        "fonte": (fonte or "").strip(),
        "event_id": str(event_id or ""),
        "categoria_fonte": (categoria_fonte or "").strip(),
    }
    return enriquecer_do_nome(evento)


def _preco_float(preco) -> float:
    """Aceita 'R$ 79,90', '79.90', 79.9 e devolve float >= 0."""
    if preco is None:
        return 0.0
    if isinstance(preco, (int, float)):
        return max(0.0, float(preco))
    texto = str(preco).strip()
    # "1.234,56" -> 1234.56 ; "79.90" -> 79.90 ; "79,90" -> 79.90
    m = re.search(r"(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d{2}))?", texto.replace("R$", ""))
    if not m:
        return 0.0
    inteiro = m.group(1)
    if re.match(r"^\d{1,3}(?:\.\d{3})+$", inteiro):
        inteiro = inteiro.replace(".", "")
    centavos = m.group(2) or "0"
    try:
        return max(0.0, float(f"{inteiro}.{centavos}"))
    except ValueError:
        return 0.0
