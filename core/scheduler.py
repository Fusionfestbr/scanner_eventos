"""
Scheduler para execução automática do pipeline.
"""
import json
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

from config import INTERVALO_MINUTOS, LOCK_FILE, LAST_RUN_FILE
from core.orchestrator import executar_pipeline
from core.learning import carregar_historico
from core.executor import processar_planos_acao, reavaliar_planos


running = True


def signal_handler(sig, frame):
    """Handler para Ctrl+C graceful."""
    global running
    print("\n\n[Scheduler] Parando gracefully...")
    running = False


def acquire_lock() -> bool:
    """Adquire lock para evitar execução duplicada."""
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as f:
                pid = int(f.read().strip())
            if os.name == 'nt':
                try:
                    import psutil
                    if psutil.pid_exists(pid):
                        return False
                except ImportError:
                    pass
            return False
        except (ValueError, IOError):
            pass
    
    os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)
    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))
    return True


def release_lock():
    """Libera lock."""
    try:
        os.remove(LOCK_FILE)
    except FileNotFoundError:
        pass


def save_last_run(dados: dict):
    """Salva informações do último run."""
    os.makedirs(os.path.dirname(LAST_RUN_FILE), exist_ok=True)
    with open(LAST_RUN_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def load_last_run() -> dict:
    """Carrega informações do último run."""
    if not os.path.exists(LAST_RUN_FILE):
        return {}
    try:
        with open(LAST_RUN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def filtrar_eventos_novos(eventos: list[dict]) -> list[dict]:
    """Filtra eventos que já estão no histórico."""
    historico = carregar_historico()
    
    existentes = set()
    for item in historico:
        key = f"{item.get('evento', '')}_{item.get('data', '')}"
        existentes.add(key)
    
    eventos_novos = []
    for evento in eventos:
        key = f"{evento.get('nome', '')}_{evento.get('data', '')}"
        if key not in existentes:
            eventos_novos.append(evento)
    
    return eventos_novos


def calcular_intervalo(qtd_eventos: int) -> int:
    """
    Calcula intervalo baseado no volume de eventos.
    
    Returns:
        Intervalo em minutos
    """
    if qtd_eventos >= 100:
        return 60
    elif qtd_eventos >= 50:
        return 45
    elif qtd_eventos >= 20:
        return 30
    elif qtd_eventos >= 10:
        return 20
    else:
        return 15


def executar_ciclo() -> dict:
    """Executa um ciclo do pipeline."""
    inicio = datetime.now()
    
    print(f"\n[{inicio.strftime('%Y-%m-%d %H:%M:%S')}] === INICIO DO CICLO ===")
    
    from agents.coletor import coletar_eventos
    from config import MODO_COLETA
    
    print(f"  Modo de coleta: {MODO_COLETA}")
    
    eventos_coletados = coletar_eventos()
    total_coletados = len(eventos_coletados)
    print(f"  Eventos coletados: {total_coletados}")
    
    eventos_novos = filtrar_eventos_novos(eventos_coletados)
    print(f"  Eventos novos: {len(eventos_novos)}")
    
    if not eventos_novos:
        print("  Nenhum evento novo para processar.")
        return {
            "timestamp": inicio.isoformat(),
            "coletados": total_coletados,
            "novos": 0,
            "processados": 0,
            "status": "sem_novos"
        }
    
    from agents.validador import validar_eventos
    from agents.analista import analisar_eventos
    from agents.auditor import auditar_eventos
    from core.decision import processar_decisoes
    from core.predictor import processar_previsoes
    from core.executor import processar_planos_acao
    from core.learning import salvar_evento_no_historico
    from core.notifier import verificar_e_enviar_alerta
    from core.arbitrage import processar_arbitragem
    
    eventos_validados = validar_eventos(eventos_novos)
    eventos_analisados = analisar_eventos(eventos_validados)
    eventos_auditados = auditar_eventos(eventos_analisados)
    eventos_finais = processar_decisoes(eventos_auditados)
    
    eventos_finais = processar_previsoes(eventos_finais)
    eventos_finais = processar_planos_acao(eventos_finais)
    eventos_finais = processar_arbitragem(eventos_finais, apenas_comprar=True)
    
    for item in eventos_finais:
        evento = item.get("evento", {})
        analise = item.get("analise", {})
        auditoria = item.get("auditoria", {})
        acao = item.get("acao_final", "IGNORAR")
        plano_acao = item.get("plano_acao", {})
        arbitragem = item.get("arbitragem", {})
        salvar_evento_no_historico(evento, analise, auditoria, acao)
        verificar_e_enviar_alerta(evento, analise, auditoria, acao, plano_acao, arbitragem)
    
    compras = sum(1 for e in eventos_finais if e.get("acao_final") == "COMPRAR")
    monitorar = sum(1 for e in eventos_finais if e.get("acao_final") == "MONITORAR")
    ignorar = sum(1 for e in eventos_finais if e.get("acao_final") == "IGNORAR")
    
    print(f"  Pipeline: {len(eventos_finais)} processados")
    print(f"  Decisões: COMPRAR({compras}), MONITORAR({monitorar}), IGNORAR({ignorar})")
    
    fim = datetime.now()
    duracao = (fim - inicio).total_seconds()
    
    return {
        "timestamp": inicio.isoformat(),
        "coletados": total_coletados,
        "novos": len(eventos_novos),
        "processados": len(eventos_finais),
        "comprar": compras,
        "monitorar": monitorar,
        "ignorar": ignorar,
        "duracao_segundos": duracao,
        "status": "sucesso"
    }


def executar_loop(intervalo_minutos: int | None = None, reavaliar_horas: int = 6):
    """
    Executa o loop de scheduler.
    
    Args:
        intervalo_minutos: Intervalo entre execuções (default: config.INTERVALO_MINUTOS)
        reavaliar_horas: Frequência de reavaliação em horas (default: 6h)
    """
    global running
    
    intervalo_minutos = intervalo_minutos or INTERVALO_MINUTOS
    ciclos_para_reavaliar = max(1, (reavaliar_horas * 60) // intervalo_minutos)
    ciclo_atual = 0
    
    if not acquire_lock():
        print("[ERROR] Scheduler já está rodando!")
        sys.exit(1)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("=" * 50)
    print("  Fusion Revenda Master - SCHEDULER")
    print("=" * 50)
    print(f"  Intervalo: {intervalo_minutos} minutos")
    print(f"  Reavaliação: a cada {reavaliar_horas}h ({ciclos_para_reavaliar} ciclos)")
    print(f"  Pressione CTRL+C para parar")
    print("=" * 50)
    
    try:
        while running:
            ciclo_atual += 1
            
            if ciclo_atual % ciclos_para_reavaliar == 0:
                reavaliar_eventos_comprados()
            
            try:
                resultado = executar_ciclo()
                
                qtd_coletados = resultado.get("coletados", 0)
                intervalo_dinamico = calcular_intervalo(qtd_coletados)
                
                save_last_run({
                    "ultimo_ciclo": resultado,
                    "proximo_ciclo": datetime.now().isoformat(),
                    "intervalo_minutos": intervalo_dinamico
                })
                
                print(f"\n  Ultimo run: {resultado.get('timestamp', '')}")
                print(f"  Intervalo ajustado: {intervalo_dinamico}min (baseado em {qtd_coletados} eventos)")
                
                if running:
                    segundos = intervalo_dinamico * 60
                    print(f"  Proximo ciclo em {intervalo_dinamico}min...")
                    time.sleep(segundos)
                    
            except Exception as e:
                print(f"  [ERRO] Ciclo falhou: {e}")
                time.sleep(60)
                
    finally:
        release_lock()
        print("\n[Scheduler] Encerrado.")


def stop_scheduler():
    """Para o scheduler."""
    if os.path.exists(LOCK_FILE):
        try:
            os.remove(LOCK_FILE)
            print("Scheduler parado.")
        except Exception as e:
            print(f"Erro ao parar: {e}")
    else:
        print("Scheduler não está rodando.")


def reavaliar_eventos_comprados():
    """
    Reavalia planos de ação de eventos com COMPRAR.
    Deve ser chamado periodicamente (ex: a cada 6h).
    """
    from core.learning import carregar_historico
    from core.predictor import processar_previsoes
    
    print("\n[Reavaliação] Verificando eventos comprados...")
    
    historico = carregar_historico()
    eventos_comprar = [h for h in historico if h.get("acao_final") == "COMPRAR"]
    
    if not eventos_comprar:
        print("  Nenhum evento COMPRAR no histórico.")
        return
    
    print(f"  {len(eventos_comprar)} eventos COMPRAR para reavaliar")
    
    eventos_atualizados = reavaliar_planos(eventos_comprar)
    
    alterados = [e for e in eventos_atualizados 
                 if e.get("plano_acao", {}).get("alterou_estrategia")]
    
    if alterados:
        print(f"  {len(alterados)} alterações de estratégia detectadas")
        for e in alterados:
            evento_nome = e.get("evento", e.get("evento", {}))
            nova_estrategia = e.get("plano_acao", {}).get("estrategia_saida")
            print(f"    - {evento_nome.get('nome', 'N/A')}: {nova_estrategia}")
    else:
        print("  Nenhuma alteração necessária.")
    
    from core.learning import salvar_historico
    salvar_historico(eventos_atualizados)
