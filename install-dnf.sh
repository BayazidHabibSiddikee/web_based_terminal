#!/usr/bin/env bash
# ── AVR Control Plane — Fedora/RHEL Installer ──
set -e

echo "╔══════════════════════════════════════════╗"
echo "║   AVR Control Plane — DNF Installer      ║"
echo "╚══════════════════════════════════════════╝"
echo ""

if [ "$EUID" -ne 0 ]; then
    echo "[INFO] Installing AVR toolchain (requires sudo)..."
    sudo dnf install -y avr-gcc avr-libc avrdude
else
    dnf install -y avr-gcc avr-libc avrdude
fi

echo ""
echo "[OK] AVR toolchain installed."
echo ""

for t in avr-gcc avr-objcopy avr-size avrdude; do
    if command -v "$t" &>/dev/null; then
        echo "  ✓ $t — $(which $t)"
    else
        echo "  ✗ $t — NOT FOUND"
    fi
done

echo ""
echo "[INFO] Installing Python dependencies..."
pip3 install --user PySide6 2>/dev/null || echo "[WARN] PySide6 install failed (optional)"

echo ""
echo "══════════════════════════════════════════"
echo "  DONE! Run: python3 terminal.py"
echo "══════════════════════════════════════════"