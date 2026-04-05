@echo off
echo ================================================
echo   Fusion Revenda Master - Gerando Executavel
echo ================================================
echo.

REM Verificar se pyinstaller esta instalado
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo Instalando PyInstaller...
    pip install pyinstaller
    echo.
)

REM Gerar o executavel
echo Gerando executavel...
pyinstaller --onefile --windowed --name="FusionRevenda" --add-data "dashboard/templates;dashboard/templates" --add-data "data;data" --hidden-import=dashboard.app --hidden-import=core.filtros --hidden-import=core.classificadores --hidden-import=core.learning --hidden-import=core.orchestrator --hidden-import=core.scheduler --hidden-import=core.ranking --hidden-import=core.notifier --hidden-import=core.decision --hidden-import=core.predictor --hidden-import=core.executor --hidden-import=core.arbitrage --hidden-import=core.executor_real --hidden-import=core.data_quality --hidden-import=core.historico_valorizacao --hidden-import=agents.scraper --hidden-import=agents.coletor --hidden-import=agents.validador --hidden-import=agents.analista --hidden-import=agents.auditor --hidden-import=agents.aggregator --hidden-import=agents.eventim_api --hidden-import=agents.ingresse_api --hidden-import=agents.livepass_api --hidden-import=agents.q2ingressos_api --hidden-import=agents.zigtickets_api --hidden-import=agents.guicheweb_api --hidden-import=utils.date_utils launcher.py

echo.
if exist "dist\FusionRevenda.exe" (
    echo ================================================
    echo   SUCESSO!
    echo   Executavel gerado em: dist\FusionRevenda.exe
    echo ================================================
) else (
    echo ================================================
    echo   ERRO! Verifique as mensagens acima.
    echo ================================================
)

echo.
pause
