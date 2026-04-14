"""
Sistema de Cache Inteligente para eventos.
Memoriza eventos já processados para evitar re-análise via LLM.
"""
import hashlib
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

CACHE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "eventos_cache.json")
REANALISE_DIAS = 7


def gerar_evento_id(evento: dict) -> str:
    """Gera ID único para o evento baseado em nome + data + fonte."""
    nome = evento.get("nome", "").lower().strip()
    data = evento.get("data", "")
    fonte = evento.get("fonte", "").lower().strip()
    
    if not nome or not data:
        return ""
    
    chave = f"{nome}|{data}|{fonte}"
    return hashlib.md5(chave.encode()).hexdigest()[:16]


def carregar_cache() -> dict:
    """Carrega o cache de eventos do arquivo JSON."""
    if not os.path.exists(CACHE_FILE):
        return criar_cache_vazio()
    
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return criar_cache_vazio()


def criar_cache_vazio() -> dict:
    """Cria estrutura inicial do cache."""
    return {
        "eventos": {},
        "metadados": {
            "total_eventos": 0,
            "ultima_atualizacao": None,
            "stats": {
                "cache_hits": 0,
                "cache_misses": 0,
                "re_analises": 0,
                "total_coletas": 0
            }
        }
    }


def salvar_cache(cache: dict) -> None:
    """Salva o cache no arquivo JSON."""
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    cache["metadados"]["ultima_atualizacao"] = datetime.now().isoformat()
    
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def buscar_evento_no_cache(evento_id: str, cache: dict = None) -> Optional[dict]:
    """Busca um evento específico no cache."""
    if cache is None:
        cache = carregar_cache()
    
    return cache.get("eventos", {}).get(evento_id)


def esta_fresco(evento_cache: dict) -> bool:
    """Verifica se o evento no cache ainda é válido (menos de 7 dias)."""
    data_processamento = evento_cache.get("data_processamento")
    if not data_processamento:
        return False
    
    try:
        dt = datetime.fromisoformat(data_processamento)
        dias = (datetime.now() - dt).days
        return dias < REANALISE_DIAS
    except (ValueError, TypeError):
        return False


def esta_valido(evento_cache: dict) -> bool:
    """Verifica se o evento ainda é válido (data futura)."""
    data_evento = evento_cache.get("data")
    if not data_evento:
        return False
    
    try:
        dt = datetime.strptime(data_evento, "%Y-%m-%d")
        return dt > datetime.now()
    except (ValueError, TypeError):
        return False


def adicionar_ao_cache(evento: dict, analise: dict = None, auditoria: dict = None, 
                       acao_final: str = "", previsao: dict = None, 
                       plano_acao: dict = None, execucao: dict = None) -> None:
    """Adiciona ou atualiza um evento no cache."""
    cache = carregar_cache()
    
    evento_id = evento.get("evento_id")
    if not evento_id:
        evento_id = gerar_evento_id(evento)
    
    if not evento_id:
        return
    
    cache["eventos"][evento_id] = {
        "evento_id": evento_id,
        "nome": evento.get("nome", ""),
        "data": evento.get("data", ""),
        "fonte": evento.get("fonte", ""),
        "url": evento.get("url", ""),
        "cidade": evento.get("cidade", ""),
        "tipo_geografico": evento.get("tipo_geografico", ""),
        "categoria": evento.get("categoria", ""),
        "pais": evento.get("pais", ""),
        "artista": evento.get("artista", ""),
        "analise": analise or {},
        "auditoria": auditoria or {},
        "acao_final": acao_final,
        "previsao": previsao or {},
        "plano_acao": plano_acao or {},
        "execucao": execucao or {},
        "data_processamento": datetime.now().isoformat(),
        "ultima_atualizacao": datetime.now().isoformat()
    }
    
    cache["metadados"]["total_eventos"] = len(cache["eventos"])
    salvar_cache(cache)


def adicionar_lote_ao_cache(eventos_completos: List[dict]) -> None:
    """Adiciona múltiplos eventos ao cache de uma vez."""
    cache = carregar_cache()
    
    for item in eventos_completos:
        evento = item.get("evento", {})
        analise = item.get("analise", {})
        auditoria = item.get("auditoria", {})
        acao_final = item.get("acao_final", "")
        previsao = item.get("previsao", {})
        plano_acao = item.get("plano_acao", {})
        execucao = item.get("execucao", {})
        
        evento_id = gerar_evento_id(evento)
        
        if not evento_id:
            continue
        
        cache["eventos"][evento_id] = {
            "evento_id": evento_id,
            "nome": evento.get("nome", ""),
            "data": evento.get("data", ""),
            "fonte": evento.get("fonte", ""),
            "url": evento.get("url", ""),
            "cidade": evento.get("cidade", ""),
            "tipo_geografico": evento.get("tipo_geografico", ""),
            "categoria": evento.get("categoria", ""),
            "pais": evento.get("pais", ""),
            "artista": evento.get("artista", ""),
            "analise": analise,
            "auditoria": auditoria,
            "acao_final": acao_final,
            "previsao": previsao,
            "plano_acao": plano_acao,
            "execucao": execucao,
            "data_processamento": datetime.now().isoformat(),
            "ultima_atualizacao": datetime.now().isoformat()
        }
    
    cache["metadados"]["total_eventos"] = len(cache["eventos"])
    salvar_cache(cache)


def limpar_eventos_passados() -> int:
    """Remove eventos do cache que já passaram (data < hoje)."""
    cache = carregar_cache()
    removidos = 0
    
    eventos_validos = {}
    for evento_id, dados in cache.get("eventos", {}).items():
        if esta_valido(dados):
            eventos_validos[evento_id] = dados
        else:
            removidos += 1
    
    cache["eventos"] = eventos_validos
    cache["metadados"]["total_eventos"] = len(eventos_validos)
    salvar_cache(cache)
    
    return removidos


def get_cache_stats() -> dict:
    """Retorna estatísticas do cache."""
    cache = carregar_cache()
    metadados = cache.get("metadados", {})
    
    eventos_validos = 0
    eventos_velhos = 0
    
    for dados in cache.get("eventos", {}).values():
        if esta_valido(dados):
            if esta_fresco(dados):
                eventos_validos += 1
            else:
                eventos_velhos += 1
    
    return {
        "total_cache": cache.get("metadados", {}).get("total_eventos", 0),
        "eventos_validos": eventos_validos,
        "eventos_velhos": eventos_velhos,
        "stats": metadados.get("stats", {}),
        "ultima_atualizacao": metadados.get("ultima_atualizacao")
    }


def processar_com_cache(eventos_coletados: List[dict]) -> tuple:
    """
    Processa eventos comparing com cache.
    
    Returns:
        tuple: (eventos_do_cache, eventos_para_processar, stats)
    """
    cache = carregar_cache()
    stats = {
        "cache_hits": 0,
        "cache_misses": 0,
        "re_analises": 0,
        "total": len(eventos_coletados)
    }
    
    eventos_do_cache = []
    eventos_para_processar = []
    
    for evento in eventos_coletados:
        evento_id = gerar_evento_id(evento)
        
        if not evento_id:
            eventos_para_processar.append(evento)
            continue
        
        evento_cache = cache.get("eventos", {}).get(evento_id)
        
        if evento_cache:
            # Verificar se ainda é válido e fresco
            if esta_valido(evento_cache):
                if esta_fresco(evento_cache):
                    # Hit total - usar cache
                    eventos_do_cache.append({
                        "do_cache": True,
                        "evento": evento,
                        "cache": evento_cache
                    })
                    stats["cache_hits"] += 1
                else:
                    # Evento existente mas velho - marcar para re-análise
                    eventos_para_processar.append(evento)
                    stats["re_analises"] += 1
            else:
                # Evento passou - processar como novo
                eventos_para_processar.append(evento)
                stats["cache_misses"] += 1
        else:
            # Evento novo
            eventos_para_processar.append(evento)
            stats["cache_misses"] += 1
    
    # Atualizar stats da coleta
    cache["metadados"]["stats"]["cache_hits"] += stats["cache_hits"]
    cache["metadados"]["stats"]["cache_misses"] += stats["cache_misses"]
    cache["metadados"]["stats"]["re_analises"] += stats["re_analises"]
    cache["metadados"]["stats"]["total_coletas"] += 1
    salvar_cache(cache)
    
    return eventos_do_cache, eventos_para_processar, stats


def mesclar_resultados(eventos_do_cache: List[dict], eventos_processados: List[dict]) -> List[dict]:
    """Mescla eventos do cache com eventos recém processados."""
    resultado = []
    
    # Adicionar eventos do cache (com dados completos)
    for item in eventos_do_cache:
        cache = item["cache"]
        resultado.append({
            "evento": item["evento"],
            "analise": cache.get("analise", {}),
            "auditoria": cache.get("auditoria", {}),
            "acao_final": cache.get("acao_final", ""),
            "previsao": cache.get("previsao", {}),
            "plano_acao": cache.get("plano_acao", {}),
            "execucao": cache.get("execucao", {}),
            "from_cache": True
        })
    
    # Adicionar eventos processados
    for item in eventos_processados:
        resultado.append({
            "evento": item.get("evento", {}),
            "analise": item.get("analise", {}),
            "auditoria": item.get("auditoria", {}),
            "acao_final": item.get("acao_final", ""),
            "previsao": item.get("previsao", {}),
            "plano_acao": item.get("plano_acao", {}),
            "execucao": item.get("execucao", {}),
            "from_cache": False
        })
    
    return resultado