import json
import os
from datetime import datetime
from typing import List, Dict, Optional

HISTORICO_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "historico_eventos.json")


def carregar_historico() -> List[Dict]:
    """Carrega histórico de eventos do JSON."""
    if not os.path.exists(HISTORICO_FILE):
        return []
    try:
        with open(HISTORICO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def salvar_historico(historico: List[Dict]) -> None:
    """Salva histórico no JSON."""
    os.makedirs(os.path.dirname(HISTORICO_FILE), exist_ok=True)
    with open(HISTORICO_FILE, "w", encoding="utf-8") as f:
        json.dump(historico, f, ensure_ascii=False, indent=2)


def adicionar_evento(evento: Dict) -> None:
    """Adiciona novo evento ao histórico."""
    historico = carregar_historico()
    
    novo_registro = {
        "nome_evento": evento.get("nome_evento", ""),
        "artista": evento.get("artista", ""),
        "data_evento": evento.get("data_evento", ""),
        "preco_inicial": evento.get("preco_inicial", 0),
        "preco_maximo_revenda": evento.get("preco_maximo_revenda", 0),
        "esgotou": evento.get("esgotou", False),
        "dias_para_esgotar": evento.get("dias_para_esgotar", 0),
        "data_registro": datetime.now().isoformat()
    }
    
    historico.append(novo_registro)
    salvar_historico(historico)


def buscar_artista(nome_artista: str) -> List[Dict]:
    """Busca eventos de um artista no histórico."""
    historico = carregar_historico()
    return [e for e in historico if e.get("artista", "").lower() == nome_artista.lower()]


def obter_estatisticas_artista(nome_artista: str) -> Dict:
    """Retorna estatísticas de um artista no histórico."""
    eventos = buscar_artista(nome_artista)
    
    if not eventos:
        return {
            "total_eventos": 0,
            "taxa_esgotamento": 0,
            "media_dias_esgotar": 0,
            "valorizacao_media": 0
        }
    
    total = len(eventos)
    esgotados = sum(1 for e in eventos if e.get("esgotou", False))
    
    dias_esgotar = [e.get("dias_para_esgotar", 0) for e in eventos if e.get("dias_para_esgotar", 0) > 0]
    media_dias = sum(dias_esgotar) / len(dias_esgotar) if dias_esgotar else 0
    
    valorizacoes = []
    for e in eventos:
        preco_inicial = e.get("preco_inicial", 0)
        preco_max = e.get("preco_maximo_revenda", 0)
        if preco_inicial > 0:
            valorizacao = ((preco_max - preco_inicial) / preco_inicial) * 100
            valorizacoes.append(valorizacao)
    
    valorizacao_media = sum(valorizacoes) / len(valorizacoes) if valorizacoes else 0
    
    return {
        "total_eventos": total,
        "taxa_esgotamento": (esgotados / total) * 100,
        "media_dias_esgotar": round(media_dias, 1),
        "valorizacao_media": round(valorizacao_media, 1)
    }


def obter_tipos_evento(nome_evento: str) -> str:
    """Determina o tipo de evento baseado no nome."""
    nome_lower = nome_evento.lower()
    
    indicadores_festival = ["festival", "festa", "day festival"]
    indicadores_turne = ["tour", "turnê", "world tour", "live tour"]
    indicadores_show = ["show", "live", "em concerto"]
    
    for ind in indicadores_festival:
        if ind in nome_lower:
            return "festival"
    
    for ind in indicadores_turne:
        if ind in nome_lower:
            return "turnê"
    
    return "show único"