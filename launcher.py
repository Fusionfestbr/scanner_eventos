"""
Launcher - Aplicação Desktop Fusion Revenda Master.
Inicia o Flask em background e abre o navegador automaticamente.
"""
import os
import sys
import webbrowser
import threading
import time
import subprocess

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PORT = 5000
HOST = "127.0.0.1"


def iniciar_flask():
    """Inicia o servidor Flask em background."""
    from dashboard.app import app
    app.run(debug=False, host=HOST, port=PORT, use_reloader=False)


def abrir_navegador():
    """Aguarda o servidor iniciar e abre o navegador."""
    time.sleep(2)
    webbrowser.open(f"http://{HOST}:{PORT}")


def main():
    """Função principal do launcher."""
    print("=" * 50)
    print("  Fusion Revenda Master - Desktop")
    print("=" * 50)
    print(f"\n  Iniciando servidor em http://{HOST}:{PORT}")
    print("  O navegador será aberto automaticamente...\n")

    flask_thread = threading.Thread(target=iniciar_flask, daemon=True)
    flask_thread.start()

    browser_thread = threading.Thread(target=abrir_navegador, daemon=True)
    browser_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n  Encerrando servidor...")
        sys.exit(0)


if __name__ == "__main__":
    main()
