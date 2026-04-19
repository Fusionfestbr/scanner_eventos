"""
Dashboard Flask para visualização de eventos.
"""
import json
import os
import secrets
import sys

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import threading
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, jsonify, Response

from utils.logger import logger
from utils.rate_limiter import get_rate_limiter
from utils.validation import validar_busca, validar_filtro, sanitizar_string

app = Flask(__name__)

rate_limiter = get_rate_limiter()


@app.before_request
def check_rate_limit():
    """Rate limiting para todas as rotas."""
    if request.endpoint in [None, 'static']:
        return None
    
    ip = request.remote_addr or 'unknown'
    
    if request.endpoint:
        permitido, motivo = rate_limiter.check(ip)
        
        if not permitido:
            logger.warning(f"Rate limit excedido para {ip} em {request.endpoint}")
            return jsonify({"status": "erro", "mensagem": motivo}), 429
    
    return None
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)
logger.info("Dashboard iniciado")

DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
FINAL_FILE = os.path.join(DATA_DIR, "final.json")
RANKING_FILE = os.path.join(DATA_DIR, "ranking.json")
RAW_FILE = os.path.join(DATA_DIR, "raw.json")
CLEAN_FILE = os.path.join(DATA_DIR, "clean.json")

coleta_status = {"ativo": False, "mensagem": "Pronto para coletar", "progresso": 0, "ultima_coleta": None}

# Auto-coleta configurável
AUTO_COLETA_ENABLED = False
AUTO_COLETA_INTERVALO = 120  # 2 horas em minutos
auto_coleta_timer = None
auto_coleta_proxima = None

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
    from core.cache import get_cache_stats
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False

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
        logger.warning("AVISO: DASHBOARD_PASSWORD não configurada - acesso sem autenticação")
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
            logger.warning("Acesso permitido sem autenticação")
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
    
    cache_stats = {}
    if CACHE_AVAILABLE:
        try:
            cache_stats = get_cache_stats()
        except Exception:
            cache_stats = {}
    
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
        cache_stats=cache_stats if cache_stats else None,
        cache_available=CACHE_AVAILABLE,
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
        cache_stats=None,
        cache_available=CACHE_AVAILABLE,
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
        cache_stats=None,
        cache_available=CACHE_AVAILABLE,
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
@require_auth
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
            coleta_status["ultima_coleta"] = datetime.now().isoformat()
            
            from core.orchestrator import executar_pipeline, get_pipeline_status
            
            coleta_status["mensagem"] = "Coletando eventos..."
            coleta_status["progresso"] = 20
            
            result = executar_pipeline()
            qtd_coletados, qtd_validados, qtd_analisados, qtd_finais, score, cache_stats = result
            
            pipeline_status = get_pipeline_status()
            coleta_status["etapas"] = pipeline_status.get("etapas", [])
            coleta_status["cache_stats"] = cache_stats
            
            coleta_status["mensagem"] = f"Processado: {qtd_coletados} coletados, {qtd_finais} decisões ({cache_stats.get('cache_hits', 0)} do cache)"
            
            coleta_status["mensagem"] = f"Processado: {qtd_coletados} coletados, {qtd_finais} decisões"
            coleta_status["progresso"] = 100
            coleta_status["ativo"] = False
            
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
@require_auth
def get_coleta_status():
    """Retorna status da coleta para progresso visual."""
    from core.orchestrator import get_pipeline_status
    pipeline_status = get_pipeline_status()
    coleta_status["etapas"] = pipeline_status.get("etapas", [])
    coleta_status["etapa_atual"] = pipeline_status.get("etapa_atual", "")
    return jsonify(coleta_status)


@app.route("/api/events")
@require_auth
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
@require_auth
def api_resumo():
    """API para resumo estatístico dos eventos."""
    from core.orchestrator import get_pipeline_status
    pipeline_status = get_pipeline_status()
    eventos = carregar_ranking()
    if FILTROS_AVAILABLE:
        resumo = resumo_estatistico(eventos)
    else:
        resumo = {"total": len(eventos)}
    resumo["pipeline_status"] = pipeline_status
    return jsonify(resumo)


@app.route("/health")
def health_check():
    """Endpoint de saúde do sistema."""
    import psutil
    
    try:
        from core.orchestrator import get_pipeline_status
        pipeline_status = get_pipeline_status()
    except:
        pipeline_status = {"ativo": False, "etapa_atual": "indisponivel"}
    
    try:
        from core.learning import calcular_metricas_financeiras
        metricas = calcular_metricas_financeiras()
    except:
        metricas = {"total_operacoes": 0, "lucro_total": 0}
    
    try:
        from utils.checkpoint import get_checkpoint, get_estado_pipeline
        checkpoint = get_checkpoint()
        estado_pipeline = get_estado_pipeline()
        checkpoint_info = {
            "existe": checkpoint.existe(),
            "etapa": checkpoint.get_etapa(),
            "timestamp": checkpoint.get_timestamp()
        }
        pipeline_info = {
            "etapa_atual": estado_pipeline.get_etapa_atual(),
            "progresso": estado_pipeline.get_progresso(),
            "saudavel": estado_pipeline.esta_saudavel(),
            "erros": len(estado_pipeline.get_erros())
        }
    except:
        checkpoint_info = {}
        pipeline_info = {}
    
    health_data = {
        "status": "UP",
        "timestamp": datetime.now().isoformat(),
        "sistema": {
            "python": True,
            "flask": True,
            "lm_studio": _check_lm_studio(),
        },
        "pipeline": pipeline_status,
        "metricas_financeiras": metricas,
        "checkpoint": checkpoint_info,
        "pipeline_estado": pipeline_info,
        "recursos": {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        }
    }
    
    return jsonify(health_data)


def _check_lm_studio() -> bool:
    """Verifica se LM Studio está disponível."""
    try:
        import requests
        r = requests.get("http://127.0.0.1:1234/v1/models", timeout=2)
        return r.status_code == 200
    except:
        return False


@app.route("/refresh")
def refresh():
    """Recarrega a página principal."""
    return redirect(url_for("index"))


@app.route("/api/auto-coleta-status")
@require_auth
def api_auto_coleta_status():
    """Retorna status da auto-coleta."""
    global auto_coleta_proxima
    return jsonify({
        "enabled": AUTO_COLETA_ENABLED,
        "intervalo": AUTO_COLETA_INTERVALO,
        "proxima": auto_coleta_proxima.isoformat() if auto_coleta_proxima else None
    })


@app.route("/api/auto-coleta-toggle", methods=["POST"])
@require_auth
def api_auto_coleta_toggle():
    """Liga/desliga auto-coleta."""
    global AUTO_COLETA_ENABLED, auto_coleta_timer, auto_coleta_proxima
    
    data = request.get_json() or {}
    enabled = data.get("enabled", not AUTO_COLETA_ENABLED)
    intervalo = data.get("intervalo", AUTO_COLETA_INTERVALO)
    
    if enabled and intervalo > 0:
        AUTO_COLETA_ENABLED = True
        AUTO_COLETA_INTERVALO = intervalo
        auto_coleta_proxima = datetime.now() + timedelta(minutes=intervalo)
        _iniciar_auto_coleta(intervalo)
        mensagem = f"Auto-coleta iniciada: a cada {intervalo} min"
    else:
        AUTO_COLETA_ENABLED = False
        if auto_coleta_timer:
            auto_coleta_timer.cancel()
            auto_coleta_timer = None
        auto_coleta_proxima = None
        mensagem = "Auto-coleta parada"
    
    return jsonify({"status": "ok", "enabled": AUTO_COLETA_ENABLED, "intervalo": AUTO_COLETA_INTERVALO, "mensagem": mensagem})


@app.route("/api/enviar-alerta", methods=["POST"])
@require_auth
def api_enviar_alerta():
    """Envia alerta manual via Telegram."""
    from core.notifier import enviar_alerta
    
    data = request.get_json() or {}
    mensagem = data.get("mensagem", "Alerta de teste")
    
    try:
        enviado = enviar_alerta(mensagem)
        return jsonify({"status": "ok", "enviado": enviado})
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)})


def _iniciar_auto_coleta(minutos):
    """Inicia o timer de auto-coleta."""
    global auto_coleta_timer, auto_coleta_proxima
    
    def executar_coleta_automatica():
        global auto_coleta_proxima, AUTO_COLETA_ENABLED
        try:
            if not coleta_status["ativo"]:
                coleta_status["ativo"] = True
                coleta_status["mensagem"] = "Auto-coleta em andamento..."
                from core.orchestrator import executar_pipeline
                result = executar_pipeline()
                coleta_status["ativo"] = False
                coleta_status["ultima_coleta"] = datetime.now().isoformat()
        except Exception as e:
            print(f"[AUTO-COLETA] Erro: {e}")
        finally:
            if AUTO_COLETA_ENABLED:
                auto_coleta_proxima = datetime.now() + timedelta(minutes=AUTO_COLETA_INTERVALO)
                _iniciar_auto_coleta(AUTO_COLETA_INTERVALO)
    
    if auto_coleta_timer:
        auto_coleta_timer.cancel()
    
    auto_coleta_timer = threading.Timer(minutos * 60, executar_coleta_automatica)
    auto_coleta_timer.daemon = True
    auto_coleta_timer.start()
    print(f"[AUTO-COLETA] Timer iniciado: {minutos} min")


if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=5000)
