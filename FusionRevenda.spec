# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=[('dashboard/templates', 'dashboard/templates')],
    hiddenimports=['dashboard.app', 'core.filtros', 'core.classificadores', 'core.learning', 'core.orchestrator', 'core.scheduler', 'core.ranking', 'core.notifier', 'core.decision', 'core.predictor', 'core.executor', 'core.arbitrage', 'core.executor_real', 'core.data_quality', 'core.historico_valorizacao', 'agents.scraper', 'agents.coletor', 'agents.validador', 'agents.analista', 'agents.auditor', 'agents.aggregator', 'agents.eventim_api', 'agents.ingresse_api', 'agents.livepass_api', 'agents.q2ingressos_api', 'agents.zigtickets_api', 'agents.guicheweb_api', 'utils.date_utils'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='FusionRevenda',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
