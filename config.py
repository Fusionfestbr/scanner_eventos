"""
Configurações do scanner_eventos.
"""
import os

LM_STUDIO_URL = os.environ.get("LM_STUDIO_URL", "http://127.0.0.1:1234/v1/chat/completions")
MODEL = os.environ.get("MODEL", "google/gemma-3-4b")

REQUEST_TIMEOUT = 120
MAX_TOKENS = 500

MODO_COLETA = "real"

SCRAPER_TIMEOUT = int(os.environ.get("SCRAPER_TIMEOUT", "15"))
SCRAPER_RETRY = int(os.environ.get("SCRAPER_RETRY", "3"))

MIN_QUALITY_PERCENT = int(os.environ.get("MIN_QUALITY_PERCENT", "30"))
FALLBACK_ENABLED = False
REJECTED_LOG_ENABLED = True

SITES_CONFIG = {
    "ticketmaster": {
        "url": "https://www.ticketmaster.com.br/",
        "timeout": 30,
        "prioridade": "alta"
    },
    "ingresse": {
        "url": "https://www.ingresse.com/",
        "timeout": 30,
        "prioridade": "alta"
    },
    "sympla": {
        "url": "https://www.sympla.com.br/eventos",
        "timeout": 30,
        "prioridade": "alta"
    },
    "ticket360": {
        "url": "https://www.ticket360.com.br/",
        "timeout": 30,
        "prioridade": "alta"
    },
    "blueticket": {
        "url": "https://www.blueticket.com.br/",
        "timeout": 30,
        "prioridade": "media"
    },
    "livepass": {
        "url": "https://www.livepass.com.br/",
        "timeout": 30,
        "prioridade": "media"
    },
    "bilheteriadigital": {
        "url": "https://www.bilheteriadigital.com/",
        "timeout": 30,
        "prioridade": "media"
    },
    "ticketsforfun": {
        "url": "https://www.ticketsforfun.com.br/",
        "timeout": 30,
        "prioridade": "baixa"
    },
    "guicheweb": {
        "url": "https://www.guicheweb.com.br/",
        "timeout": 30,
        "prioridade": "baixa"
    },
    "q2ingressos": {
        "url": "https://q2ingressos.com.br/",
        "timeout": 30,
        "prioridade": "baixa"
    },
    "uhuu": {
        "url": "https://uhuu.com/",
        "timeout": 30,
        "prioridade": "baixa"
    },
    "zigtickets": {
        "url": "https://zig.tickets/pt-BR",
        "timeout": 30,
        "prioridade": "baixa"
    },
    "betimelapse": {
        "url": "https://betimelapse.com.br/",
        "timeout": 30,
        "prioridade": "baixa"
    }
}

SITES_ATIVOS = list(SITES_CONFIG.keys())

INTERVALO_MINUTOS = int(os.environ.get("INTERVALO_MINUTOS", "30"))

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8436380065:AAFFCJ0Z7EWmfHDGCpGQrlbBbKmHQCXVf6o")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "1048111648")
ALERTA_NOTA_MINIMA = float(os.environ.get("ALERTA_NOTA_MINIMA", "8.5"))
ALERTA_CONFIANCA_MINIMA = int(os.environ.get("ALERTA_CONFIANCA_MINIMA", "7"))
ALERTA_ENABLED = os.environ.get("ALERTA_ENABLED", "true").lower() == "true"

LOCK_FILE = os.path.join(os.path.dirname(__file__), "data", "running.lock")
LAST_RUN_FILE = os.path.join(os.path.dirname(__file__), "data", "last_run.json")
REJECTED_FILE = os.path.join(os.path.dirname(__file__), "data", "rejected.json")
NOTIFICADOS_FILE = os.path.join(os.path.dirname(__file__), "data", "notificados.json")
