"""
Configurações do scanner_eventos.
"""
import os

LM_STUDIO_URL = os.environ.get("LM_STUDIO_URL", "http://127.0.0.1:1234/v1/chat/completions")
MODEL = os.environ.get("MODEL", "google/gemma-3-4b")

REQUEST_TIMEOUT = 120
MAX_TOKENS = 500

INTERVALO_MINUTOS = int(os.environ.get("INTERVALO_MINUTOS", "30"))
MODO_COLETA = os.environ.get("MODO_COLETA", "real")

SCRAPER_TIMEOUT = int(os.environ.get("SCRAPER_TIMEOUT", "10"))
SCRAPER_RETRY = int(os.environ.get("SCRAPER_RETRY", "3"))

MIN_QUALITY_PERCENT = int(os.environ.get("MIN_QUALITY_PERCENT", "30"))
FALLBACK_ENABLED = os.environ.get("FALLBACK_ENABLED", "true").lower() == "true"
REJECTED_LOG_ENABLED = True

LOCK_FILE = os.path.join(os.path.dirname(__file__), "data", "running.lock")
LAST_RUN_FILE = os.path.join(os.path.dirname(__file__), "data", "last_run.json")
REJECTED_FILE = os.path.join(os.path.dirname(__file__), "data", "rejected.json")
