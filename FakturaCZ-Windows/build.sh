#!/bin/bash
# ============================================================
# FakturaCZ — Build standalone executable (Linux/macOS)
# ============================================================
# Prerequisites:
#   1. Python 3.11+ installed
#   2. pip install -r requirements.txt
# ============================================================

set -e

echo ""
echo "========================================"
echo " FakturaCZ — Building executable"
echo "========================================"
echo ""

echo "[1/3] Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "[2/3] Building executable with PyInstaller..."
pyinstaller \
    --name "FakturaCZ" \
    --onedir \
    --windowed \
    --noconfirm \
    --clean \
    --add-data "app:app" \
    main.py

echo ""
echo "[3/3] Creating data directory..."
mkdir -p dist/FakturaCZ/data

echo ""
echo "========================================"
echo " BUILD COMPLETE"
echo "========================================"
echo ""
echo " The application is in: dist/FakturaCZ/"
echo " Run: dist/FakturaCZ/FakturaCZ"
echo ""
echo " All invoice data will be stored in:"
echo "   dist/FakturaCZ/data/"
echo ""
