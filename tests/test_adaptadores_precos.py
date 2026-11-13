"""Adaptadores de preco por plataforma (zig markdown, SPA playwright, rotas)."""
import pytest

from core import adaptadores_precos as ap
from core.monitor_precos import verificar_url

# Fixture real: markdown devolvido por zig.tickets (Accept: text/markdown)
ZIG_MD = """# Elis a Dois - Com Dani Moreno e Cauê Nardi

- Quando: sábado, 12 de dezembro de 2026 às 18:00
- Onde: Casa Eluar, Curitiba, PR
- Endereço: Rua Exemplo, 123, Centro, Curitiba, PR
- Status: à venda
- Organizador: Casa Eluar
- Página: https://zig.tickets/eventos/elis-a-dois-com-dani-moreno-e-caue-nardi

## Sobre

Uma homenagem intimista à obra de Elis Regina.

## Ingressos

- Geral [Inteira] Único: R$ 100,00 + R$ 10,00 de taxa - setor Geral
- Geral [Meia Solidária] Único: R$ 50,00 + R$ 5,00 de taxa - setor Geral

Preços e disponibilidade mudam a todo momento - confirme na página do evento antes de decidir.
"""

ZIG_MD_ENCERRADO = ZIG_MD.replace("- Status: à venda", "- Status: à venda (vendas encerradas)")

ZIG_MD_SEM_ESTOQUE = ZIG_MD.replace(
    "- Geral [Inteira] Único: R$ 100,00 + R$ 10,00 de taxa - setor Geral\n"
    "- Geral [Meia Solidária] Único: R$ 50,00 + R$ 5,00 de taxa - setor Geral",
    "- Não há ingressos disponíveis neste momento",
)


def test_zig_markdown_extrai_menor_preco_sem_taxa():
    dados = ap._zig_markdown_dados(ZIG_MD)
    # menor preço-base (Meia Solidária R$ 50; a taxa R$ 5 entra fora)
    assert dados["preco"] == 50.0
    assert dados["esgotado"] is False
    assert dados["cancelado"] is False


def test_zig_markdown_vendas_encerradas_esgotado():
    dados = ap._zig_markdown_dados(ZIG_MD_ENCERRADO)
    assert dados["esgotado"] is True


def test_zig_markdown_secao_sem_ingressos_esgotado():
    dados = ap._zig_markdown_dados(ZIG_MD_SEM_ESTOQUE)
    assert dados["esgotado"] is True
    assert dados["preco"] is None


def test_zig_url_eventos_reescreve_link_antigo():
    assert ap._zig_url_eventos("https://zig.tickets/event/abc") == \
        "https://zig.tickets/eventos/abc"
    # URL já correta não é mexida
    assert ap._zig_url_eventos("https://zig.tickets/eventos/abc") == \
        "https://zig.tickets/eventos/abc"


def test_rota_dominios():
    assert ap._dominio("https://WWW.Zig.Tickets/eventos/x") == "zig.tickets"
    # domínios sem adaptador -> None (cai na camada estática do monitor)
    assert ap.verificar_evento("https://uhuu.com/evento/x") is None
    assert ap.verificar_evento("https://www.eventim.com.br/artist/x/") is None
    assert ap.verificar_evento("") is None


def test_rota_spa_vai_para_playwright(monkeypatch):
    capturado = {}

    def fake_pw(url, nome=None):
        capturado["url"] = url
        return {"preco": 210.0, "esgotado": False, "cancelado": False,
                "status": 200, "erro": None, "camada": "playwright"}

    for dom in ("q2ingressos.com.br", "ingresse.com", "blueticket.com.br"):
        monkeypatch.setattr(ap, "_playwright_verificar", fake_pw)
        res = ap.verificar_evento(f"https://{dom}/events/x", "Algum Show")
        assert res["camada"] == "playwright"
    assert capturado["url"] == "https://blueticket.com.br/events/x"


def test_monitor_verificar_url_intercepta_adaptador(monkeypatch):
    monkeypatch.setattr("core.adaptadores_precos.verificar_evento",
                        lambda url, nome=None: {"preco": 7.0, "camada": "zig-markdown"})
    res = verificar_url("https://zig.tickets/eventos/x", "Show X")
    assert res["preco"] == 7.0


def test_render_extrai_jsonld_preço_e_esgotado():
    html = """<html><head><script type="application/ld+json">
    {"@type":"Event","name":"Show Y","offers":{"@type":"Offer","price":"180,00",
    "availability":"https://schema.org/SoldOut"}}
    </script></head><body>Show Y</body></html>"""
    out = ap._extrair_de_render(html, "Show Y - ingressos esgotados", "Show Y")
    assert out["preco"] == 180.0
    assert out["esgotado"] is True


def test_render_preco_do_texto_visivel_fallback():
    html = "<html><body><div>LUAN REGISTRO</div></body></html>"
    texto = "Pista R$ 210,00\nCamarote R$ 420,00"
    out = ap._extrair_de_render(html, texto, "LUAN REGISTRO")
    assert out["preco"] == 210.0
    assert out["esgotado"] is False
