"""
Agente auditor de eventos.
Revisa análises e gera decisões.
"""
import json
import re
import requests

from config import LM_STUDIO_URL, MODEL, REQUEST_TIMEOUT, MAX_TOKENS


def construir_prompt_auditoria(evento: dict, analise: dict) -> list[dict]:
    """Constrói prompt para auditoria."""
    prompt = f"""Você é um auditor especializado em tomada de decisão no mercado de eventos.

Revise a análise abaixo e verifique:
- se as notas fazem sentido
- se há inconsistências
- se o evento ainda é relevante (baseado na data)

Evento: {evento.get('nome', '')}, Artista: {evento.get('artista', '')}, Data: {evento.get('data', '')}, Cidade: {evento.get('cidade', '')}
Análise: hype={analise.get('hype', 0)}, escassez={analise.get('escassez', 0)}, publikco={analise.get('publico', 0)}, potencial_revenda={analise.get('potencial_revenda', 0)}, nota_final={analise.get('nota_final', 0)}

Retorne APENAS JSON válido:
{{"decisao": "COMPRAR" | "MONITORAR" | "IGNORAR", "confianca": 0-10, "erro_detectado": true/false, "comentario": ""}}"""
    
    return [
        {"role": "system", "content": "Você é auditor especializado em eventos. Retorne APENAS JSON válido."},
        {"role": "user", "content": prompt}
    ]


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
    """Audita lista de eventos."""
    resultados = []
    
    for i, item in enumerate(eventos_analisados, 1):
        evento = item["evento"]
        analise = item["analise"]
        
        nome = evento.get("nome", "N/A")
        print(f"   Auditando evento {i}/{len(eventos_analisados)}: {nome}")
        
        auditoria = auditar_evento(evento, analise)
        
        resultados.append({
            "evento": evento,
            "analise": analise,
            "auditoria": auditoria
        })
    
    return resultados
