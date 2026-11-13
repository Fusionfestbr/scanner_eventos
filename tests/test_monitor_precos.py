# -*- coding: utf-8 -*-
"""Testes das heurísticas do radar de preços (Fase 2) e do feedback (Fase 3)."""
from core.monitor_precos import (
    _parse_br, _jsonld_dados, _preco_regex, extrair_preco, extrair_esgotado
)
from core.feedback import _julgar

KW = "ingressos esgotados"


class TestParseBr:
    def test_milhar_virgula(self):
        assert _parse_br("1.234,56") == 1234.56

    def test_virgula_decimal(self):
        assert _parse_br("89,90") == 89.9

    def test_ponto_decimal(self):
        assert _parse_br("350.00") == 350.0

    def test_vazio(self):
        assert _parse_br("") is None
        assert _parse_br(None) is None


class TestJsonLd:
    def test_price_em_offer(self):
        html = '<script type="application/ld+json">{"@type":"Offer","price":"90.00","priceCurrency":"BRL"}</script>'
        d = _jsonld_dados(html)
        assert d["precos"] == [90.0]
        assert extrair_preco(html) == 90.0

    def test_availability_soldout(self):
        html = ('<script type="application/ld+json">{"@type":"Offer","price":"50.00",'
                '"availability":"https://schema.org/SoldOut"}</script>')
        d = _jsonld_dados(html)
        assert d["soldout"] is True

    def test_event_status_cancelled(self):
        html = ('<script type="application/ld+json">{"@type":"Event","eventStatus":'
                '"https://schema.org/EventCancelled"}</script>')
        assert _jsonld_dados(html)["cancelado"] is True

    def test_price_zero_filtrado(self):
        html = '<script type="application/ld+json">{"@type":"Offer","price":"0.00"}</script>'
        assert _jsonld_dados(html)["precos"] == []

    def test_json_invalido_ignorado(self):
        assert _jsonld_dados('<script type="application/ld+json">{erro</script>') == {
            "precos": [], "soldout": False, "cancelado": False}


class TestPrecoRegex:
    def test_repetido_vence_taxa(self):
        assert _preco_regex("Taxa R$ 10,00 | Ingresso R$ 120,00 | Ingresso R$ 120,00") == 120.0

    def test_menor_quando_unicos(self):
        assert _preco_regex("Lote 1 R$ 200,00 | Lote 2 R$ 250,00") == 200.0

    def test_sem_preco(self):
        assert _preco_regex("sem preços aqui") is None

    def test_filtrado_min(self):
        assert _preco_regex("Taxa de serviço R$ 2,00") is None


class TestExtrairPreco:
    def test_itemprop(self):
        assert extrair_preco('<span itemprop="price" content="350.00"></span>') == 350.0

    def test_estruturado_antes_de_regex(self):
        html = ('<script type="application/ld+json">{"@type":"Offer","price":"80.00"}</script>'
                '<div>R$ 999,99</div>')
        assert extrair_preco(html) == 80.0


class TestEsgotado:
    def test_forte_com_nome(self):
        assert extrair_esgotado(f"{KW} agora", nome="Festival X") is False  # nome ausente
        assert extrair_esgotado(f"Festival X {KW}", nome="Festival X") is True

    def test_nome_curto_desativa(self):
        # "SEX" tem 3 letras — não deve ativar keyword path
        assert extrair_esgotado("SEX ingresso esgotado", nome="SEX") is False

    def test_sem_nome_nao_confia(self):
        assert extrair_esgotado(KW) is False

    def test_nao_bate_texto_neutro(self):
        assert extrair_esgotado("compre seu ingresso com desconto", nome="Show Z") is False


class TestFeedbackJulgar:
    def test_esgotou_valorizou(self):
        assert _julgar([{"p": 100.0, "esg": False}, {"p": None, "esg": True}]) == "valorizou"

    def test_cancelado_valorizou(self):
        assert _julgar([{"p": 90.0, "c": True}]) == "valorizou"

    def test_preco_subiu(self):
        assert _julgar([{"p": 100.0}, {"p": 130.0}]) == "valorizou"

    def test_preco_caiu(self):
        assert _julgar([{"p": 100.0}, {"p": 80.0}]) == "nao_valorizou"

    def test_um_ponto_sem_julgamento(self):
        assert _julgar([{"p": 100.0}]) == ""

    def test_sem_serie(self):
        assert _julgar([]) == ""
