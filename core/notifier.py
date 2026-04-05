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


def formatar_mensagem(
    evento: dict, 
    analise: dict, 
    auditoria: dict, 
    plano_acao: Optional[Dict] = None, 
    arbitragem: Optional[Dict] = None,
    execucao: Optional[Dict] = None
) -> tuple[str, list]:
    """Formata mensagem de alerta com inline keyboard opcional."""
    nome = evento.get("nome", "N/A")
    artista = evento.get("artista", "N/A")
    data = evento.get("data", "N/A")
    cidade = evento.get("cidade", "N/A")
    fonte = evento.get("fonte", "N/A")
    link = evento.get("link", "")
    
    nota = analise.get("nota_final", 0)
    confianca = auditoria.get("confianca", 0)
    comentario = auditoria.get("comentario", "")[:100]
    
    previsao_score = 0
    previsao_prob = 0
    if execucao:
        previsao_score = execucao.get("score", 0)
        previsao_prob = execucao.get("probabilidade_esgotar", 0)
    
    prioridade = ""
    if execucao and execucao.get("prioridade"):
        p = execucao["prioridade"]
        if p == "alta":
            prioridade = " 🔴 ALTA"
        elif p == "média":
            prioridade = " 🟡 MÉDIA"
        else:
            prioridade = " 🟢 BAIXA"
    
    emoji_urgencia = ""
    if execucao and execucao.get("urgencia"):
        emoji_urgencia = " ⏰ URGENTE"
    
    mensagem = f"""🚨 <b>OPORTUNIDADE REAL{prioridade}{emoji_urgencia}</b>

📌 <b>Evento:</b> {nome}
🎤 <b>Artista:</b> {artista}
📅 <b>Data:</b> {data}
📍 <b>Cidade:</b> {cidade}

⭐ <b>Nota:</b> {nota:.1f}/10
🎯 <b>Confiança:</b> {confianca}/10"""

    if previsao_score > 0:
        mensagem += f"""
📈 <b>Score Valorização:</b> {previsao_score}/10
⚡ <b>Prob. Esgotamento:</b> {previsao_prob}%"""

    mensagem += f"""

✅ <b>AÇÃO: COMPRAR</b>

<i>{comentario}...</i>"""
    
    inline_buttons = []
    
    if execucao and execucao.get("link_direto"):
        link_compra = execucao["link_direto"]
        plataforma = execucao.get("melhor_plataforma", "site")
        preco = execucao.get("preco_estimado", 0)
        
        qtd = 1
        if plano_acao and plano_acao.get("quantidade"):
            qtd = plano_acao["quantidade"].get("recomendado", 1)
        
        if preco > 0:
            mensagem += f"""

💰 <b>LINK DIRETO</b>
🔗 Plataforma: {plataforma}
💵 Preço estimado: R$ {preco:.2f}
📊 Qtd: {qtd} ingresso(s)"""
        else:
            mensagem += f"""

🔗 <b>Link direto:</b> {link_compra}"""
        
        inline_buttons.append([
            {"text": "💰 COMPRAR AGORA", "url": link_compra},
            {"text": "📋 Ver detalhes", "url": link or link_compra}
        ])
    
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
    
    if arbitragem and arbitragem.get("oportunidade"):
        menor = arbitragem.get("menor_preco", 0)
        maior = arbitragem.get("maior_preco", 0)
        spread = arbitragem.get("spread_percent", 0)
        lucro = arbitragem.get("lucro_potencial", 0)
        fonte_menor = arbitragem.get("fonte_menor", "N/A")
        fonte_maior = arbitragem.get("fonte_maior", "N/A")
        
        mensagem += f"""

💸 <b>ARBITRAGEM DETECTADA</b>
💰 Menor: R$ {menor:.2f} ({fonte_menor})
💵 Maior: R$ {maior:.2f} ({fonte_maior})
📊 Spread: {spread:.1f}%
💵 Lucro: R$ {lucro:.2f}"""
    
    return mensagem, inline_buttons


def enviar_alerta(
    evento: dict, 
    analise: dict, 
    auditoria: dict, 
    plano_acao: Optional[Dict] = None, 
    arbitragem: Optional[Dict] = None,
    execucao: Optional[Dict] = None
) -> bool:
    """
    Envia alerta via Telegram com inline keyboard opcional.
    
    Args:
        evento: Dados do evento
        analise: Dados da análise
        auditoria: Dados da auditoria
        plano_acao: Dados do plano de ação (opcional)
        arbitragem: Dados da arbitragem (opcional)
        execucao: Dados de execução (opcional)
    
    Returns:
        True se enviado com sucesso
    """
    if not ALERTA_ENABLED:
        return False
    
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    
    mensagem, inline_buttons = formatar_mensagem(evento, analise, auditoria, plano_acao, arbitragem, execucao)
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensagem,
        "parse_mode": "HTML"
    }
    
    if inline_buttons:
        payload["reply_markup"] = {
            "inline_keyboard": inline_buttons
        }
    
    try:
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            return True
        else:
            print(f"   [ERRO] Telegram HTTP {response.status_code}: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"   [ERRO] Telegram request falhou: {e}")
        return False
    except Exception as e:
        print(f"   [ERRO] Telegram falhou inesperado: {e}")
        import traceback
        traceback.print_exc()
        return False


def verificar_e_enviar_alerta(
    evento: dict, 
    analise: dict, 
    auditoria: dict, 
    acao: str, 
    plano_acao: dict | None = None, 
    arbitragem: dict | None = None,
    execucao: dict | None = None
) -> bool:
    """
    Verifica critérios e envia alerta se necessário.
    
    Args:
        evento: Dados do evento
        analise: Dados da análise
        auditoria: Dados da auditoria
        acao: Ação final (COMPRAR, MONITORAR, IGNORAR)
        plano_acao: Dados do plano de ação (opcional)
        arbitragem: Dados da arbitragem (opcional)
        execucao: Dados de execução (opcional)
    
    Returns:
        True se alerta foi enviado
    """
    if acao != "COMPRAR":
        return False
    
    nota = analise.get("nota_final", 0)
    confianca = auditoria.get("confianca", 0)
    
    if nota < ALERTA_NOTA_MINIMA:
        print(f"   [TELEGRAM] {evento.get('nome','?')[:40]}: nota {nota:.1f} < {ALERTA_NOTA_MINIMA} - nao notifica")
        return False
    
    if confianca < ALERTA_CONFIANCA_MINIMA:
        print(f"   [TELEGRAM] {evento.get('nome','?')[:40]}: confianca {confianca} < {ALERTA_CONFIANCA_MINIMA} - nao notifica")
        return False
    
    evento_id = gerar_id_evento(evento)
    
    if ja_notificado(evento_id):
        print(f"   [TELEGRAM] {evento.get('nome','?')[:40]}: ja notificado - pulando")
        return False
    
    print(f"   [TELEGRAM] Enviando alerta: {evento.get('nome','?')[:50]} (nota={nota}, conf={confianca})")
    sucesso = enviar_alerta(evento, analise, auditoria, plano_acao, arbitragem, execucao)
    
    if sucesso:
        marcar_notificado(evento_id)
        print(f"   [TELEGRAM] Alerta enviado com sucesso!")
    else:
        print(f"   [TELEGRAM] FALHA ao enviar alerta para: {evento.get('nome','?')[:50]}")
    
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
