"""Estatísticas de IA no enriquecimento: pedidas vs concluídas.

O dashboard usa essas estatísticas para avisar quando a coleta rodou
sem IA (LM Studio desligado) — pedidas > 0 com ok == 0.
"""
import json

from core import enricher
from core.enricher import enriquecer_eventos, get_ia_stats


def _evento_sem_artista():
    """Evento que dispara _precisa_ia mesmo após regras de artista/categoria.

    categoria "outros" garante a chamada de IA mesmo que limpar_e_extrair
    resolva o artista pelas regras (regras têm precedência sobre a IA).
    """
    return {
        "nome": "Show Teste ao vivo",
        "artista": "",
        "categoria": "outros",
        "data": "2026-12-01",
        "cidade": "São Paulo",
        "local": "Arena",
    }


def test_sem_eventos_stats_zeradas():
    enriquecer_eventos([])
    assert get_ia_stats() == {"pedidas": 0, "ok": 0}


def test_regras_resolvem_sem_chamar_ia():
    ev = {"nome": "Show Rock", "artista": "Já tem artista", "categoria": "show"}
    enriquecer_eventos([ev])
    assert get_ia_stats() == {"pedidas": 0, "ok": 0}


def test_ia_ok_contada(monkeypatch):
    monkeypatch.setattr(enricher, "ENRIQUECER_COM_IA", True)

    def fake_llm(*args, **kwargs):
        return json.dumps({
            "artista": "Artista X",
            "genero": "rock",
            "e_musical": True,
            "descricao": "Show ao vivo",
        })

    monkeypatch.setattr("agents.analista.chamar_llm", fake_llm)

    ev = _evento_sem_artista()
    enriquecer_eventos([ev])

    assert get_ia_stats() == {"pedidas": 1, "ok": 1}
    assert ev.get("enriquecido_ia") is True
    # artista preenchido (por regras ou pela IA — regras têm precedência)
    assert (ev.get("artista") or "").strip()


def test_ia_indisponivel_detectada(monkeypatch):
    """LM Studio off: chamar_llm lança exceção, ok fica 0 — sinal do aviso."""
    monkeypatch.setattr(enricher, "ENRIQUECER_COM_IA", True)

    def fake_llm(*args, **kwargs):
        raise ConnectionError("LM Studio offline")

    monkeypatch.setattr("agents.analista.chamar_llm", fake_llm)

    ev = _evento_sem_artista()
    enriquecer_eventos([ev])

    assert get_ia_stats() == {"pedidas": 1, "ok": 0}
    assert "enriquecido_ia" not in ev
