"""
Compila o Scanner Eventos para .exe.
Execute: python compilar_exe.py
"""
import os
import sys
import subprocess

def compilar():
    """Compila o app para .exe usando PyInstaller."""
    print("[COMPILAR] Criando executável...")
    
    args = [
        "pyinstaller",
        "--onefile",
        "--noconsole",
        "--windowed",
        "--name", "ScannerEventos",
        "--add-data", "dashboard/templates;templates",
        "--add-data", "dashboard/static;static",
        "app.py"
    ]
    
    subprocess.run(args, check=True)
    print("[COMPILAR] Concluído! Executável em dist/ScannerEventos.exe")

if __name__ == "__main__":
    compilar()