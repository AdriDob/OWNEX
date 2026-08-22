# -*- mode: python ; coding: utf-8 -*-
# ruff: noqa: UP009, F821 — spec file executed by PyInstaller, not imported.
from PyInstaller.utils.hooks import collect_all

datas = [
    ("desktop/native/ui", "desktop/native/ui"),
    ("desktop/native/services", "desktop/native/services"),
    ("assets/branding/themes", "assets/branding/themes"),
    ("assets/branding/design-tokens.json", "assets/branding"),
    ("assets/branding/fonts", "assets/branding/fonts"),
    ("assets/logos", "assets/logos"),
    ("run-desktop", "."),
]
binaries = []
hiddenimports = []
tmp_ret = collect_all("sqlalchemy")
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]
tmp_ret = collect_all("httpx")
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]
tmp_ret = collect_all("pydantic")
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]
tmp_ret = collect_all("qasync")
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]
tmp_ret = collect_all("PySide6")
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]
tmp_ret = collect_all("fastapi")
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]
tmp_ret = collect_all("starlette")
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]
tmp_ret = collect_all("uvicorn")
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]
tmp_ret = collect_all("prometheus_client")
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]
tmp_ret = collect_all("pydantic_settings")
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]
# Backend sidecar: the in-process API server (api.main) needs the full project
# tree available in the bundle so the desktop is self-contained and can
# produce real data (pipeline, scheduler, scrapers) on Windows.
for pkg in ("api", "database", "core", "cores", "apps"):
    tmp_ret = collect_all(pkg)
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]


a = Analysis(
    ["desktop/native/app.py"],
    pathex=[SPECPATH],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    [],
    exclude_binaries=True,
    name="OWNEX-Desktop-Alpha",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/logos/ownex-icon-alpha.ico",
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="OWNEX-Desktop-Alpha",
)
