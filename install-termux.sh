#!/usr/bin/env bash
# ── AVR Control Plane — Termux (Android) Installer ──
set -e

echo "╔══════════════════════════════════════════╗"
echo "║   AVR Control Plane — Termux Installer   ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# Update packages first
pkg update -y

# Install AVR toolchain
echo "[INFO] Installing AVR toolchain..."
pkg install -y avr-toolchain avrdude

echo ""
echo "[OK] AVR toolchain installed."
echo ""

for t in avr-gcc avr-objcopy avr-size avrdude; do
    if command -v "$t" &>/dev/null; then
        echo "  ✓ $t"
    else
        echo "  ✗ $t — NOT FOUND"
    fi
done

echo ""
echo "[INFO] Installing Python..."
pkg install -y python

echo ""
echo "[INFO] Installing Python dependencies..."
pip install PySide6 2>/dev/null || echo "[WARN] PySide6 may not work on Termux (optional)"

echo ""
echo "══════════════════════════════════════════"
echo "  DONE! Run: python3 terminal.py"
echo ""
echo "  NOTE: On Termux, you MUST use"
echo "  127.0.0.1:8090 (not localhost)"
echo "  to avoid Android DNS issues."
echo "══════════════════════════════════════════"