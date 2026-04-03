"""
Configurações do scanner_eventos.
"""
import os

LM_STUDIO_URL = os.environ.get("LM_STUDIO_URL", "http://127.0.0.1:1234/v1/chat/completions")
MODEL = os.environ.get("MODEL", "google/gemma-3-4b")

REQUEST_TIMEOUT = 120
MAX_TOKENS = 500
