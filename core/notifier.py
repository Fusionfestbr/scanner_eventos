"""
Módulo de notificações via Telegram.
Envia alertas quando oportunidades são detectadas.
"""
import json
import os
import requests
from datetime import datetime
from typing import Optional, Dict

from config import (
    TELEGRAM_TOKEN,
    TELEGRAM_CHAT_ID,
    ALERTA_ENABLED,
    ALERTA_NOTA_MINIMA,
    ALERTA_CONFIANCA_MINIMA,
    NOTIFICADOS_FILE
)


def carregar_notificados() -> set:
    """Carrega IDs dos eventos já notificados."""
    if not os.path.exists(NOTIFICADOS_FILE):
        return set()
    try:
        with open(NOTIFICADOS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("ids", []))
    except (json.JSONDecodeError, IOError):
        return set()


def salvar_notificados(ids: set) -> None:
    """Salva IDs dos eventos notificados."""
    os.makedirs(os.path.dirname(NOTIFICADOS_FILE), exist_ok=True)
    with open(NOTIFICADOS_FILE, "w", encoding="utf-8") as f:
        json.dump({"ids": list(ids), "ultima_att": datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)


def gerar_id_evento(evento: dict) -> str:
    """Gera ID único para o evento."""
    nome = evento.get("nome", "")
    data = evento.get("data", "")
    return f"{nome}_{data}".replace(" ", "_")


def ja_notificado(evento_id: str) -> bool:
    """Verifica se evento já foi notificado."""
    notificados = carregar_notificados()
    return evento_id in notificados


def marcar_notificado(evento_id: str) -> None:
    """Marca evento como notificado."""
    notificados = carregar_notificados()
    notificados.add(evento_id)
    salvar_notificados(notificados)


def formatar_mensagem(evento: dict, analise: dict, auditoria: dict, plano_acao: Optional[Dict] = None) -> str:
    """Formata mensagem de alerta."""
    nome = evento.get("nome", "N/A")
    artista = evento.get("artista", "N/A")
    data = evento.get("data", "N/A")
    cidade = evento.get("cidade", "N/A")
    
    nota = analise.get("nota_final", 0)
    confianca = auditoria.get("confianca", 0)
    comentario = auditoria.get("comentario", "")[:100]
    
    mensagem = f"""🚨 <b>OPORTUNIDADE DETECTADA</b>

📌 <b>Evento:</b> {nome}
🎤 <b>Artista:</b> {artista}
📅 <b>Data:</b> {data}
📍 <b>Cidade:</b> {cidade}

⭐ <b>Nota:</b> {nota:.1f}/10
🎯 <b>Confiança:</b> {confianca}/10

✅ <b>AÇÃO: COMPRAR</b>

<i>{comentario}...</i>"""
    
    if plano_acao and plano_acao.get("comprar"):
        qtd = plano_acao.get("quantidade", {})
        momento = plano_acao.get("momento_compra", "N/A")
        estrategia = plano_acao.get("estrategia_saida", "N/A")
        preco_alvo = plano_acao.get("preco_alvo_venda", 0)
        margem = plano_acao.get("margem_estimada", "0%")
        
        qtd_recomendada = qtd.get("recomendado", "N/A") if isinstance(qtd, dict) else qtd
        
        mensagem += f"""

💰 <b>SUGESTÃO DE COMPRA</b>
📊 Qtd recomendada: {qtd_recomendada} ingresso(s)
⏰ Timing: {momento}
📈 Estratégia saída: {estrategia}
🎯 Preço alvo venda: R$ {preco_alvo:.2f}
💵 Margem estimada: {margem}"""
    
    return mensagem


def enviar_alerta(evento: dict, analise: dict, auditoria: dict, plano_acao: Optional[Dict] = None) -> bool:
    """
    Envia alerta via Telegram.
    
    Args:
        evento: Dados do evento
        analise: Dados da análise
        auditoria: Dados da auditoria
        plano_acao: Dados do plano de ação (opcional)
    
    Returns:
        True se enviado com sucesso
    """
    if not ALERTA_ENABLED:
        return False
    
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    
    mensagem = formatar_mensagem(evento, analise, auditoria)
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensagem,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            return True
        else:
            print(f"   [ERRO] Telegram: {response.text}")
            return False
    except Exception as e:
        print(f"   [ERRO] Telegram falhou: {e}")
        return False


def verificar_e_enviar_alerta(evento: dict, analise: dict, auditoria: dict, acao: str, plano_acao: Optional[Dict] = None) -> bool:
    """
    Verifica critérios e envia alerta se necessário.
    
    Args:
        evento: Dados do evento
        analise: Dados da análise
        auditoria: Dados da auditoria
        acao: Ação final (COMPRAR, MONITORAR, IGNORAR)
        plano_acao: Dados do plano de ação (opcional)
    
    Returns:
        True se alerta foi enviado
    """
    if acao != "COMPRAR":
        return False
    
    nota = analise.get("nota_final", 0)
    confianca = auditoria.get("confianca", 0)
    
    if nota < ALERTA_NOTA_MINIMA:
        return False
    
    if confianca < ALERTA_CONFIANCA_MINIMA:
        return False
    
    evento_id = gerar_id_evento(evento)
    
    if ja_notificado(evento_id):
        return False
    
    sucesso = enviar_alerta(evento, analise, auditoria, plano_acao)
    
    if sucesso:
        marcar_notificado(evento_id)
    
    return sucesso


def testar_conexao() -> bool:
    """Testa conexão com Telegram."""
    if not TELEGRAM_TOKEN:
        print("  Token não configurado")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                print(f"  Bot conectado: @{data['result']['username']}")
                return True
        print(f"  Erro: {response.text}")
        return False
    except Exception as e:
        print(f"  Falha: {e}")
        return False
