"""
Feedback automático pós-evento (Fase 3).

Para eventos COMPRAR/MONITORAR cuja data já passou, que NÃO têm operação
no Kanban nem resultado_real no histórico, julga usando os snapshots do
radar de preços:

  - última checagem esgotada/cancelada          -> "valorizou"  (escassez)
  - preço subiu desde a 1ª leitura              -> "valorizou"
  - preço caiu ou ficou igual (>= 2 leituras)   -> "nao_valorizou"
  - sem snapshots suficientes                   -> sem julgamento

Julgamentos ficam em data/feedback_log.json (idempotência). Roda acoplado
ao fim de cada rodada do monitor.
"""
import json
import os
import threading
from datetime import datetime

from utils.logger import logger
from core.learning import carregar_historico, registrar_resultado

FEEDBACK_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "feedback_log.json")
ALTA_PCT = float(os.environ.get("FEEDBACK_ALTA_PCT", "3"))

_file_lock = threading.Lock()


def _ev_de(item: dict) -> dict:
    ev = item.get("evento")
    return ev if isinstance(ev, dict) else item


def carregar_log() -> dict:
    if not os.path.exists(FEEDBACK_FILE):
        return {}
    try:
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, IOError):
        return {}


def salvar_log(log: dict) -> None:
    with _file_lock:
        os.makedirs(os.path.dirname(FEEDBACK_FILE), exist_ok=True)
        with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False)


def _julgar(serie: list) -> str:
    """'valorizou' | 'nao_valorizou' | '' (sem sinal suficiente)."""
    if not serie:
        return ""
    ultimo = serie[-1]
    if ultimo.get("esg") or ultimo.get("c"):
        return "valorizou"
    com_preco = [s for s in serie if s.get("p") is not None]
    if len(com_preco) < 2:
        return ""
    p0, p1 = float(com_preco[0]["p"]), float(com_preco[-1]["p"])
    if not p0:
        return ""
    if p1 > p0 * (1 + ALTA_PCT / 100):
        return "valorizou"
    return "nao_valorizou"


def rodar_feedback() -> dict:
    """Roda o julgamento automático. Retorna summary."""
    summary = {"passados": 0, "julgados": 0, "valorizou": 0, "nao_valorizou": 0,
               "sem_sinal": 0, "com_operacao": 0, "ja_julgados": 0}
    try:
        ranking_path = os.path.join(os.path.dirname(__file__), "..", "data", "ranking.json")
        if not os.path.exists(ranking_path):
            return summary
        with open(ranking_path, "r", encoding="utf-8") as f:
            ranking = json.load(f)

        hoje = datetime.now().date()
        historico = carregar_historico()
        julgados_hist = {(h.get("evento"), str(h.get("data"))[:10])
                         for h in historico if h.get("resultado_real")}

        try:
            from core.operacoes import carregar as carregar_ops
            ops = {(o.get("nome"), o.get("data")) for o in carregar_ops()}
        except Exception:
            ops = set()

        log = carregar_log()
        agora = datetime.now().isoformat()

        try:
            from core.monitor_precos import serie_precos, carregar_precos
            precos_map = carregar_precos()
        except Exception:
            return summary

        for item in ranking:
            if item.get("acao_final") not in ("COMPRAR", "MONITORAR"):
                continue
            ev = _ev_de(item)
            nome = ev.get("nome") or ""
            data_ev = str(ev.get("data") or "")[:10]
            if not nome or not data_ev:
                continue
            try:
                data_dt = datetime.fromisoformat(data_ev).date()
            except ValueError:
                continue
            if data_dt >= hoje:
                continue  # só eventos passados

            summary["passados"] += 1
            ev_id = str(ev.get("event_id") or f"{nome}_{data_ev}")

            if (nome, data_ev) in ops:
                summary["com_operacao"] += 1
                continue
            if (nome, data_ev) in julgados_hist:
                summary["ja_julgados"] += 1
                continue
            if ev_id in log:
                summary["ja_julgados"] += 1
                continue

            serie = precos_map.get(ev_id) or []
            resultado = _julgar(serie)
            if not resultado:
                summary["sem_sinal"] += 1
                log[ev_id] = {"resultado": "sem_sinal", "t": agora}
                continue

            ok = registrar_resultado(nome, data_ev, resultado)
            log[ev_id] = {"resultado": resultado, "t": agora,
                          "registrado": bool(ok)}
            summary["julgados"] += 1
            summary[resultado] += 1
            logger.info(f"[FEEDBACK] {nome[:40]} ({data_ev}) -> {resultado} (registrado={ok})")

        salvar_log(log)
    except Exception as e:
        logger.error(f"[FEEDBACK] Falhou: {e}")
    return summary
