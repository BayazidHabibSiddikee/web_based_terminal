<p align="center">
  <img src="banner.png" alt="AVR Control Plane Banner" width="100%">
</p>

# ⚡ AVR Control Plane
**Cross-Platform | Python | Web-Based Terminal Interface**

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Fedora](https://img.shields.io/badge/Fedora-Workstation-blue?logo=fedora&logoColor=white)](https://getfedora.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A lightweight web interface for compiling and flashing AVR microcontrollers without the bloat of traditional IDEs.

---

## 🚀 What It Does
**Write C code → Select your MCU → Click BUILD & FLASH → Done.**

- **Compile** `.c` files to `.elf` or `.hex` using `avr-gcc`.
- **Flash** directly to AVR chips via `avrdude`.
- **Run any shell command** through a raw terminal.
- **Support for 27+ AVR chips** (ATmega, ATtiny series).
- **Auto-detects** your platform and serial port.

---

## 🧠 Why This Exists
Traditional AVR development usually requires juggling multiple terminals, remembering complex `avr-gcc` flags, and fighting with `avrdude` parameters. 

This tool puts **everything into one screen** — a clean, cyberpunk-themed web terminal that talks to a lightweight Python backend. No Electron, no heavy IDE, no 500MB download.

---

## 🛠️ Quick Start

### 1. Install AVR Toolchain
Pick your platform and run the corresponding script to install `avr-gcc`, `avr-libc`, and `avrdude`:

| Platform | Command |
|----------|---------|
| **Fedora / RHEL** | `chmod +x install-dnf.sh && ./install-dnf.sh` |
| **Ubuntu / Debian** | `chmod +x install-apt.sh && ./install-apt.sh` |
| **Arch Linux** | `chmod +x install-pacman.sh && ./install-pacman.sh` |
| **Windows** | Double-click `install.bat` |
| **Android (Termux)** | `chmod +x install-termux.sh && ./install-termux.sh` |

### 2. Launch
```bash
# Linux / macOS / Termux
python3 terminal.py

# Windows
python terminal.py
A browser window opens automatically at http://localhost:8090.(Note: Termux users should open 127.0.0.1:8090 manually).📁 Project StructurePlaintextavr-control-plane/
├── index.html           # Frontend — web terminal UI
├── terminal.py          # Backend — HTTP server + browser launcher
├── flash_avr.py         # Core — compile, hex generation, flashing
├── requirements.txt     # Python dependencies
├── install-apt.sh       # Installer for Ubuntu / Debian
├── install-dnf.sh       # Installer for Fedora / RHEL
├── install-pacman.sh    # Installer for Arch Linux
├── install-termux.sh    # Installer for Android (Termux)
├── install.bat          # Installer for Windows
└── README.md            # You are here
🛰️ Supported MicrocontrollersSeriesChipavr-gcc MCUavrdude IDATmegaATmega328Patmega328pm328pATmegaATmega2560atmega2560m2560ATmegaATmega8atmega8m8ATtinyATtiny85attiny85t85ATtinyATtiny13Aattiny13t13Missing a chip? Simply add it to the BOARD_MAP dictionary in flash_avr.py.✨ Features🌐 Web TerminalColor-coded output: Green (Success), Red (Error), Cyan (Info).Live Status: Pulse animations for active processes.Security: Blocks dangerous commands (e.g., rm -rf /, shutdown).⚙️ BackendMulti-threaded: Slow flashing processes won't block the server.KISS Architecture: Uses Python's built-in http.server—no heavy API frameworks.Auto-Programmer Detection: Tries arduino, usbasp, avrisp, etc.🔧 Troubleshooting"avr-gcc not found": Run the install script for your platform."All programmers failed": Check your USB-TTL connection and verify the port name.Termux: Android DNS quirks mean you must use 127.0.0.1 instead of localhost.PySide6: Optional. If not installed, it defaults to your system browser.🛡️ SecurityThe server binds to 0.0.0.0:8090 (accessible on your local network).Commands have a 30-second timeout (60s for avrdude).Warning: Do not expose this to the public internet.📝 Tech StackFrontend: HTML, CSS, Vanilla JSBackend: Python 3.x (Standard Library)GUI: Optional PySide6 / Qt WebEngineTools: avr-gcc, avr-libc, avrdude📄 LicenseMIT License — Built with 🛠️ by Bayazid Habib Siddikee
