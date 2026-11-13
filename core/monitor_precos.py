"""
Monitor de preços — radar de compra (Fase 2).

Re-visita periodicamente as páginas dos eventos COMPRAR/MONITORAR futuros,
extrai preço atual e status de esgotamento, grava snapshots em
data/precos_historico.json e dispara alertas Telegram:
  - 📉 queda de preço >= MONITOR_QUEDA_PCT (default 5%)
  - 🚨 evento futuro esgotou (urgência)
  - ⛔ evento cancelado/postponed (JSON-LD eventStatus)

Extração em camadas, da mais confiável para a menos:
  1. JSON-LD estruturado (offers.price, availability SoldOut, eventStatus)
  2. itemprop="price" content="..."
  3. regex "R$ ..." — só valores que aparecem repetidos vencem (evita taxas)

Snapshots são deduplicados: cada evento é verificado no máximo a cada
INTERVALO_MINIMO_HORAS (20h), a menos que force=True.

Limitação conhecida: plataformas 100% SPA (zig.tickets, q2ingressos,
ingresse, blueticket, sympla) não expõem preço no HTML estático — ficam
como "sem sinal"/erro e geram snapshot marcador (dedupe), sem preço.
"""
import json
import os
import re
import threading
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import requests

from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, ALERTA_ENABLED
from utils.logger import logger

HIST_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "precos_historico.json")

MAX_SNAPSHOTS_POR_EVENTO = 400
MAX_PONTOS_PAYLOAD = 60
INTERVALO_MINIMO_HORAS = 20
QUEDA_PRECO_PCT = float(os.environ.get("MONITOR_QUEDA_PCT", "5"))
MONITOR_WORKERS = int(os.environ.get("MONITOR_WORKERS", "8"))
MONITOR_TIMEOUT = int(os.environ.get("MONITOR_TIMEOUT", "20"))
MIN_PRECO = 5.0
MAX_PRECO = 100000.0

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
}

# Frases fortes apenas — palavras soltas ("esgotado", "encerrado", "lotado")
# geram falso positivo ("tempo esgotado" em modal de checkout, badges
# "Encerrado" de sessões passadas em páginas de turnê, CSS .soldout).
PALAVRAS_ESGOTADO = [
    "ingresso esgotado", "ingressos esgotados", "estão esgotados",
    "está esgotado", "esta esgotado", "esgotou", "sold out",
    "out of stock", "vendas encerradas",
]

_RE_ITEMPROP = re.compile(r'itemprop="price"[^>]*content="([\d.,]+)"')
_RE_RS = re.compile(r'R\$\s*([\d.,]{3,12})')
_RE_JSONLD_BLOCK = re.compile(
    r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.S | re.I)

_file_lock = threading.Lock()
_status = {"rodando": False, "ultimo_summary": None, "ultima_rodada": None}


def _norm(txt: str) -> str:
    if not txt:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(txt))
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def _ev_de(item: dict) -> dict:
    ev = item.get("evento")
    return ev if isinstance(ev, dict) else item


def id_evento(item: dict) -> str:
    ev = _ev_de(item)
    return str(ev.get("event_id") or f"{ev.get('nome')}_{ev.get('data')}")


# ==================== ARQUIVO ====================

def carregar_precos() -> dict:
    if not os.path.exists(HIST_FILE):
        return {}
    try:
        with open(HIST_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, IOError):
        return {}


def salvar_precos(precos: dict) -> None:
    with _file_lock:
        os.makedirs(os.path.dirname(HIST_FILE), exist_ok=True)
        with open(HIST_FILE, "w", encoding="utf-8") as f:
            json.dump(precos, f, ensure_ascii=False)


def serie_precos(event_id: str, apenas_com_preco: bool = True, limite: int = None) -> list:
    """Série de snapshots [{t, p, esg}] de um evento."""
    precos = carregar_precos()
    serie = precos.get(str(event_id), [])
    if apenas_com_preco:
        serie = [s for s in serie if s.get("p") is not None]
    if limite:
        serie = serie[-limite:]
    return serie


# ==================== EXTRAÇÃO ====================

def _parse_br(valor: str):
    """'1.234,56' | '1234.56' | '1234,56' -> float"""
    v = (valor or "").strip()
    if not v:
        return None
    if "." in v and "," in v:
        v = v.replace(".", "").replace(",", ".")
    elif "," in v:
        v = v.replace(",", ".")
    else:
        # '1.234' com ponto simples pode ser milhar ou decimal
        if v.count(".") == 1 and len(v.split(".")[1]) == 3 and len(v.split(".")[0]) > 1:
            v = v.replace(".", "")
    try:
        return float(v)
    except ValueError:
        return None


def _jsonld_dados(texto: str) -> dict:
    """Percorre blocos JSON-LD: preços plausíveis, availability SoldOut,
    eventStatus cancelado/postponed."""
    precos, soldout, cancelado = [], False, False
    for m in _RE_JSONLD_BLOCK.finditer(texto):
        try:
            data = json.loads(m.group(1))
        except (json.JSONDecodeError, ValueError):
            continue
        fila = [data]
        while fila:
            node = fila.pop()
            if isinstance(node, list):
                fila.extend(node)
                continue
            if not isinstance(node, dict):
                continue
            tipo = str(node.get("@type") or "").lower()
            if "event" in tipo:
                st = str(node.get("eventStatus") or "").lower()
                if "cancelled" in st or "canceled" in st or "postponed" in st:
                    cancelado = True
            if "offer" in tipo:
                av = str(node.get("availability") or "").lower()
                if "soldout" in av.replace(" ", "") or "outofstock" in av:
                    soldout = True
                for chave in ("price", "lowPrice", "bestPrice"):
                    v = node.get(chave)
                    if v is not None:
                        p = _parse_br(str(v))
                        if p and MIN_PRECO <= p <= MAX_PRECO:
                            precos.append(p)
            fila.extend(v for v in node.values() if isinstance(v, (dict, list)))
    return {"precos": precos, "soldout": soldout, "cancelado": cancelado}


def _preco_regex(texto: str):
    """Fallback: menor 'R$ ...' plausível; se algum valor se repete
    (preço real aparece em vários lotes/menções), preferir os repetidos."""
    candidatos = []
    for match in _RE_RS.finditer(texto):
        p = _parse_br(match.group(1))
        if p and MIN_PRECO <= p <= MAX_PRECO:
            candidatos.append(round(p, 2))
    if not candidatos:
        return None
    repetidos = [p for p in candidatos if candidatos.count(p) > 1]
    return min(repetidos) if repetidos else min(candidatos)


def extrair_preco(texto: str):
    """Menor preço plausível da página (estruturado > itemprop > regex)."""
    estrut = _jsonld_dados(texto)
    if estrut["precos"]:
        return min(estrut["precos"])
    for match in _RE_ITEMPROP.finditer(texto):
        p = _parse_br(match.group(1))
        if p and MIN_PRECO <= p <= MAX_PRECO:
            return p
    return _preco_regex(texto)


def extrair_esgotado(texto: str, nome: str = None) -> bool:
    """Keyword match — só confia se o NOME do evento (>=4 letras) aparece na
    página: evita falso positivo do catálogo i18n de SPA shells e de páginas
    sem identificação. Nomes curtos (<4 letras, ex.: 'SEX', 'DOM') desativam
    o keyword path: 'sex' bate em qualquer palavra."""
    n = _norm(nome or "")
    if len(n) < 4 or n not in _norm(texto):
        return False
    t = _norm(texto)
    return any(_norm(palavra) in t for palavra in PALAVRAS_ESGOTADO)


def verificar_url(url: str, nome: str = None) -> dict:
    """Baixa a página e extrai {preco, esgotado, cancelado, status, erro}."""
    resultado = {"preco": None, "esgotado": False, "cancelado": False,
                 "status": None, "erro": None}
    try:
        resp = requests.get(url, headers=HEADERS, timeout=MONITOR_TIMEOUT)
        resultado["status"] = resp.status_code
        if resp.status_code != 200:
            resultado["erro"] = f"HTTP {resp.status_code}"
            return resultado
        texto = resp.text
        estrut = _jsonld_dados(texto)
        if estrut["precos"]:
            resultado["preco"] = min(estrut["precos"])
        if resultado["preco"] is None:
            for match in _RE_ITEMPROP.finditer(texto):
                p = _parse_br(match.group(1))
                if p and MIN_PRECO <= p <= MAX_PRECO:
                    resultado["preco"] = p
                    break
        if resultado["preco"] is None:
            resultado["preco"] = _preco_regex(texto)
        resultado["esgotado"] = bool(estrut["soldout"]) or extrair_esgotado(texto, nome)
        resultado["cancelado"] = estrut["cancelado"]
    except requests.exceptions.RequestException as e:
        resultado["erro"] = str(e)[:120]
    except Exception as e:
        resultado["erro"] = str(e)[:120]
    return resultado


# ==================== TELEGRAM ====================

def _enviar_telegram(texto: str) -> bool:
    if not ALERTA_ENABLED or not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        resp = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": texto,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }, timeout=15)
        return resp.status_code == 200
    except Exception as e:
        logger.warning(f"Telegram falhou no monitor: {e}")
        return False


# ==================== MONITOR ====================

def _eventos_alvo(ranking: list, so_futuros: bool = True) -> list:
    hoje = datetime.now().date()
    alvo = []
    for item in ranking:
        acao = item.get("acao_final") or ""
        if acao not in ("COMPRAR", "MONITORAR"):
            continue
        ev = _ev_de(item)
        url = ev.get("url") or ""
        if not url:
            continue
        data_str = str(ev.get("data") or "")[:10]
        if so_futuros:
            try:
                if datetime.fromisoformat(data_str).date() < hoje:
                    continue
            except ValueError:
                continue
        alvo.append(item)
    return alvo


def _ultimo_snapshot(precos: dict, ev_id: str):
    serie = precos.get(ev_id, [])
    return serie[-1] if serie else None


def rodar_monitor(force: bool = False) -> dict:
    """Executa uma rodada de verificação. Deduplica por INTERVALO_MINIMO_HORAS."""
    if _status["rodando"]:
        return {"status": "ja_rodando", "summary": _status["ultimo_summary"]}
    _status["rodando"] = True

    summary = {
        "status": "ok",
        "alvo": 0, "verificados": 0, "com_sinal": 0, "sem_sinal": 0,
        "erros": 0, "esgotados": 0, "quedas": 0, "cancelados": 0, "alertas": 0,
        "skipped_recente": 0,
        "iniciado": datetime.now().isoformat(),
    }

    try:
        ranking_path = os.path.join(os.path.dirname(__file__), "..", "data", "ranking.json")
        with open(ranking_path, "r", encoding="utf-8") as f:
            ranking = json.load(f)

        alvo = _eventos_alvo(ranking)
        summary["alvo"] = len(alvo)

        precos = carregar_precos()
        agora = datetime.now()

        pendentes = []
        for item in alvo:
            ev_id = id_evento(item)
            ultimo = _ultimo_snapshot(precos, ev_id)
            if not force and ultimo:
                try:
                    dt = datetime.fromisoformat(ultimo.get("t", ""))
                    if (agora - dt).total_seconds() < INTERVALO_MINIMO_HORAS * 3600:
                        summary["skipped_recente"] += 1
                        continue
                except (ValueError, TypeError):
                    pass
            ev = _ev_de(item)
            pendentes.append((item, ev_id, ev.get("nome") or "", ev.get("url"), ev.get("data") or ""))

        logger.info(f"[MONITOR] {len(pendentes)}/{len(alvo)} eventos a verificar ({summary['skipped_recente']} recentes demais)")

        resultados = {}
        if pendentes:
            with ThreadPoolExecutor(max_workers=MONITOR_WORKERS) as pool:
                futures = {pool.submit(verificar_url, url, nome): (ev_id, nome, url, data_ev)
                           for (item, ev_id, nome, url, data_ev) in pendentes}
                for future in as_completed(futures):
                    ev_id, nome, url, data_ev = futures[future]
                    try:
                        resultados[ev_id] = (future.result(), nome, url, data_ev)
                    except Exception:
                        resultados[ev_id] = ({"preco": None, "esgotado": False, "cancelado": False,
                                              "status": None, "erro": "excecao"},
                                             nome, url, data_ev)

        quedas, esgotados, cancelados, alertas = [], [], [], 0
        for (item, ev_id, nome, url, data_ev) in pendentes:
            res = resultados.get(ev_id)
            if not res:
                continue
            res, nome, url, data_ev = res
            summary["verificados"] += 1

            tem_sinal = res.get("preco") is not None or res.get("esgotado") or res.get("cancelado")
            if not tem_sinal:
                if res.get("erro"):
                    summary["erros"] += 1
                else:
                    summary["sem_sinal"] += 1

            anterior = _ultimo_snapshot(precos, ev_id)
            snapshot = {
                "t": agora.isoformat(),
                "p": res.get("preco"),
                "esg": bool(res.get("esgotado")),
                "c": bool(res.get("cancelado")),
                "st": res.get("status"),
            }
            precos.setdefault(ev_id, []).append(snapshot)
            if len(precos[ev_id]) > MAX_SNAPSHOTS_POR_EVENTO:
                precos[ev_id] = precos[ev_id][-MAX_SNAPSHOTS_POR_EVENTO:]

            if tem_sinal:
                summary["com_sinal"] += 1

            # 📉 queda de preço
            if (res.get("preco") is not None and anterior and anterior.get("p") is not None
                    and not snapshot["esg"]):
                p_antes = float(anterior["p"])
                p_agora = float(res["preco"])
                if p_antes > 0 and p_agora < p_antes * (1 - QUEDA_PRECO_PCT / 100):
                    pct = (1 - p_agora / p_antes) * 100
                    quedas.append({"nome": nome, "antes": p_antes, "agora": p_agora,
                                   "pct": round(pct, 1), "url": url, "data": data_ev})

            # 🚨 esgotou
            if snapshot["esg"] and not (anterior and anterior.get("esg")):
                esgotados.append({"nome": nome, "url": url, "data": data_ev})

            # ⛔ cancelado/postponed
            if snapshot["c"] and not (anterior and anterior.get("c")):
                cancelados.append({"nome": nome, "url": url, "data": data_ev})

        if pendentes:
            precos["_meta"] = {
                "ultima_rodada": agora.isoformat(),
                "verificados": summary["verificados"],
                "alvo": len(alvo),
            }
            salvar_precos(precos)

        # alertas
        for q in quedas:
            texto = (f"📉 <b>QUEDA DE PREÇO</b>\n\n"
                     f"🎫 {q['nome'][:70]}\n"
                     f"💰 R$ {q['antes']:.2f} → R$ {q['agora']:.2f} (-{q['pct']}%)\n"
                     f"📅 {q['data'][:10]}\n\n"
                     f"{q['url']}")
            if _enviar_telegram(texto):
                alertas += 1
            logger.info(f"[MONITOR] Queda: {q['nome'][:40]} {q['antes']}->{q['agora']}")
        for e in esgotados:
            texto = (f"🚨 <b>ESGOTOU!</b>\n\n"
                     f"🎫 {e['nome'][:70]}\n"
                     f"📅 {e['data'][:10]}\n\n"
                     f"O ingresso está esgotado — hora de revisar a estratégia de revenda.\n"
                     f"{e['url']}")
            if _enviar_telegram(texto):
                alertas += 1
            logger.info(f"[MONITOR] Esgotou: {e['nome'][:40]}")
        for c in cancelados:
            texto = (f"⛔ <b>EVENTO CANCELADO/POSTERGADO</b>\n\n"
                     f"🎫 {c['nome'][:70]}\n"
                     f"📅 {c['data'][:10]}\n\n"
                     f"Revisar posição — venda pode ser afetada.\n"
                     f"{c['url']}")
            if _enviar_telegram(texto):
                alertas += 1
            logger.info(f"[MONITOR] Cancelado: {c['nome'][:40]}")

        summary["quedas"] = len(quedas)
        summary["esgotados"] = len(esgotados)
        summary["cancelados"] = len(cancelados)
        summary["alertas"] = alertas
        summary["concluido"] = datetime.now().isoformat()

        # Feedback automático pós-evento (julga passados sem operação)
        try:
            from core.feedback import rodar_feedback
            summary["feedback"] = rodar_feedback()
        except Exception as e:
            logger.warning(f"[FEEDBACK] Falhou: {e}")

        _status["ultimo_summary"] = summary
        _status["ultima_rodada"] = agora.isoformat()
        logger.info(f"[MONITOR] Rodada concluída: {summary}")
        return summary

    except Exception as e:
        summary["status"] = "erro"
        summary["erro"] = str(e)[:200]
        _status["ultimo_summary"] = summary
        logger.error(f"[MONITOR] Falhou: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return summary
    finally:
        _status["rodando"] = False


def rodar_monitor_background(force: bool = False):
    """Dispara o monitor em thread daemon (não bloqueia chamador)."""
    th = threading.Thread(target=rodar_monitor, args=(force,), daemon=True)
    th.start()
    return th


def resumo_monitor() -> dict:
    """Resumo para o dashboard."""
    precos = carregar_precos()
    com_serie = {k: v for k, v in precos.items() if k != "_meta" and v}
    total_snapshots = sum(len(v) for v in com_serie.values())
    return {
        "eventos_com_historico": len(com_serie),
        "total_snapshots": total_snapshots,
        "ultima_rodada": (com_serie and max(
            (s.get("t", "") for serie in com_serie.values() for s in serie), default="")),
        "meta": precos.get("_meta", {}),
        "rodando": _status["rodando"],
        "ultimo_summary": _status["ultimo_summary"],
        "queda_pct_config": QUEDA_PRECO_PCT,
    }
