#!/usr/bin/env bash
# ── AVR Control Plane — Ubuntu/Debian/Mint Installer ──
set -e

echo "╔══════════════════════════════════════════╗"
echo "║   AVR Control Plane — APT Installer      ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# Check if running as root (for apt)
if [ "$EUID" -ne 0 ]; then
    echo "[INFO] Installing AVR toolchain (requires sudo)..."
    sudo apt update
    sudo apt install -y gcc-avr avr-libc avrdude
else
    apt update
    apt install -y gcc-avr avr-libc avrdude
fi

echo ""
echo "[OK] AVR toolchain installed."
echo ""

# Verify tools
for t in avr-gcc avr-objcopy avr-size avrdude; do
    if command -v "$t" &>/dev/null; then
        echo "  ✓ $t — $(which $t)"
    else
        echo "  ✗ $t — NOT FOUND"
    fi
done

echo ""
echo "[INFO] Installing Python dependencies..."
pip3 install --user PySide6 2>/dev/null || echo "[WARN] PySide6 install failed (optional — will use browser)"

echo ""
echo "══════════════════════════════════════════"
echo "  DONE! Run: python3 terminal.py"
echo "══════════════════════════════════════════"