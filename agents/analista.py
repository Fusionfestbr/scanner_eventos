"""
Agente analista de eventos via IA local (LM Studio).
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
    """Envia requisição para LM Studio com retry."""
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
            
            choices = data.get("choices", [])
            if not choices:
                print(f"   [ERRO] Resposta sem choices (tentativa {attempt + 1})")
                continue
            
            message = choices[0].get("message", {})
            
            content = message.get("content", "")
            reasoning = message.get("reasoning_content", "")
            
            full_text = content or reasoning or ""
            
            if full_text:
                return full_text
            else:
                print(f"   [ERRO] Resposta vazia (tentativa {attempt + 1})")
                continue
        except requests.exceptions.RequestException as e:
            print(f"   [ERRO] Requisição falhou: {e}")
            continue
        except (KeyError, IndexError) as e:
            print(f"   [ERRO] Resposta inválida: {e}")
            continue
    
    return None


def extrair_json(resposta: str) -> dict | None:
    """Extrai JSON da resposta do LLM."""
    if not resposta:
        return None
    
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
        publico_match = re.search(r'"publico"\s*:\s*([\d.]+)', resposta)
        revenda_match = re.search(r'"potencial_revenda"\s*:\s*([\d.]+)', resposta)
        nota_match = re.search(r'"nota_final"\s*:\s*([\d.]+)', resposta)
        
        if hype_match:
            result = {
                "hype": float(hype_match.group(1)),
                "escassez": float(escassez_match.group(1)) if escassez_match else 0,
                "publico": float(publico_match.group(1)) if publico_match else 0,
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
    Analisa lista de eventos via LLM em paralelo.
    Retorna lista com eventos + análise (parcial em caso de falha).
    """
    global _counter
    _counter = 0
    resultados = [None] * len(eventos)

    def analisar_com_indice(idx, evento):
        analise = analisar_evento(evento)
        count = _increment_counter()
        nome = evento.get('nome', 'N/A')[:60]
        nota = analise.get('nota_final', 0)
        print(f"   [{count}/{len(eventos)}] {nome} -> nota: {nota}")
        return idx, {"evento": evento, "analise": analise}

    with ThreadPoolExecutor(max_workers=LLM_WORKERS) as executor:
        futures = {executor.submit(analisar_com_indice, i, evento): i for i, evento in enumerate(eventos)}
        for future in as_completed(futures):
            idx, resultado = future.result()
            resultados[idx] = resultado

    return resultados
