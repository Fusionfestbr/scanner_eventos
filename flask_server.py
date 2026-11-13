"""
Scanner Eventos - Servidor Flask para Electron
Este arquivo inicia apenas o Flask (sem PyQt5) para ser usado com Electron.
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dashboard.app import app


def _limpar_porta(porta: int = 5000) -> None:
    """Encerra órfãos de sessões anteriores que estejam escutando a porta.

    O Electron mata o cmd.exe ao fechar, mas o Python filho pode sobreviver
    e continuar com código antigo na porta — a janela nova então conectaria
    no servidor velho. Sem órfãos, não há o que limpar.
    """
    try:
        out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                             timeout=15).stdout
        pids = {int(m) for m in re.findall(
            rf"127\.0\.0\.1:{porta}\s+\S+\s+LISTENING\s+(\d+)", out)}
        pids.discard(os.getpid())
        for pid in pids:
            print(f"[Flask] Porta {porta} ocupada por PID {pid} (orfao) — encerrando")
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                           capture_output=True)
    except Exception as e:
        print(f"[Flask] Limpeza de porta ignorada: {e}")


if __name__ == "__main__":
    _limpar_porta(5000)
    print("[Flask] Servidor iniciado em http://127.0.0.1:5000")
    app.run(debug=False, host="127.0.0.1", port=5000, use_reloader=False)
