"""
Scanner Eventos - Servidor Flask para Electron
Este arquivo inicia apenas o Flask (sem PyQt5) para ser usado com Electron.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dashboard.app import app

if __name__ == "__main__":
    print("[Flask] Servidor iniciado em http://127.0.0.1:5000")
    app.run(debug=False, host="127.0.0.1", port=5000, use_reloader=False)