# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Kindle Mailroom desktop build.

One spec, `sys.platform` conditionals. Requires the package itself and
googleapiclient importable in the environment running PyInstaller (so
`pip install .` first) plus pyinstaller-hooks-contrib for the lxml/
cryptography/certifi hooks:

    pip install . pyinstaller pyinstaller-hooks-contrib
    pyinstaller packaging/kindle-mailroom.spec

macOS/Windows outputs land in dist/; see docs/install-desktop.md for what to
do with them and .github/workflows/release.yml for how CI packages and ships
them. Linux gets an onedir console build for local verification only (see
Step 4 of the desktop-app plan) - it is never shipped, since pipx already
covers Linux users.
"""

import sys
from pathlib import Path

import googleapiclient

import kindle_mailroom

ROOT = Path(SPECPATH).resolve().parent  # kindle-mailroom/
PACKAGING = ROOT / "packaging"
APP_NAME = "Kindle Mailroom"
APP_VERSION = kindle_mailroom.__version__

# googleapiclient ships ~586 discovery docs; we only ever call the Gmail
# API (see src/kindle_mailroom/core/gmail_client.py), so bundle exactly one
# instead of ~50MB of JSON we'll never read.
DISCOVERY_DOC = Path(googleapiclient.__file__).parent / "discovery_cache" / "documents" / "gmail.v1.json"
if not DISCOVERY_DOC.exists():
    raise SystemExit(f"gmail.v1.json not found at {DISCOVERY_DOC} - googleapiclient layout changed?")

datas = [
    (str(ROOT / "src" / "kindle_mailroom" / "web" / "templates"), "kindle_mailroom/web/templates"),
    (str(ROOT / "src" / "kindle_mailroom" / "web" / "static"), "kindle_mailroom/web/static"),
    (str(DISCOVERY_DOC), "googleapiclient/discovery_cache/documents"),
]

a = Analysis(
    [str(PACKAGING / "desktop_launcher.py")],
    pathex=[str(ROOT / "src")],
    datas=datas,
    hiddenimports=[],
    # unittest is NOT safe to exclude despite the name: httplib2.auth ->
    # pyparsing.testing imports it at module load, as a real transitive
    # runtime dependency, not just for our own test suite. Found by the
    # local verification build in Step 4 - trust that build over intuition
    # about what "should" be test-only.
    excludes=["tkinter", "test"],
    noarchive=False,
)

# Belt-and-braces: drop any OTHER discovery doc a hook collected on its own
# (a hooks-contrib update has, in the past, pulled in the whole
# discovery_cache/documents directory for other Google API packages). Asset
# size in CI is the tripwire if this filter ever needs revisiting.
a.datas = [
    entry for entry in a.datas
    if "discovery_cache/documents" not in entry[0].replace("\\", "/")
    or entry[0].replace("\\", "/").endswith("gmail.v1.json")
]

pyz = PYZ(a.pure)

if sys.platform == "win32":
    # Onefile: a novice double-clicking inside Explorer's zip preview
    # extracts only the .exe, not a sibling _internal/ folder - onedir would
    # silently break for exactly the audience this build is for.
    exe = EXE(
        pyz, a.scripts, a.binaries, a.datas, [],
        name=APP_NAME,
        console=False,
        icon=str(PACKAGING / "icon.ico"),
    )

elif sys.platform == "darwin":
    exe = EXE(
        pyz, a.scripts, [],
        exclude_binaries=True,
        name=APP_NAME,
        console=False,
        # No codesign_identity: PyInstaller ad-hoc signs the arm64 binary
        # automatically, which is the minimum the kernel requires to run it
        # at all. This is not the same as a paid Developer ID signature -
        # see docs/install-desktop.md for the "Open Anyway" step this
        # still requires on first launch.
    )
    coll = COLLECT(exe, a.binaries, a.datas, name=APP_NAME)
    app = BUNDLE(
        coll,
        name=f"{APP_NAME}.app",
        icon=str(PACKAGING / "icon.icns"),
        bundle_identifier="io.github.cipshadow.mailroom",
        info_plist={
            "CFBundleShortVersionString": APP_VERSION,
            "CFBundleVersion": APP_VERSION,
            "NSHighResolutionCapable": True,
            # Normal foreground app: it now opens a real pywebview window
            # (see desktop.py) instead of the system browser, so it behaves
            # like any other windowed app - Dock icon, Cmd+Tab entry, no
            # more bouncing forever waiting for a window that never came.
            "LSUIElement": False,
        },
    )

else:
    # Dev-only verification build (Step 4) - never uploaded to a release.
    exe = EXE(
        pyz, a.scripts, [],
        exclude_binaries=True,
        name="kindle-mailroom-desktop",
        console=True,
    )
    coll = COLLECT(exe, a.binaries, a.datas, name="kindle-mailroom-desktop")
