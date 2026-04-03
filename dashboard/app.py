"""
Dashboard Flask para visualização de eventos.
"""
import json
import os
from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
FINAL_FILE = os.path.join(DATA_DIR, "final.json")
RANKING_FILE = os.path.join(DATA_DIR, "ranking.json")

try:
    from core.learning import (
        calcular_metricas_financeiras,
        calcular_metricas_moving_average,
        analisar_padroes,
        verificar_performance,
        obter_thresholds,
        carregar_resultados
    )
    LEARNING_AVAILABLE = True
except ImportError:
    LEARNING_AVAILABLE = False


def carregar_eventos():
    """Carrega eventos do arquivo final.json."""
    if not os.path.exists(FINAL_FILE):
        return []
    try:
        with open(FINAL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def carregar_ranking():
    """Carrega ranking do arquivo ranking.json."""
    if not os.path.exists(RANKING_FILE):
        return carregar_eventos()
    try:
        with open(RANKING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def calcular_estatisticas(eventos):
    """Calcula estatísticas."""
    total = len(eventos)
    if total == 0:
        return {"total": 0, "comprar": 0, "monitorar": 0, "ignorar": 0, "nota_media": 0}
    
    comprar = sum(1 for e in eventos if e.get("acao_final") == "COMPRAR")
    monitorar = sum(1 for e in eventos if e.get("acao_final") == "MONITORAR")
    ignorar = sum(1 for e in eventos if e.get("acao_final") == "IGNORAR")
    
    notas = [e.get("analise", {}).get("nota_final", 0) for e in eventos]
    nota_media = sum(notas) / total if total > 0 else 0
    
    return {
        "total": total,
        "comprar": comprar,
        "monitorar": monitorar,
        "ignorar": ignorar,
        "nota_media": round(nota_media, 2)
    }


@app.route("/")
def index():
    """Página principal com lista de eventos."""
    filtro = request.args.get("acao", "todos")
    
    eventos = carregar_ranking()
    estatisticas = calcular_estatisticas(eventos)
    
    learning_stats = {}
    if LEARNING_AVAILABLE:
        try:
            learning_stats = {
                "metricas_financeiras": calcular_metricas_financeiras(),
                "moving_average": calcular_metricas_moving_average(),
                "padroes": analisar_padroes(),
                "performance": verificar_performance(),
                "thresholds": obter_thresholds()
            }
        except Exception:
            learning_stats = {}
    
    if filtro != "todos":
        eventos = [e for e in eventos if e.get("acao_final") == filtro]
    
    return render_template(
        "index.html",
        eventos=eventos,
        estatisticas=estatisticas,
        filtro=filtro,
        learning_stats=learning_stats if learning_stats else None,
        learning_available=LEARNING_AVAILABLE
    )


@app.route("/metrics")
def metrics():
    """API para métricas de aprendizado."""
    if not LEARNING_AVAILABLE:
        return jsonify({"error": "Learning module not available"})
    
    try:
        return jsonify({
            "financeiras": calcular_metricas_financeiras(),
            "moving_average": calcular_metricas_moving_average(),
            "padroes": analisar_padroes(),
            "performance": verificar_performance(),
            "thresholds": obter_thresholds()
        })
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/refresh")
def refresh():
    """Recarrega a página principal."""
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
