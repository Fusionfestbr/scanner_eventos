"""
Agente auditor de eventos.
Revisa análises e gera decisões.
"""
import json
import re
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from config import LM_STUDIO_URL, MODEL, REQUEST_TIMEOUT, MAX_TOKENS, LLM_WORKERS

_lock = threading.Lock()
_counter = 0

def _increment_counter():
    global _counter
    with _lock:
        _counter += 1
        return _counter


def construir_prompt_auditoria(evento: dict, analise: dict) -> list[dict]:
    """Constrói prompt para auditoria (template em prompts/auditor.txt)."""
    prompt = (
        carregar_prompt()
        .replace("{nome}", str(evento.get("nome", "")))
        .replace("{artista}", str(evento.get("artista", "")))
        .replace("{data}", str(evento.get("data", "")))
        .replace("{cidade}", str(evento.get("cidade", "")))
        .replace("{hype}", str(analise.get("hype", 0)))
        .replace("{escassez}", str(analise.get("escassez", 0)))
        .replace("{publico}", str(analise.get("publico", 0)))
        .replace("{potencial_revenda}", str(analise.get("potencial_revenda", 0)))
        .replace("{nota_final}", str(analise.get("nota_final", 0)))
    )

    return [
        {"role": "system", "content": "Você é auditor especializado em eventos. Retorne APENAS JSON válido."},
        {"role": "user", "content": prompt}
    ]


def carregar_prompt() -> str:
    """Carrega o template de auditoria (prompts/auditor.txt)."""
    import os
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prompt_path = os.path.join(base_dir, "prompts", "auditor.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def chamar_llm(messages: list[dict]) -> str | None:
    """Envia requisição para LM Studio."""
    payload = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": MAX_TOKENS,
        "disable_thinking": True
    }
    try:
        response = requests.post(LM_STUDIO_URL, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"].get("content", "")
    except Exception as e:
        print(f"   [ERRO] Auditoria falhou: {e}")
        return None


def extrair_json(resposta: str) -> dict | None:
    """Extrai JSON da resposta."""
    if not resposta:
        return None
    
    resposta = resposta.strip()
    resposta = resposta.replace("```json", "").replace("```", "")
    
    start = resposta.find("{")
    end = resposta.rfind("}") + 1
    
    if start >= 0 and end > start:
        try:
            return json.loads(resposta[start:end])
        except json.JSONDecodeError:
            pass
    
    return None


def auditar_evento(evento: dict, analise: dict) -> dict:
    """Audita um evento."""
    messages = construir_prompt_auditoria(evento, analise)
    
    resposta = chamar_llm(messages)
    
    if resposta:
        auditoria = extrair_json(resposta)
        if auditoria and "decisao" in auditoria:
            return auditoria
    
    return {
        "decisao": "IGNORAR",
        "confianca": 0,
        "erro_detectado": True,
        "comentario": "Auditoria indisponível"
    }


def auditar_eventos(eventos_analisados: list[dict]) -> list[dict]:
    """Audita lista de eventos em paralelo."""
    global _counter
    _counter = 0
    resultados = [None] * len(eventos_analisados)

    def auditar_com_indice(idx, item):
        evento = item["evento"]
        analise = item["analise"]
        auditoria = auditar_evento(evento, analise)
        count = _increment_counter()
        nome = evento.get("nome", "N/A")[:60]
        decisao = auditoria.get("decisao", "IGNORAR")
        confianca = auditoria.get("confianca", 0)
        print(f"   [{count}/{len(eventos_analisados)}] {nome} -> {decisao} (conf: {confianca})")
        return idx, {
            "evento": evento,
            "analise": analise,
            "auditoria": auditoria
        }

    with ThreadPoolExecutor(max_workers=LLM_WORKERS) as executor:
        futures = {executor.submit(auditar_com_indice, i, item): i for i, item in enumerate(eventos_analisados)}
        for future in as_completed(futures):
            idx, resultado = future.result()
            resultados[idx] = resultado

    return resultados
