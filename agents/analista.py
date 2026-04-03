"""
Agente analista de eventos via IA local (LM Studio).
"""
import json
import re
import requests

from config import LM_STUDIO_URL, MODEL, REQUEST_TIMEOUT, MAX_TOKENS


def carregar_prompt() -> str:
    """Carrega o prompt base do arquivo."""
    import os
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prompt_path = os.path.join(base_dir, "prompts", "analista.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def construir_prompt_evento(evento: dict) -> list[dict]:
    """Constrói mensagens para a API."""
    nome = evento.get('nome', '')
    artista = evento.get('artista', '')
    data = evento.get('data', '')
    cidade = evento.get('cidade', '')
    
    evento_info = f"Evento: {nome}, Artista: {artista}, Data: {data}, Cidade: {cidade}. Notas 0-10 hype/escassez/publico/potencial_revenda. nota_final = media. Retorne APENAS JSON."
    
    messages = [
        {"role": "system", "content": "Você é especialista em análise de eventos para revenda de ingressos. Retorne APENAS JSON válido."},
        {"role": "user", "content": evento_info}
    ]
    return messages


def chamar_llm(messages: list[dict]) -> str | None:
    """Envia requisição para LM Studio."""
    for attempt in range(2):
        payload = {
            "model": MODEL,
            "messages": messages,
            "max_tokens": MAX_TOKENS,
            "disable_thinking": True
        }
        try:
            response = requests.post(
                LM_STUDIO_URL,
                json=payload,
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            
            message = data["choices"][0]["message"]
            
            content = message.get("content", "")
            reasoning = message.get("reasoning_content", "")
            
            full_text = content or reasoning or ""
            
            if full_text:
                return full_text
        except requests.exceptions.RequestException as e:
            print(f"   [ERRO] Requisição falhou: {e}")
            return None
        except (KeyError, IndexError) as e:
            print(f"   [ERRO] Resposta inválida: {e}")
            return None
    
    return None


def extrair_json(resposta: str) -> dict | None:
    """Extrai JSON da resposta do LLM."""
    if not resposta:
        return None
    
    import re
    
    match = re.search(r'\{[^{}]*"hype"[^{}]*\}', resposta, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
            if "hype" in result:
                return result
        except json.JSONDecodeError:
            pass
    
    match = re.search(r'"hype"\s*:\s*[\d.]+', resposta)
    if match:
        hype_match = re.search(r'"hype"\s*:\s*([\d.]+)', resposta)
        escassez_match = re.search(r'"escassez"\s*:\s*([\d.]+)', resposta)
        publikco_match = re.search(r'"publico"\s*:\s*([\d.]+)', resposta)
        revenda_match = re.search(r'"potencial_revenda"\s*:\s*([\d.]+)', resposta)
        nota_match = re.search(r'"nota_final"\s*:\s*([\d.]+)', resposta)
        
        if hype_match:
            result = {
                "hype": float(hype_match.group(1)),
                "escassez": float(escassez_match.group(1)) if escassez_match else 0,
                "publico": float(publikco_match.group(1)) if publikco_match else 0,
                "potencial_revenda": float(revenda_match.group(1)) if revenda_match else 0,
                "nota_final": float(nota_match.group(1)) if nota_match else 0,
                "justificativa": "Extraido do reasoning"
            }
            return result
    
    return None


def analisar_evento(evento: dict) -> dict:
    """Analisa um único evento via LLM."""
    messages = construir_prompt_evento(evento)
    
    resposta = chamar_llm(messages)
    
    if resposta:
        analise = extrair_json(resposta)
        if analise:
            return analise
    
    return {
        "hype": 0,
        "escassez": 0,
        "publico": 0,
        "potencial_revenda": 0,
        "nota_final": 0,
        "justificativa": "Analise indisponivel",
        "analise_indisponivel": True
    }


def analisar_eventos(eventos: list[dict]) -> list[dict]:
    """
    Analisa lista de eventos via LLM.
    Retorna lista com eventos + análise (parcial em caso de falha).
    """
    resultados = []
    
    for i, evento in enumerate(eventos, 1):
        print(f"   Analisando evento {i}/{len(eventos)}: {evento.get('nome', 'N/A')}")
        
        analise = analisar_evento(evento)
        resultados.append({
            "evento": evento,
            "analise": analise
        })
    
    return resultados
