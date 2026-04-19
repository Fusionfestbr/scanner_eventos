"""
Scanner Eventos - Interface Desktop
Abre o dashboard em uma janela própria com WebView.
"""
import os
import sys
import threading
import time
import socket
from pathlib import Path

def verificar_porta_em_uso(porta=5000):
    """Verifica se a porta está em uso."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('127.0.0.1', porta)) == 0
    except:
        return False

def iniciar_servidor():
    """Inicia o servidor Flask em thread separada."""
    if verificar_porta_em_uso(5000):
        print("[APP] Servidor já está rodando na porta 5000")
        return
    
    print("[APP] Iniciando servidor Flask...")
    from dashboard.app import app
    app.run(debug=False, host="127.0.0.1", port=5000, use_reloader=False)

def main():
    """Main - Interface PyQt5 com WebView."""
    try:
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtWebEngineWidgets import QWebEngineView
        from PyQt5.QtWebEngineCore import QWebEngineProfile
        from PyQt5.QtCore import QUrl, QTimer
        from PyQt5.QtGui import QIcon, QGuiApplication
    except ImportError:
        print("[ERRO] PyQt5 não instalado. Execute: pip install PyQt5 PyQtWebEngine")
        sys.exit(1)
    
    tela_iniciada = threading.Event()
    servidor_thread = None
    
    def verificar_servidor_pronto():
        """Verifica se o servidor está pronto."""
        for _ in range(50):
            if verificar_porta_em_uso(5000):
                return True
            time.sleep(0.2)
        return False
    
    def rodar_app():
        global servidor_thread
        
        app_qt = QApplication(sys.argv)
        
        janela = QWebEngineView()
        janela.setWindowTitle("Scanner Eventos")
        janela.resize(1280, 800)
        
        profile = QWebEngineProfile.defaultProfile()
        profile.setHttpUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        tela_iniciada.set()
        
        if verificar_servidor_pronto():
            janela.load(QUrl("http://127.0.0.1:5000"))
        else:
            print("[ERRO] Servidor não iniciou a tempo")
            sys.exit(1)
        
        janela.show()
        
        def fechar_tudo():
            """Fecha o app e para o servidor."""
            QApplication.quit()
        
        janela.closeEvent = lambda event: fechar_tudo()
        
        sys.exit(app_qt.exec_())
    
    if verificar_porta_em_uso(5000):
        print("[APP] Servidor já está rodando. Abrindo interface...")
        tela_iniciada.set()
    else:
        print("[APP] Iniciando servidor em background...")
        servidor_thread = threading.Thread(target=iniciar_servidor, daemon=True)
        servidor_thread.start()
    
    tela_iniciada.wait()
    
    if not verificar_porta_em_uso(5000):
        print("[ERRO] Falha ao iniciar servidor")
        sys.exit(1)
    
    rodar_app()

if __name__ == "__main__":
    main()