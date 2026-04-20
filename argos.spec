# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Argos — AI Vision Engineer Agent.

Usage:
    pyinstaller argos.spec
"""

import sys
import os
from pathlib import Path

block_cipher = None

# Detect platform
is_macos = sys.platform == "darwin"
is_windows = sys.platform == "win32"
is_linux = sys.platform.startswith("linux")

# Project root
project_root = os.path.abspath(".")

# Data files to bundle
datas = []

# Include assets directory
assets_dir = os.path.join(project_root, "assets")
if os.path.isdir(assets_dir):
    datas.append((assets_dir, "assets"))

# Include config directory
config_dir = os.path.join(project_root, "config")
if os.path.isdir(config_dir):
    datas.append((config_dir, "config"))

# Hidden imports — ensure all submodules are found
hidden_imports = [
    # PyQt6 modules
    "PyQt6.QtWidgets",
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    # Core modules
    "core",
    "core.models",
    "core.interfaces",
    "core.image_processor",
    "core.image_store",
    "core.key_manager",
    "core.logger",
    "core.validators",
    "core.exceptions",
    "core.error_handler",
    # Core analyzers
    "core.analyzers",
    "core.analyzers.feature_analyzer",
    "core.analyzers.histogram_analyzer",
    "core.analyzers.noise_analyzer",
    "core.analyzers.edge_analyzer",
    "core.analyzers.shape_analyzer",
    # Core align
    "core.align",
    "core.align.align_engine",
    "core.align.pattern_align",
    "core.align.feature_align",
    "core.align.contour_align",
    "core.align.blob_align",
    "core.align.caliper_align",
    # Core inspection
    "core.inspection",
    "core.inspection.blob_inspector",
    "core.inspection.pattern_inspector",
    "core.inspection.linear_caliper_inspector",
    "core.inspection.circular_caliper_inspector",
    "core.inspection.candidate_generator",
    "core.inspection.optimizer",
    # Core evaluation
    "core.evaluation",
    "core.evaluation.evaluator",
    "core.evaluation.failure_analyzer",
    "core.evaluation.feasibility_analyzer",
    # Core export
    "core.export",
    "core.export.json_exporter",
    "core.export.pdf_exporter",
    "core.export.image_exporter",
    # Core providers
    "core.providers",
    "core.providers.base_provider",
    "core.providers.provider_factory",
    "core.providers.openai_provider",
    "core.providers.claude_provider",
    "core.providers.gemini_provider",
    # UI modules
    "ui",
    "ui.main_window",
    "ui.style",
    "ui.theme",
    "ui.pages",
    "ui.components",
    "ui.dialogs",
    "ui.workers",
    "ui.widgets",
    # Third-party
    "cv2",
    "numpy",
    "cryptography",
    "reportlab",
]

# Icon
icon_file = None
if is_macos:
    icns = os.path.join(assets_dir, "icon.icns")
    if os.path.exists(icns):
        icon_file = icns
elif is_windows:
    ico = os.path.join(assets_dir, "icon.ico")
    if os.path.exists(ico):
        icon_file = ico
else:
    png = os.path.join(assets_dir, "icon.png")
    if os.path.exists(png):
        icon_file = png

a = Analysis(
    ["main.py"],
    pathex=[project_root],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "pytest",
        "pytest_qt",
        "_pytest",
        "tests",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="Argos",
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
    icon=icon_file,
)

# macOS .app bundle
if is_macos:
    app = BUNDLE(
        exe,
        name="Argos.app",
        icon=icon_file,
        bundle_identifier="com.argosvision.argos",
        info_plist={
            "CFBundleShortVersionString": "1.0.0",
            "CFBundleVersion": "1.0.0",
            "NSHighResolutionCapable": True,
        },
    )
