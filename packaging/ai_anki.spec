# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH).parent


def optional_collect(package: str):
    """Collect runtime data/binaries without copying raw Python source files."""
    try:
        return collect_all(package, include_py_files=False)
    except Exception:
        return [], [], []


datas = [
    (str(ROOT / "assets"), "assets"),
]
binaries = []
hiddenimports = []

# Only packages that need native binaries or runtime data are collected
# explicitly. Cloud SDKs are discovered normally by PyInstaller, which avoids
# copying their test fixtures and very long source filenames into the release.
for package in (
    "customtkinter",
    "faster_whisper",
    "ctranslate2",
    "tokenizers",
    "av",
    "piper",
    "piper_phonemize",
    "sounddevice",
    "soundfile",
):
    package_datas, package_binaries, package_hiddenimports = optional_collect(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

a = Analysis(
    [str(ROOT / "main_gui_custom.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(ROOT / "packaging" / "runtime_workdir.py")],
    excludes=[
        "pytest",
        "pytest_cov",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AI Anki Language Assistant",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(ROOT / "assets" / "app_icon.ico"),
    contents_directory="_i",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="AIAnki",
)
