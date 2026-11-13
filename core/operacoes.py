"""
Kanban de operações (Fase 3).

Ciclo do ingresso: comprar -> comprado -> revendendo -> vendido | perdido.
Estado em data/operacoes.json. Ao finalizar (vendido/perdido), alimenta o
motor de aprendizado via learning.registrar_operacao() — fechando o loop
nota -> decisão -> resultado real -> thresholds.
"""
import json
import os
import threading
import uuid
from datetime import datetime
from typing import Optional

from utils.logger import logger

OPS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "operacoes.json")

ETAPAS = ["comprar", "comprado", "revendendo", "vendido", "perdido"]

_file_lock = threading.Lock()


def carregar() -> list:
    if not os.path.exists(OPS_FILE):
        return []
    try:
        with open(OPS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("ops", []) if isinstance(data, dict) else []
    except (json.JSONDecodeError, IOError):
        return []


def salvar(ops: list) -> None:
    with _file_lock:
        os.makedirs(os.path.dirname(OPS_FILE), exist_ok=True)
        with open(OPS_FILE, "w", encoding="utf-8") as f:
            json.dump({"ops": ops}, f, ensure_ascii=False)


def get_op(op_id: str) -> Optional[dict]:
    for op in carregar():
        if op.get("op_id") == op_id:
            return op
    return None


def _ev_de(item: dict) -> dict:
    ev = item.get("evento")
    return ev if isinstance(ev, dict) else item


def criar_op(evento: dict, qtd: int = 1, preco_compra: float = None, notas: str = "") -> dict:
    """Cria operação a partir de um evento achatado do dashboard.

    Aceita também o item cru do ranking (com 'evento' aninhado).
    """
    ev = _ev_de(evento)
    op = {
        "op_id": f"op_{uuid.uuid4().hex[:10]}",
        "event_id": str(ev.get("id") or ev.get("event_id") or f"{ev.get('nome')}_{ev.get('data')}"),
        "nome": ev.get("nome") or "",
        "artista": ev.get("artista") or "",
        "data": str(ev.get("data") or "")[:10],
        "cidade": ev.get("cidade") or "",
        "estado": ev.get("estado") or "",
        "fonte": ev.get("fonte") or "",
        "url": ev.get("url") or "",
        "imagem": ev.get("imagem") or "",
        "nota": ev.get("nota"),
        "acao": ev.get("acao") or ev.get("acao_final") or "",
        "genero": ev.get("genero") or "",
        "compra_agressiva": bool(ev.get("compra_agressiva")),
        "etapa": "comprar",
        "qtd": max(1, int(qtd or 1)),
        "preco_compra": round(float(preco_compra), 2) if preco_compra is not None else (
            round(float(ev.get("preco")), 2) if ev.get("preco") is not None else None),
        "preco_venda": None,
        "taxa": 0.0,
        "notas": notas or "",
        "criada_em": datetime.now().isoformat(),
        "comprada_em": None,
        "vendida_em": None,
        "feed_learning": False,
    }
    ops = carregar()
    ops.append(op)
    salvar(ops)
    logger.info(f"[OP] Criada {op['op_id']}: {op['nome'][:40]} qtd={op['qtd']} pc={op['preco_compra']}")
    return op


def mover(op_id: str, etapa: str, preco_venda=None, taxa=None, qtd=None,
          notas=None) -> Optional[dict]:
    """Move operação de etapa e atualiza campos de venda.

    Entrar em 'vendido' exige preco_venda > 0. 'perdido' aceita preço
    recuperado (0 = perda total). Na primeira finalização, alimenta o
    learning (flag feed_learning evita duplicação se voltar e refinar).
    """
    etapa = (etapa or "").strip().lower()
    if etapa not in ETAPAS:
        return None

    ops = carregar()
    op = next((o for o in ops if o.get("op_id") == op_id), None)
    if not op:
        return None

    if qtd is not None:
        try:
            op["qtd"] = max(1, int(qtd))
        except (TypeError, ValueError):
            pass
    if notas is not None:
        op["notas"] = str(notas)[:500]
    if taxa is not None:
        try:
            op["taxa"] = max(0.0, round(float(taxa), 2))
        except (TypeError, ValueError):
            pass
    if preco_venda is not None:
        try:
            op["preco_venda"] = max(0.0, round(float(preco_venda), 2))
        except (TypeError, ValueError):
            pass

    if etapa == "comprado" and not op.get("comprada_em"):
        op["comprada_em"] = datetime.now().isoformat()
        if op.get("preco_compra") is None:
            # sem preço de compra conhecido — zera para forçar preenchimento
            op["preco_compra"] = 0.0
    if etapa in ("vendido", "perdido"):
        if etapa == "vendido" and not (op.get("preco_venda") or 0) > 0:
            return None  # vendido exige preço de venda
        if not op.get("vendida_em"):
            op["vendida_em"] = datetime.now().isoformat()
    if etapa in ("comprar", "comprado", "revendendo"):
        op["vendida_em"] = None

    op["etapa"] = etapa

    finalizada = etapa in ("vendido", "perdido")
    if finalizada and not op.get("feed_learning"):
        _alimentar_aprendizado(op)
        op["feed_learning"] = True

    salvar(ops)
    logger.info(f"[OP] {op_id} -> {etapa}")
    return op


def remover(op_id: str) -> bool:
    ops = carregar()
    novas = [o for o in ops if o.get("op_id") != op_id]
    if len(novas) == len(ops):
        return False
    salvar(novas)
    return True


def pnl(op: dict) -> Optional[float]:
    """P&L realizado da operação (total, não unitário). None se não finalizada."""
    if op.get("etapa") not in ("vendido", "perdido"):
        return None
    pc = op.get("preco_compra")
    if pc is None:
        return None
    pv = op.get("preco_venda") or 0.0
    return round((pv - float(pc)) * op.get("qtd", 1) - float(op.get("taxa") or 0), 2)


def _alimentar_aprendizado(op: dict) -> None:
    """Fecha o loop: registra a operação no motor de aprendizado."""
    try:
        from core.learning import registrar_operacao
        nome = op.get("nome") or ""
        data_ev = op.get("data") or ""
        artista = op.get("artista") or ""
        pc = float(op.get("preco_compra") or 0)
        pv = float(op.get("preco_venda") or 0)
        data_compra = (op.get("comprada_em") or op.get("criada_em") or "")[:10] or datetime.now().strftime("%Y-%m-%d")
        data_venda = (op.get("vendida_em") or datetime.now().isoformat())[:10]
        estrategia = "agressiva" if op.get("compra_agressiva") else "padrao"
        nota = float(op.get("nota") or 0)
        registrar_operacao(
            nome_evento=nome,
            data_evento=data_ev,
            artista=artista,
            preco_compra=pc,
            preco_venda=pv,
            data_compra=data_compra,
            data_venda=data_venda,
            fonte_compra=op.get("fonte") or "",
            fonte_venda="",
            nota_decisao=nota,
            estrategia=estrategia,
        )
        logger.info(f"[OP] Learning alimentado: {nome[:40]} lucro={(pv - pc) * op.get('qtd', 1):.2f}")
    except Exception as e:
        logger.warning(f"[OP] Falha ao alimentar learning: {e}")


def resumo() -> dict:
    """Resumo financeiro do Kanban."""
    ops = carregar()
    por_etapa = {e: 0 for e in ETAPAS}
    capital = 0.0
    pnl_total = 0.0
    finalizadas = 0
    acertos = 0
    for op in ops:
        etapa = op.get("etapa") or "comprar"
        por_etapa[etapa] = por_etapa.get(etapa, 0) + 1
        pc = op.get("preco_compra")
        if etapa in ("comprado", "revendendo") and pc is not None:
            capital += float(pc) * op.get("qtd", 1)
        p = pnl(op)
        if p is not None:
            finalizadas += 1
            pnl_total += p
            if p > 0:
                acertos += 1
    return {
        "total": len(ops),
        "por_etapa": por_etapa,
        "capital_investido": round(capital, 2),
        "pnl_realizado": round(pnl_total, 2),
        "finalizadas": finalizadas,
        "taxa_acerto": round(acertos / finalizadas * 100, 1) if finalizadas else None,
    }
