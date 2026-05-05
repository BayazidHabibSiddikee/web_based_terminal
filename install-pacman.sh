#!/usr/bin/env bash
# ── AVR Control Plane — Arch Linux Installer ──
set -e

echo "╔══════════════════════════════════════════╗"
echo "║   AVR Control Plane — Pacman Installer   ║"
echo "╚══════════════════════════════════════════╝"
echo ""

if [ "$EUID" -ne 0 ]; then
    sudo pacman -Syu --noconfirm avr-gcc avr-libc avrdude
else
    pacman -Syu --noconfirm avr-gcc avr-libc avrdude
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
pip install --user PySide6 2>/dev/null || echo "[WARN] PySide6 install failed (optional)"

echo ""
echo "══════════════════════════════════════════"
echo "  DONE! Run: python3 terminal.py"
echo "══════════════════════════════════════════"