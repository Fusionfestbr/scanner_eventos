# -*- coding: utf-8 -*-
"""Testes do Kanban de operações (Fase 3), com arquivos isolados em tmp."""
import json

import pytest

from core import operacoes, learning


@pytest.fixture
def ops_isolado(tmp_path, monkeypatch):
    monkeypatch.setattr(operacoes, "OPS_FILE", str(tmp_path / "operacoes.json"))
    monkeypatch.setattr(learning, "RESULTADOS_FILE", str(tmp_path / "resultados.json"))
    return operacoes


def _ev(**kw):
    base = {"id": "EV1", "nome": "Show Teste", "data": "2026-12-25", "cidade": "SP",
            "estado": "SP", "fonte": "teste", "url": "https://x/e", "nota": 8.0,
            "acao": "COMPRAR", "preco": 100.0, "artista": "Artista"}
    base.update(kw)
    return base


class TestCiclo:
    def test_criar_comprar_finalizar(self, ops_isolado):
        op = ops_isolado.criar_op(_ev(), qtd=2)
        assert op["etapa"] == "comprar"
        assert op["preco_compra"] == 100.0
        assert op["qtd"] == 2

        assert ops_isolado.mover(op["op_id"], "etapa-invalida") is None
        assert ops_isolado.mover(op["op_id"], "comprado")["etapa"] == "comprado"
        assert ops_isolado.mover(op["op_id"], "revendendo")["etapa"] == "revendendo"

        # vendido sem preço é bloqueado
        assert ops_isolado.mover(op["op_id"], "vendido") is None
        r = ops_isolado.mover(op["op_id"], "vendido", preco_venda=150.0, taxa=5.0)
        assert r["etapa"] == "vendido"
        # (150-100)*2 - 5
        assert ops_isolado.pnl(r) == 95.0

    def test_perdido_aceita_zero(self, ops_isolado):
        op = ops_isolado.criar_op(_ev(), qtd=1)
        ops_isolado.mover(op["op_id"], "comprado")
        r = ops_isolado.mover(op["op_id"], "perdido", preco_venda=0)
        assert ops_isolado.pnl(r) == -100.0

    def test_learning_alimentado_uma_vez(self, ops_isolado):
        op = ops_isolado.criar_op(_ev(), qtd=1)
        ops_isolado.mover(op["op_id"], "comprado")
        ops_isolado.mover(op["op_id"], "vendido", preco_venda=120.0)
        # reabre e re-finaliza — não duplica no learning
        ops_isolado.mover(op["op_id"], "revendendo")
        ops_isolado.mover(op["op_id"], "vendido", preco_venda=130.0)
        resultados = learning.carregar_resultados()
        registros = [r for r in resultados if r.get("nome_evento") == "Show Teste"]
        assert len(registros) == 1
        assert registros[0]["lucro"] == 20.0
        assert registros[0]["resultado"] == "sucesso"

    def test_remover(self, ops_isolado):
        op = ops_isolado.criar_op(_ev())
        assert ops_isolado.remover(op["op_id"]) is True
        assert ops_isolado.remover(op["op_id"]) is False
        assert ops_isolado.carregar() == []


class TestResumo:
    def test_resumo_completo(self, ops_isolado):
        o1 = ops_isolado.criar_op(_ev(id="A"), qtd=1)          # 100
        o2 = ops_isolado.criar_op(_ev(id="B"), qtd=1)          # 100
        ops_isolado.mover(o1["op_id"], "comprado")
        ops_isolado.mover(o1["op_id"], "vendido", preco_venda=180.0)
        ops_isolado.mover(o2["op_id"], "comprado")              # em carteira
        ops_isolado.mover(o2["op_id"], "revendendo")
        r = ops_isolado.resumo()
        assert r["total"] == 2
        assert r["por_etapa"]["vendido"] == 1
        assert r["por_etapa"]["revendendo"] == 1
        assert r["capital_investido"] == 100.0
        assert r["pnl_realizado"] == 80.0
        assert r["taxa_acerto"] == 100.0

    def test_resumo_vazio(self, ops_isolado):
        r = ops_isolado.resumo()
        assert r["total"] == 0
        assert r["taxa_acerto"] is None

    def test_arquivo_persiste(self, ops_isolado, tmp_path):
        op = ops_isolado.criar_op(_ev())
        arquivo = tmp_path / "operacoes.json"
        data = json.loads(arquivo.read_text(encoding="utf-8"))
        assert data["ops"][0]["op_id"] == op["op_id"]
