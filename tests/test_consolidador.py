# -*- coding: utf-8 -*-
"""Testes do consolidador de duplicatas (Fase 1)."""
from core.consolidador import (
    normalizar_texto, chave_grupo, anotar_grupos, consolidar
)


def _ev(nome, data="2026-12-01", cidade="", fonte="a", event_id=None, acao=None, nota=None):
    return {
        "evento": {
            "nome": nome, "data": data, "cidade": cidade, "fonte": fonte,
            "event_id": event_id or f"{nome}_{data}", "url": f"https://x/{fonte}/{nome}",
            "preco": 100.0,
        },
        "acao_final": acao or "",
        "analise": {"nota_final": nota or 0},
    }


class TestNormalizarTexto:
    def test_sem_acentos_e_maiusculo(self):
        assert normalizar_texto("Festival Verão") == "FESTIVAL VERAO"

    def test_remove_data_padrao_mes(self):
        assert "20" not in normalizar_texto("ALDEIA 20.NOV") or \
            normalizar_texto("ALDEIA 20.NOV") == "ALDEIA"

    def test_remove_data_num(self):
        assert normalizar_texto("SHOW 13/11") == "SHOW"

    def test_pontuacao_vira_espaco(self):
        assert normalizar_texto("A&B - Show!") == "A B SHOW"

    def test_brackets_removidos(self):
        assert normalizar_texto("FESTA [DATA EXTRA]") == "FESTA"

    def test_vazio(self):
        assert normalizar_texto("") == ""
        assert normalizar_texto(None) == ""


class TestChaveGrupo:
    def test_mesmo_evento_fontes_diferentes(self):
        a = _ev("SUPER MAQUINAS", cidade="Fortaleza", data="2026-12-05", fonte="zigtickets")
        b = _ev("SUPER MÁQUINAS", cidade="Fortaleza", data="2026-12-05", fonte="q2ingressos")
        assert chave_grupo(a) == chave_grupo(b)

    def test_series_datas_diferentes_nao_agrupam(self):
        a = _ev("ALDEIA SABADO", data="2026-11-14")
        b = _ev("ALDEIA SABADO", data="2026-11-21")
        assert chave_grupo(a) != chave_grupo(b)

    def test_cidade_no_fim_do_nome_removida(self):
        a = _ev("SHOW - RIO DE JANEIRO", cidade="Rio de Janeiro", data="2026-12-01")
        b = _ev("SHOW", cidade="Rio de Janeiro", data="2026-12-01")
        assert chave_grupo(a) == chave_grupo(b)


class TestAnotarGrupos:
    def test_grupo_com_n_fontes(self):
        itens = [
            _ev("FESTA", fonte="a", acao="MONITORAR", nota=6.0),
            _ev("FESTA", fonte="b", acao="COMPRAR", nota=6.0),
            _ev("OUTRO", fonte="a", acao="IGNORAR", nota=3.0),
        ]
        anotar_grupos(itens)
        assert itens[0]["grupo_count"] == 2
        assert itens[1]["grupo_count"] == 2
        assert itens[2]["grupo_count"] == 1
        # representante é o COMPRAR (prioridade maior)
        assert itens[1]["grupo_repr"] is True
        assert itens[0]["grupo_repr"] is False
        assert len(itens[0]["grupo_membros"]) == 2

    def test_representante_por_nota(self):
        itens = [
            _ev("FESTA", fonte="a", acao="MONITORAR", nota=5.0),
            _ev("FESTA", fonte="b", acao="MONITORAR", nota=9.0),
        ]
        anotar_grupos(itens)
        assert itens[1]["grupo_repr"] is True

    def test_consolidar_dedupe(self):
        itens = [
            _ev("FESTA", fonte="a"), _ev("FESTA", fonte="b"),
            _ev("FESTA", fonte="c", data="2026-12-02"),
        ]
        grupos = consolidar(itens)
        assert len(grupos) == 2  # 2 datas distintas


def test_zero_duplicatas_em_series_reais():
    """Cenário real: repetições de nome com datas diferentes = eventos distintos."""
    itens = [_ev("ALDEIA SABADO", data=f"2026-11-{d:02d}") for d in (14, 15, 21, 22)]
    grupos = consolidar(itens)
    assert len(grupos) == 4
