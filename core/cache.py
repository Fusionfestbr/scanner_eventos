"""
Sistema de Cache Inteligente para eventos.
Memoriza eventos já processados para evitar re-análise via LLM.
"""
import hashlib
import json
import os
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple

CACHE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "eventos_cache.json")
STATS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "artistas_stats.json")

REANALISE_DIAS_MIN = 7
REANALISE_DIAS_MAX = 30

_cache_em_memoria: Dict[str, dict] = {}
_lock_cache = threading.RLock()

_artistas_frequencia: Dict[str, int] = {}
_artistas_confianca: Dict[str, float] = {}
_cache_inicializado = False


def get_cache() -> Dict[str, dict]:
    """Retorna cache em memória, inicializando se necessário."""
    global _cache_inicializado
    if not _cache_inicializado:
        inicializar_cache_em_memoria()
        _cache_inicializado = True
    return _cache_em_memoria


def gerar_ttl_dias(evento: dict, artista_frequencia: int = 0, confianca_anterior: float = 0.0) -> int:
    """
    Calcula TTL dinâmico baseado em múltiplos fatores.
    
    Args:
        evento: Dados do evento
        artista_frequencia: Quantas vezes o artista já foi analisado
        confianca_anterior: Nota de confiança da análise anterior (0-10)
    
    Returns:
        Dias até re-análise necessária
    """
    ttl = REANALISE_DIAS_MIN
    
    if confianca_anterior >= 8.0:
        ttl = min(REANALISE_DIAS_MAX, ttl + 10)
    elif confianca_anterior >= 6.0:
        ttl = min(REANALISE_DIAS_MAX, ttl + 5)
    elif confianca_anterior < 4.0:
        ttl = max(REANALISE_DIAS_MIN, ttl - 3)
    
    if artista_frequencia >= 10:
        ttl = min(REANALISE_DIAS_MAX, ttl + 7)
    elif artista_frequencia >= 5:
        ttl = min(REANALISE_DIAS_MAX, ttl + 3)
    elif artista_frequencia == 0:
        ttl = max(REANALISE_DIAS_MIN, ttl - 2)
    
    return ttl


def esta_fresco(evento_cache: dict) -> Tuple[bool, int]:
    """
    Verifica se o evento no cache ainda é válido com TTL dinâmico.
    
    Returns:
        (é fresco, ttl_usado)
    """
    data_processamento = evento_cache.get("data_processamento")
    if not data_processamento:
        return False, REANALISE_DIAS_MIN
    
    try:
        dt = datetime.fromisoformat(data_processamento)
        dias_passados = (datetime.now() - dt).days
        
        ttl = evento_cache.get("ttl_dias", REANALISE_DIAS_MIN)
        
        if ttl <= 0:
            ttl = REANALISE_DIAS_MIN
        
        return dias_passados < ttl, ttl
    except (ValueError, TypeError):
        return False, REANALISE_DIAS_MIN


def _atualizar_cache_em_memoria(evento_id: str, dados: dict) -> None:
    """Atualiza cache em memória para acesso rápido."""
    global _cache_em_memoria
    with _lock_cache:
        _cache_em_memoria[evento_id] = dados


def _buscar_cache_em_memoria(evento_id: str) -> Optional[dict]:
    """Busca no cache em memória (sem lock de arquivo)."""
    with _lock_cache:
        return _cache_em_memoria.get(evento_id)


def inicializar_cache_em_memoria() -> None:
    """Carrega todo cache para memória na inicialização."""
    global _cache_em_memoria, _artistas_frequencia, _artistas_confianca
    cache = carregar_cache()
    
    with _lock_cache:
        _cache_em_memoria = cache.get("eventos", {}).copy()
    
    _carregar_stats_artistas()
    
    for evento_id, dados in _cache_em_memoria.items():
        artista = dados.get("artista", "").lower()
        if artista:
            _artistas_frequencia[artista] = _artistas_frequencia.get(artista, 0)
            analise = dados.get("analise", {})
            confianca = analise.get("confiança", analise.get("confianca", 0.0))
            if isinstance(confianca, (int, float)):
                if _artistas_confianca.get(artista, 0) == 0:
                    _artistas_confianca[artista] = confianca
    
    print(f"[CACHE] Inicializado com {len(_cache_em_memoria)} eventos em memória")


def _carregar_stats_artistas() -> None:
    """Carrega estatísticas de artistas do arquivo."""
    global _artistas_frequencia, _artistas_confianca
    
    if not os.path.exists(STATS_FILE):
        return
    
    try:
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            dados = json.load(f)
            _artistas_frequencia = dados.get("frequencia", {})
            for k, v in dados.get("confianca", {}).items():
                _artistas_confianca[k] = float(v)
    except:
        pass


def _salvar_stats_artistas() -> None:
    """Salva estatísticas de artistas."""
    with _lock_cache:
        dados = {
            "frequencia": dict(_artistas_frequencia),
            "confianca": {k: float(v) for k, v in _artistas_confianca.items()},
            "ultima_atualizacao": datetime.now().isoformat()
        }
        
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)


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
    """Verifica se o evento no cache ainda é válido (usa TTL dinâmico)."""
    fresco, _ = esta_fresco_com_ttl(evento_cache)
    return fresco


def esta_fresco_com_ttl(evento_cache: dict) -> Tuple[bool, int]:
    """
    Verifica se o evento no cache ainda é válido com TTL dinâmico.
    
    Returns:
        (é fresco, ttl_usado)
    """
    data_processamento = evento_cache.get("data_processamento")
    if not data_processamento:
        return False, REANALISE_DIAS_MIN
    
    try:
        dt = datetime.fromisoformat(data_processamento)
        dias_passados = (datetime.now() - dt).days
        
        ttl = evento_cache.get("ttl_dias", REANALISE_DIAS_MIN)
        
        if ttl <= 0:
            ttl = REANALISE_DIAS_MIN
        
        return dias_passados < ttl, ttl
    except (ValueError, TypeError):
        return False, REANALISE_DIAS_MIN


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
    
    artista = evento.get("artista", "").lower()
    confianca = 0.0
    if analise:
        confianca = analise.get("confiança", analise.get("confianca", 0.0))
        if isinstance(confianca, str):
            try:
                confianca = float(confianca)
            except:
                confianca = 0.0
    
    freq = _artistas_frequencia.get(artista, 0)
    ttl = gerar_ttl_dias(evento, freq, confianca)
    
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
        "ttl_dias": ttl,
        "data_processamento": datetime.now().isoformat(),
        "ultima_atualizacao": datetime.now().isoformat()
    }
    
    if artista:
        _artistas_frequencia[artista] = freq + 1
        _artistas_confianca[artista] = confianca
    
    _atualizar_cache_em_memoria(evento_id, cache["eventos"][evento_id])
    
    cache["metadados"]["total_eventos"] = len(cache["eventos"])
    salvar_cache(cache)
    _salvar_stats_artistas()


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
    Processa eventos comparando com cache (usa cache em memória primeiro).
    
    Returns:
        tuple: (eventos_do_cache, eventos_para_processar, stats)
    """
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
        
        evento_cache = _buscar_cache_em_memoria(evento_id)
        
        if evento_cache:
            if esta_valido(evento_cache):
                if esta_fresco(evento_cache):
                    eventos_do_cache.append({
                        "do_cache": True,
                        "evento": evento,
                        "cache": evento_cache
                    })
                    stats["cache_hits"] += 1
                else:
                    eventos_para_processar.append(evento)
                    stats["re_analises"] += 1
            else:
                eventos_para_processar.append(evento)
                stats["cache_misses"] += 1
        else:
            eventos_para_processar.append(evento)
            stats["cache_misses"] += 1
    
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