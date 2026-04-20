# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Scan Input - Vietnamese OCR Tool."""

import os
import sys
from pathlib import Path

block_cipher = None

# Paths to bundled tools (set by build script)
TESSERACT_DIR = os.environ.get("TESSERACT_DIR", r"C:\Program Files\Tesseract-OCR")
POPPLER_DIR = os.environ.get("POPPLER_DIR", r"C:\poppler\Library\bin")

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("src", "src"),
        ("templates", "templates"),
    ],
    hiddenimports=[
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "pytesseract",
        "pdf2image",
        "PIL",
        "numpy",
        "cv2",
        "openpyxl",
        "pdfplumber",
        "docx",
        "vietocr",
        "vietocr.tool.predictor",
        "vietocr.tool.config",
        "vietocr.tool.translate",
        "torch",
        "torchvision",
        "rapidocr",
        "onnxruntime",
        "underthesea",
        "underthesea.pipeline",
    ],
    hookspath=[],
    excludes=[
        "matplotlib",
        "scipy.tests",
        "pandas.tests",
        "tkinter",
        "paddle",
        "paddleocr",
        "paddlepaddle",
        "paddlex",
        "easyocr",
    ],
    noarchive=False,
    cipher=block_cipher,
)

# Add Tesseract binaries if available
if os.path.isdir(TESSERACT_DIR):
    for root, dirs, files in os.walk(TESSERACT_DIR):
        for f in files:
            src = os.path.join(root, f)
            rel = os.path.relpath(root, TESSERACT_DIR)
            dst = os.path.join("tesseract", rel)
            a.datas.append((src, dst, "DATA"))

# Add Poppler binaries if available
if os.path.isdir(POPPLER_DIR):
    for f in os.listdir(POPPLER_DIR):
        src = os.path.join(POPPLER_DIR, f)
        if os.path.isfile(src):
            a.datas.append((src, "poppler", "DATA"))

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ScanInput",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon="resources/icon.ico" if os.path.exists("resources/icon.ico") else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name="ScanInput",
)
