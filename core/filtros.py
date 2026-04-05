"""
Módulo de filtragem de eventos.
Funções puras que filtram listas de eventos por diversos critérios.
NÃO modifica dados existentes — apenas retorna subconjuntos filtrados.
"""
from datetime import datetime, timedelta
from typing import List, Dict


def ordenar_por_data(eventos: List[dict], crescente: bool = True) -> List[dict]:
    """
    Ordena eventos por data.
    
    Args:
        eventos: Lista de eventos (dict com chave 'data' ou 'evento.data')
        crescente: True = mais próximo primeiro, False = mais distante primeiro
    
    Returns:
        Lista ordenada (sempre retorna nova lista, não modifica original)
    """
    def extrair_data(item):
        data_str = item.get("data", "")
        if not data_str:
            data_str = item.get("evento", {}).get("data", "")
        if not data_str:
            return datetime.max if crescente else datetime.min
        try:
            return datetime.fromisoformat(data_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return datetime.max if crescente else datetime.min

    return sorted(eventos, key=extrair_data, reverse=not crescente)


def filtrar_por_periodo(eventos: List[dict], periodo: str = "todos") -> List[dict]:
    """
    Filtra eventos por período temporal.
    
    Args:
        eventos: Lista de eventos
        periodo: "semana", "mes", "ano" ou "todos"
    
    Returns:
        Lista filtrada e ordenada por data crescente
    """
    if periodo == "todos":
        return ordenar_por_data(eventos, crescente=True)

    hoje = datetime.now().date()

    if periodo == "semana":
        limite = hoje + timedelta(days=7)
    elif periodo == "mes":
        limite = hoje + timedelta(days=30)
    elif periodo == "ano":
        limite = hoje + timedelta(days=365)
    else:
        return ordenar_por_data(eventos, crescente=True)

    filtrados = []
    for evento in eventos:
        data_str = evento.get("data", "")
        if not data_str:
            data_str = evento.get("evento", {}).get("data", "")
        if not data_str:
            continue
        try:
            data_evento = datetime.fromisoformat(data_str.replace("Z", "+00:00")).date()
            if hoje <= data_evento <= limite:
                filtrados.append(evento)
        except (ValueError, TypeError):
            continue

    return ordenar_por_data(filtrados, crescente=True)


def filtrar_por_escopo(eventos: List[dict], escopo: str = "todos") -> List[dict]:
    """
    Filtra eventos por escopo geográfico.
    
    Args:
        eventos: Lista de eventos
        escopo: "nacional", "internacional" ou "todos"
    
    Returns:
        Lista filtrada e ordenada por data crescente
    """
    if escopo == "todos":
        return ordenar_por_data(eventos, crescente=True)

    filtrados = []
    for evento in eventos:
        tipo = evento.get("tipo_geografico", "")
        if not tipo:
            tipo = evento.get("evento", {}).get("tipo_geografico", "")

        if escopo == "nacional" and tipo == "nacional":
            filtrados.append(evento)
        elif escopo == "internacional" and tipo == "internacional":
            filtrados.append(evento)
        elif not tipo:
            if escopo == "nacional":
                filtrados.append(evento)

    return ordenar_por_data(filtrados, crescente=True)


def filtrar_por_categoria(eventos: List[dict], categoria: str = "todos") -> List[dict]:
    """
    Filtra eventos por categoria.
    
    Args:
        eventos: Lista de eventos
        categoria: "show", "festival", "esporte", "teatro", "standup" ou "todos"
    
    Returns:
        Lista filtrada e ordenada por data crescente
    """
    if categoria == "todos":
        return ordenar_por_data(eventos, crescente=True)

    filtrados = []
    for evento in eventos:
        cat = evento.get("categoria", "")
        if not cat:
            cat = evento.get("evento", {}).get("categoria", "")

        if cat.lower() == categoria.lower():
            filtrados.append(evento)

    return ordenar_por_data(filtrados, crescente=True)


def filtrar_por_cidade(eventos: List[dict], cidade: str) -> List[dict]:
    """
    Filtra eventos por cidade (busca parcial, case-insensitive).
    
    Args:
        eventos: Lista de eventos
        cidade: Nome da cidade (busca parcial)
    
    Returns:
        Lista filtrada e ordenada por data crescente
    """
    if not cidade:
        return ordenar_por_data(eventos, crescente=True)

    cidade_lower = cidade.lower()
    filtrados = []
    for evento in eventos:
        cid = evento.get("cidade", "")
        if not cid:
            cid = evento.get("evento", {}).get("cidade", "")

        if cidade_lower in cid.lower():
            filtrados.append(evento)

    return ordenar_por_data(filtrados, crescente=True)


def filtrar_por_artista(eventos: List[dict], artista: str) -> List[dict]:
    """
    Filtra eventos por nome do artista (busca parcial, case-insensitive).
    
    Args:
        eventos: Lista de eventos
        artista: Nome do artista (busca parcial)
    
    Returns:
        Lista filtrada e ordenada por data crescente
    """
    if not artista:
        return ordenar_por_data(eventos, crescente=True)

    artista_lower = artista.lower()
    filtrados = []
    for evento in eventos:
        art = evento.get("artista", "")
        if not art:
            art = evento.get("evento", {}).get("artista", "")

        if artista_lower in art.lower():
            filtrados.append(evento)

    return ordenar_por_data(filtrados, crescente=True)


def buscar(eventos: List[dict], termo: str) -> List[dict]:
    """
    Busca termo em nome, artista e cidade simultaneamente.
    
    Args:
        eventos: Lista de eventos
        termo: Termo de busca
    
    Returns:
        Lista filtrada e ordenada por data crescente
    """
    if not termo:
        return ordenar_por_data(eventos, crescente=True)

    termo_lower = termo.lower()
    filtrados = []
    for evento in eventos:
        nome = evento.get("nome", "") or evento.get("evento", {}).get("nome", "")
        art = evento.get("artista", "") or evento.get("evento", {}).get("artista", "")
        cid = evento.get("cidade", "") or evento.get("evento", {}).get("cidade", "")

        if (termo_lower in nome.lower() or
                termo_lower in art.lower() or
                termo_lower in cid.lower()):
            filtrados.append(evento)

    return ordenar_por_data(filtrados, crescente=True)


def resumo_estatistico(eventos: List[dict]) -> dict:
    """
    Gera resumo estatístico de uma lista de eventos.
    
    Returns:
        Dicionário com contagens por ação, categoria, escopo, etc.
    """
    total = len(eventos)
    if total == 0:
        return {"total": 0}

    categorias = {}
    cidades = {}
    fontes = {}
    escopos = {}
    acoes = {}

    for evento in eventos:
        cat = evento.get("categoria", evento.get("evento", {}).get("categoria", "desconhecido"))
        cid = evento.get("cidade", evento.get("evento", {}).get("cidade", "desconhecido"))
        fonte = evento.get("fonte", evento.get("evento", {}).get("fonte", "desconhecido"))
        escopo = evento.get("tipo_geografico", evento.get("evento", {}).get("tipo_geografico", "desconhecido"))
        acao = evento.get("acao_final", "N/A")

        categorias[cat] = categorias.get(cat, 0) + 1
        cidades[cid] = cidades.get(cid, 0) + 1
        fontes[fonte] = fontes.get(fonte, 0) + 1
        escopos[escopo] = escopos.get(escopo, 0) + 1
        acoes[acao] = acoes.get(acao, 0) + 1

    return {
        "total": total,
        "por_categoria": dict(sorted(categorias.items(), key=lambda x: x[1], reverse=True)),
        "por_cidade": dict(sorted(cidades.items(), key=lambda x: x[1], reverse=True)[:10]),
        "por_fonte": dict(sorted(fontes.items(), key=lambda x: x[1], reverse=True)),
        "por_escopo": dict(sorted(escopos.items(), key=lambda x: x[1], reverse=True)),
        "por_acao": dict(sorted(acoes.items(), key=lambda x: x[1], reverse=True))
    }
