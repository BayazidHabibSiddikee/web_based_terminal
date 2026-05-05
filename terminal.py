"""
AVR Control Plane — Backend Server
Works on Windows, Linux, macOS, and Android (Termux).
PySide6 is OPTIONAL — opens system browser if not installed.
"""

import os
import sys
import subprocess
import threading
import platform
import signal
import shutil
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from flash_avr import flash_avr, generate_hex, generate_elf, get_platform

PORT = 8090

# ── Determine browser command per platform ────────────────────────────────────

def open_browser(url):
    """Open URL in the default browser — cross-platform."""
    plat = get_platform()
    try:
        if plat == "windows":
            os.startfile(url)
        elif plat == "mac":
            subprocess.Popen(["open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            # Linux / Termux — try xdg-open, then sensible-browser, then firefox
            for cmd in ["xdg-open", "sensible-browser", "firefox", "google-chrome"]:
                if shutil.which(cmd):
                    subprocess.Popen([cmd, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return
            print(f"[WARN] No browser found. Open manually: {url}")
    except Exception as e:
        print(f"[WARN] Could not open browser: {e}")
        print(f"       Open manually: {url}")


# ── Try importing PySide6 (optional) ──────────────────────────────────────────

def try_pyside6(url):
    """Try launching PySide6 window. Returns True if successful, False otherwise."""
    try:
        from PySide6.QtCore import QUrl
        from PySide6.QtWidgets import QApplication, QMainWindow
        from PySide6.QtWebEngineWidgets import QWebEngineView
        from PySide6.QtWebEngineCore import QWebEngineSettings

        class Win(QMainWindow):
            def __init__(self):
                super().__init__()
                self.setWindowTitle("AVR Control Plane")
                self.browser = QWebEngineView()
                s = self.browser.settings()
                s.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
                s.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
                self.browser.setUrl(QUrl(url))
                self.setCentralWidget(self.browser)
                self.resize(1200, 800)
                self.show()

        app = QApplication(sys.argv)
        app.setApplicationName("AVR Control Plane")
        w = Win()
        sys.exit(app.exec())
        return True
    except ImportError:
        return False
    except Exception as e:
        print(f"[PySide6] Failed to launch: {e}")
        return False


# ── HTTP Request Handler ──────────────────────────────────────────────────────

BLOCKED_COMMANDS = [
    "rm -rf /", "mkfs", "dd if=", ":(){:|:&};:", "shutdown", "reboot",
    "halt", "poweroff", "init 0", "format ", "del /f /s /q C:",
]

def is_blocked(cmd):
    cmd_lower = cmd.lower().strip()
    for b in BLOCKED_COMMANDS:
        if b.lower() in cmd_lower:
            return True
    return False


class AVRHandler(BaseHTTPRequestHandler):
    """Handles all HTTP requests for the AVR Control Plane."""

    def log_message(self, format, *args):
        # Suppress default stderr logging — we print our own
        print(f"  [{self.client_address[0]}] {args[0]}")

    def _send(self, code, body, ctype="text/plain"):
        self.send_response(code)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body.encode(errors="replace"))

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        def p(key, default=""):
            return params.get(key, [default])[0]

        route = parsed.path

        # /ping — health check
        if route == "/ping":
            self._send(200, "pong")
            return

        # /avr — AVR build / flash
        if route == "/avr":
            action   = p("action", "flash")
            filename = p("filename", "")
            board    = p("board", "atmega8")
            port_dev = p("port", "")

            if not filename:
                self._send(400, "Error: No filename provided.")
                return

            try:
                if action == "elf":
                    _, output = generate_elf(filename, board)
                elif action == "hex":
                    _, output = generate_hex(filename, board)
                else:
                    _, output = flash_avr(filename, board, port_dev or None)
                self._send(200, output)
            except Exception as e:
                self._send(500, f"Internal error: {e}")
            return

        # /run — Raw shell command
        if route == "/run":
            cmd = p("command", "")
            if not cmd:
                self._send(400, "Error: No command provided.")
                return
            if is_blocked(cmd):
                self._send(403, "Error: Command blocked for safety.")
                return
            try:
                r = subprocess.run(
                    cmd, capture_output=True, text=True, shell=True,
                    timeout=30
                )
                output = r.stdout if r.stdout else r.stderr or "(no output)"
                self._send(200, output)
            except subprocess.TimeoutExpired:
                self._send(408, "Error: Command timed out (30s).")
            except Exception as e:
                self._send(500, f"Error: {e}")
            return

        # /about — system info
        if route == "/about":
            info = f"Platform: {get_platform()}\nPython: {sys.version}\nArch: {platform.machine()}\n"
            # Try fastfetch/neofetch
            for cmd_name in ["fastfetch", "neofetch"]:
                if shutil.which(cmd_name):
                    try:
                        r = subprocess.run([cmd_name], capture_output=True, text=True, timeout=5)
                        info += "\n" + (r.stdout or r.stderr)
                    except:
                        pass
                    break
            self._send(200, info)
            return

        # Static file serving (index.html, etc.)
        if route in ("/", "/index.html"):
            filepath = "index.html"
        else:
            filepath = route.lstrip("/")

        # Security: prevent directory traversal
        filepath = os.path.normpath(filepath)
        if filepath.startswith("..") or filepath.startswith("/"):
            self._send(403, "Forbidden")
            return

        if os.path.isfile(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    self._send(200, f.read(), "text/html")
            except:
                self._send(500, "Error reading file")
        else:
            self._send(404, f"404 — {filepath} not found")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    url = f"http://localhost:{PORT}"
    print(f"""
  ╔══════════════════════════════════════════╗
  ║       AVR CONTROL PLANE  v3.1            ║
  ║       Platform: {get_platform():<24s}║
  ║       URL: {url:<32s}║
  ╚══════════════════════════════════════════╝
    """)

    server = HTTPServer(("0.0.0.0", PORT), AVRHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    print(f"[Server] Running on {url}")

    # Handle Ctrl+C cleanly
    def shutdown(sig, frame):
        print("\n[Server] Shutting down...")
        server.shutdown()
        sys.exit(0)
    signal.signal(signal.SIGINT, shutdown)
    if sys.platform != "win32":
        signal.signal(signal.SIGTERM, shutdown)

    # Try PySide6 first, fall back to system browser
    print("[GUI] Attempting PySide6 window...")
    if not try_pyside6(url):
        print("[GUI] PySide6 not available — opening system browser...")
        open_browser(url)
        print(f"[GUI] Browser opened. Press Ctrl+C to stop server.")

    # Keep main thread alive (only needed if no PySide6)
    try:
        while True:
            signal.pause() if hasattr(signal, 'pause') else threading.Event().wait(timeout=1)
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    main()