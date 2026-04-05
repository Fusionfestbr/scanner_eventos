"""
Dashboard Flask para visualização de eventos.
"""
import json
import os
import sys

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import threading
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, jsonify, Response

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-change-me-in-prod")

DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
FINAL_FILE = os.path.join(DATA_DIR, "final.json")
RANKING_FILE = os.path.join(DATA_DIR, "ranking.json")
RAW_FILE = os.path.join(DATA_DIR, "raw.json")
CLEAN_FILE = os.path.join(DATA_DIR, "clean.json")

coleta_status = {"ativo": False, "mensagem": "Pronto para coletar", "progresso": 0, "ultima_coleta": None}

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

try:
    from core.filtros import (
        filtrar_por_periodo,
        filtrar_por_escopo,
        filtrar_por_categoria,
        filtrar_por_cidade,
        filtrar_por_artista,
        buscar,
        resumo_estatistico,
        ordenar_por_data
    )
    FILTROS_AVAILABLE = True
except ImportError:
    FILTROS_AVAILABLE = False


def carregar_json(filepath):
    """Carrega arquivo JSON genérico."""
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def check_auth(username, password):
    """Verifica credenciais de auth básica."""
    if not DASHBOARD_PASSWORD:
        return True
    return password == DASHBOARD_PASSWORD


def authenticate():
    """Retorna resposta de autenticação."""
    return Response(
        'Acesso requerido', 401,
        {'WWW-Authenticate': 'Basic realm="Dashboard Login"'}
    )


def require_auth(f):
    """Decorator para proteger rotas com auth básica."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not DASHBOARD_PASSWORD:
            return f(*args, **kwargs)
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated


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


def filtrar_por_periodo(eventos, periodo):
    """Filtra eventos por período temporal."""
    if periodo == "todos":
        return eventos
    
    hoje = datetime.now().date()
    
    if periodo == "semana":
        data_limite = hoje + timedelta(days=7)
    elif periodo == "mes":
        data_limite = hoje + timedelta(days=30)
    elif periodo == "ano":
        data_limite = hoje + timedelta(days=365)
    else:
        return eventos
    
    eventos_filtrados = []
    for evento in eventos:
        data_str = evento.get("data", "")
        if not data_str:
            data_str = evento.get("evento", {}).get("data", "")
        if data_str:
            try:
                data_evento = datetime.fromisoformat(data_str.replace("Z", "+00:00")).date()
                if hoje <= data_evento <= data_limite:
                    eventos_filtrados.append(evento)
            except ValueError:
                continue
    
    return eventos_filtrados


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
@require_auth
def index():
    """Página principal com lista de eventos."""
    filtro_acao = request.args.get("acao", "todos")
    filtro_periodo = request.args.get("periodo", "todos")
    filtro_escopo = request.args.get("escopo", "todos")
    filtro_categoria = request.args.get("categoria", "todos")
    filtro_cidade = request.args.get("cidade", "")
    filtro_artista = request.args.get("artista", "")
    filtro_busca = request.args.get("busca", "")
    aba = request.args.get("aba", "oportunidades")
    
    eventos = carregar_ranking()
    
    eventos = filtrar_por_periodo(eventos, filtro_periodo)
    
    if filtro_escopo != "todos" and FILTROS_AVAILABLE:
        eventos = filtrar_por_escopo(eventos, filtro_escopo)
    
    if filtro_categoria != "todos" and FILTROS_AVAILABLE:
        eventos = filtrar_por_categoria(eventos, filtro_categoria)
    
    if filtro_cidade and FILTROS_AVAILABLE:
        eventos = filtrar_por_cidade(eventos, filtro_cidade)
    
    if filtro_artista and FILTROS_AVAILABLE:
        eventos = filtrar_por_artista(eventos, filtro_artista)
    
    if filtro_busca and FILTROS_AVAILABLE:
        eventos = buscar(eventos, filtro_busca)
    
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
    
    if filtro_acao != "todos":
        eventos = [e for e in eventos if e.get("acao_final") == filtro_acao]
    
    if aba == "oportunidades":
        eventos = [e for e in eventos if e.get("acao_final") == "COMPRAR"]
    
    return render_template(
        "index.html",
        eventos=eventos,
        estatisticas=estatisticas,
        filtro_acao=filtro_acao,
        filtro_periodo=filtro_periodo,
        filtro_escopo=filtro_escopo,
        filtro_categoria=filtro_categoria,
        filtro_cidade=filtro_cidade,
        filtro_artista=filtro_artista,
        filtro_busca=filtro_busca,
        aba=aba,
        coleta_status=coleta_status,
        learning_stats=learning_stats if learning_stats else None,
        learning_available=LEARNING_AVAILABLE
    )


@app.route("/brutos")
@require_auth
def brutos():
    """Página de eventos brutos (antes de qualquer filtro)."""
    eventos_brutos = carregar_json(RAW_FILE)
    
    if FILTROS_AVAILABLE:
        eventos_brutos = ordenar_por_data(eventos_brutos, crescente=True)
    
    estatisticas = {
        "total": len(eventos_brutos),
        "comprar": 0,
        "monitorar": 0,
        "ignorar": 0,
        "nota_media": 0
    }
    
    return render_template(
        "index.html",
        eventos=eventos_brutos,
        estatisticas=estatisticas,
        filtro_acao="todos",
        filtro_periodo="todos",
        filtro_escopo="todos",
        filtro_categoria="todos",
        filtro_cidade="",
        filtro_artista="",
        filtro_busca="",
        aba="brutos",
        coleta_status=coleta_status,
        learning_stats=None,
        learning_available=LEARNING_AVAILABLE
    )


@app.route("/validos")
@require_auth
def validos():
    """Página de eventos válidos (após validação)."""
    eventos_validos = carregar_json(CLEAN_FILE)
    
    if FILTROS_AVAILABLE:
        eventos_validos = ordenar_por_data(eventos_validos, crescente=True)
    
    estatisticas = {
        "total": len(eventos_validos),
        "comprar": 0,
        "monitorar": 0,
        "ignorar": 0,
        "nota_media": 0
    }
    
    return render_template(
        "index.html",
        eventos=eventos_validos,
        estatisticas=estatisticas,
        filtro_acao="todos",
        filtro_periodo="todos",
        filtro_escopo="todos",
        filtro_categoria="todos",
        filtro_cidade="",
        filtro_artista="",
        filtro_busca="",
        aba="validos",
        coleta_status=coleta_status,
        learning_stats=None,
        learning_available=LEARNING_AVAILABLE
    )


@app.route("/run-pipeline", methods=["POST"])
def run_pipeline():
    """Executa o pipeline de coleta em background."""
    global coleta_status
    
    if coleta_status["ativo"]:
        return jsonify({"status": "erro", "mensagem": "Coleta já em andamento"})
    
    def executar():
        global coleta_status
        try:
            coleta_status["ativo"] = True
            coleta_status["mensagem"] = "Iniciando coleta..."
            coleta_status["progresso"] = 5
            
            # Importar e executar o pipeline real
            from core.orchestrator import executar_pipeline
            
            coleta_status["mensagem"] = "Coletando eventos..."
            coleta_status["progresso"] = 20
            
            # Executar pipeline completo
            qtd_coletados, qtd_validados, qtd_analisados, qtd_finais, score = executar_pipeline()
            
            coleta_status["mensagem"] = f"Processado: {qtd_coletados} coletados, {qtd_finais} decisões"
            coleta_status["progresso"] = 100
            coleta_status["ativo"] = False
            coleta_status["ultima_coleta"] = datetime.now().isoformat()
            
            # Resetar status após 5 segundos
            import time
            time.sleep(5)
            coleta_status["mensagem"] = "Pronto para coletar"
            coleta_status["progresso"] = 0
            
        except Exception as e:
            coleta_status["ativo"] = False
            coleta_status["mensagem"] = f"Erro: {str(e)}"
            print(f"[ERRO COLETA] {e}")
    
    thread = threading.Thread(target=executar)
    thread.start()
    
    return jsonify({"status": "iniciado", "mensagem": "Coleta iniciada em background"})


@app.route("/api/coleta-status")
def get_coleta_status():
    """Retorna status da coleta para progresso visual."""
    return jsonify(coleta_status)


@app.route("/api/events")
def api_events():
    """API para auto-refresh dos eventos."""
    filtro_acao = request.args.get("acao", "todos")
    filtro_periodo = request.args.get("periodo", "todos")
    filtro_escopo = request.args.get("escopo", "todos")
    filtro_categoria = request.args.get("categoria", "todos")
    filtro_cidade = request.args.get("cidade", "")
    filtro_artista = request.args.get("artista", "")
    filtro_busca = request.args.get("busca", "")
    aba = request.args.get("aba", "oportunidades")
    
    eventos = carregar_ranking()
    eventos = filtrar_por_periodo(eventos, filtro_periodo)
    
    if filtro_escopo != "todos" and FILTROS_AVAILABLE:
        eventos = filtrar_por_escopo(eventos, filtro_escopo)
    if filtro_categoria != "todos" and FILTROS_AVAILABLE:
        eventos = filtrar_por_categoria(eventos, filtro_categoria)
    if filtro_cidade and FILTROS_AVAILABLE:
        eventos = filtrar_por_cidade(eventos, filtro_cidade)
    if filtro_artista and FILTROS_AVAILABLE:
        eventos = filtrar_por_artista(eventos, filtro_artista)
    if filtro_busca and FILTROS_AVAILABLE:
        eventos = buscar(eventos, filtro_busca)
    
    if filtro_acao != "todos":
        eventos = [e for e in eventos if e.get("acao_final") == filtro_acao]
    
    if aba == "oportunidades":
        eventos = [e for e in eventos if e.get("acao_final") == "COMPRAR"]
    
    estatisticas = calcular_estatisticas(eventos)
    
    return jsonify({
        "eventos": eventos,
        "estatisticas": estatisticas,
        "timestamp": datetime.now().isoformat()
    })


@app.route("/api/resumo")
def api_resumo():
    """API para resumo estatístico dos eventos."""
    eventos = carregar_ranking()
    if FILTROS_AVAILABLE:
        resumo = resumo_estatistico(eventos)
    else:
        resumo = {"total": len(eventos)}
    return jsonify(resumo)


@app.route("/refresh")
def refresh():
    """Recarrega a página principal."""
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
