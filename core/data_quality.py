"""
Módulo de qualidade e confiabilidade de dados.
"""
import json
import os
import re
from datetime import datetime, date
from typing import Tuple, List, Dict

from config import MIN_QUALITY_PERCENT, FALLBACK_ENABLED, REJECTED_FILE


def validar_nome(nome: str) -> bool:
    """Valida nome do evento."""
    if not nome or not isinstance(nome, str):
        return False
    nome = nome.strip()
    return len(nome) >= 3


def validar_data(data_str: str) -> Tuple[bool, str]:
    """
    Valida data do evento.
    
    Returns:
        (é_válida, motivo)
    """
    if not data_str or not isinstance(data_str, str):
        return False, "data ausente"
    
    data_str = data_str.strip()
    
    formatos = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d"
    ]
    
    data_obj = None
    for fmt in formatos:
        try:
            data_obj = datetime.strptime(data_str, fmt)
            break
        except ValueError:
            continue
    
    if not data_obj:
        return False, "formato inválido"
    
    if data_obj.date() < date.today():
        return False, "data passada"
    
    return True, ""


def validar_cidade(cidade: str) -> bool:
    """Valida cidade."""
    if not cidade or not isinstance(cidade, str):
        return False
    cidade = cidade.strip()
    return len(cidade) >= 2


def validar_evento(evento: dict) -> Tuple[bool, str]:
    """
    Valida um evento.
    
    Returns:
        (é_válido, motivo_rejeição)
    """
    nome = evento.get("nome", "")
    if not validar_nome(nome):
        return False, "nome inválido"
    
    data = evento.get("data", "")
    valida, motivo = validar_data(data)
    if not valida:
        return False, f"data inválida: {motivo}"
    
    cidade = evento.get("cidade", "")
    if not validar_cidade(cidade):
        return False, "cidade inválida"
    
    return True, ""


def filtrar_eventos_validos(eventos: list[dict]) -> Tuple[list[dict], list[dict]]:
    """
    Filtra eventos válidos vs rejeitados.
    
    Returns:
        (validos, rejeitados)
    """
    validos = []
    rejeitados = []
    
    for evento in eventos:
        valido, motivo = validar_evento(evento)
        
        if valido:
            validos.append(evento)
        else:
            rejeitados.append({
                "evento": evento,
                "motivo": motivo,
                "timestamp": datetime.now().isoformat()
            })
    
    return validos, rejeitados


def calcular_score(validos: int, total: int) -> dict:
    """
    Calcula score de qualidade.
    
    Returns:
        Dicionário com métricas
    """
    if total == 0:
        return {
            "taxa_validos": 0,
            "taxa_rejeitados": 100,
            "total": 0,
            "validos": 0,
            "rejeitados": 0,
            "score": 0
        }
    
    taxa_validos = (validos / total) * 100
    taxa_rejeitados = 100 - taxa_validos
    
    return {
        "taxa_validos": round(taxa_validos, 1),
        "taxa_rejeitados": round(taxa_rejeitados, 1),
        "total": total,
        "validos": validos,
        "rejeitados": total - validos,
        "score": round(taxa_validos, 1)
    }


def verificar_qualidade(validos: int, total: int) -> Tuple[bool, str]:
    """
    Verifica se a qualidade é aceitável.
    
    Returns:
        (qualidade_aceitável, mensagem)
    """
    score = calcular_score(validos, total)
    taxa = score["taxa_validos"]
    
    if taxa >= MIN_QUALITY_PERCENT:
        return True, f"Qualidade OK: {taxa}% válidos"
    
    msg = f"[ALERTA] Baixa qualidade: apenas {taxa}% válidos ({validos}/{total})"
    return False, msg


def salvar_rejeitados(rejeitados: list[dict]) -> None:
    """Salva eventos rejeitados em JSON."""
    if not rejeitados:
        return
    
    os.makedirs(os.path.dirname(REJECTED_FILE), exist_ok=True)
    
    existing = []
    if os.path.exists(REJECTED_FILE):
        try:
            with open(REJECTED_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    
    existing.extend(rejeitados)
    
    with open(REJECTED_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)


def carregar_rejeitados() -> list[dict]:
    """Carrega eventos rejeitados."""
    if not os.path.exists(REJECTED_FILE):
        return []
    try:
        with open(REJECTED_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def checar_fallback(validos: int, total: int) -> Tuple[bool, bool]:
    """
    Verifica se deve usar fallback.
    
    Returns:
        (qualidade_aceitável, fallback_permitido)
    """
    score = calcular_score(validos, total)
    taxa = score["taxa_validos"]
    
    if taxa >= MIN_QUALITY_PERCENT:
        return True, True
    
    if not FALLBACK_ENABLED:
        return False, False
    
    return False, True


def extrair_data_de_texto(texto: str) -> str:
    """Extrai data de texto livre usando regex."""
    if not texto:
        return ""
    
    texto = texto.strip()
    
    patterns = [
        (r"(\d{4})-(\d{2})-(\d{2})", "%Y-%m-%d"),
        (r"(\d{2})/(\d{2})/(\d{4})", "%d/%m/%Y"),
        (r"(\d{2})-(\d{2})-(\d{4})", "%d-%m-%Y"),
        (r"(\d{2}) de (\w+) de (\d{4})", None),
    ]
    
    for pattern, fmt in patterns:
        match = re.search(pattern, texto)
        if match:
            if fmt:
                try:
                    dt = datetime.strptime(match.group(), fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue
            else:
                meses = {
                    "janeiro": "01", "fevereiro": "02", "março": "03", "abril": "04",
                    "maio": "05", "junho": "06", "julho": "07", "agosto": "08",
                    "setembro": "09", "outubro": "10", "novembro": "11", "dezembro": "12"
                }
                if len(match.groups()) == 3:
                    dia, mes_nome, ano = match.groups()
                    mes = meses.get(mes_nome.lower(), "01")
                    return f"{ano}-{mes}-{dia.zfill(2)}"
    
    return ""
