# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=[('static', 'static'), ('config.ini', '.')],
    hiddenimports=[
        'engineio.async_drivers.gevent',
        'engineio.async_drivers.gevent_uwsgi', 
        'gevent',
        'gevent.ssl',
        'gevent.socket',
        'gevent.threading',
        'gevent.queue',
        'gevent.event',
        'gevent.lock',
        'gevent.local',
        'gevent._ssl3',
        'gevent.monkey',
        'geventwebsocket',
        'geventwebsocket.handler',
        'rich.console', 
        'rich.table', 
        'rich.panel', 
        'rich.prompt',
        'src.audio.voice_detector',
        'src.audio.audio_ducker'
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
    name='ClubVoice',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
