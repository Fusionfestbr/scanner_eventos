# -*- mode: python ; coding: utf-8 -*-

import os

datas = [
    ('dashboard/templates', 'dashboard/templates'),
    ('data', 'data'),
]

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'dashboard.app',
        'core.orchestrator',
        'core.learning',
        'core.cache',
        'core.filtros',
        'core.notifier',
        'core.executor',
        'core.executor_real',
        'core.predictor',
        'core.decision',
        'core.ranking',
        'core.data_quality',
        'core.arbitrage',
        'core.scheduler',
        'core.historico_valorizacao',
        'utils.logger',
        'utils.rate_limiter',
        'utils.validation',
        'utils.checkpoint',
        'utils.date_utils',
        'utils.http_client',
        'flask',
        'jinja2',
        'werkzeug',
        'requests',
        'psutil',
        'urllib3',
        'loguru',
    ],
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
    name='ScannerEventos',
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
