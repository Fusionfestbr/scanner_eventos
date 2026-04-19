"""
Executar Scanner Eventos - Versão desktop sem terminal.
Execute este arquivo (duplo clique) para abrir a interface.
"""
import os
import sys
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_PY = os.path.join(SCRIPT_DIR, "app.py")

def main():
    """Executa o app.py usando pythonw (sem terminal)."""
    python_exec = sys.executable
    
    if python_exec.endswith("pythonw.exe"):
        subprocess.Popen([python_exec, APP_PY], creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        python_w = python_exec.replace("python.exe", "pythonw.exe")
        if os.path.exists(python_w):
            subprocess.Popen([python_w, APP_PY], creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            subprocess.Popen([python_exec, APP_PY], creationflags=subprocess.CREATE_NO_WINDOW)

if __name__ == "__main__":
    main()