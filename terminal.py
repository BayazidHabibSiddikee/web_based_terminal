"""
AVR Control Plane — Backend Server
v3.5 — Bug fixes: global SERIAL_OBJ, time.sleep, createWindow, blocklist
"""

import os
import sys
import re
import time
import subprocess
import threading
import platform
import signal
import shutil
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# ── Graceful import of flash_avr with a helpful error ─────────────────────────
try:
    from flash_avr import flash_avr, generate_hex, generate_elf, get_platform, list_ports
except ImportError as _e:
    print(
        "\n[FATAL] Cannot import 'flash_avr'. "
        "Make sure flash_avr.py is in the same directory as terminal.py.\n"
        f"  Detail: {_e}\n"
    )
    sys.exit(1)

PORT = 8090

# ── Serial Monitor State ───────────────────────────────────────────────────────
SERIAL_BUFFER = []
SERIAL_OBJ    = None
SERIAL_THREAD = None
SERIAL_LOCK   = threading.Lock()


def serial_reader(port, baud):
    """Background thread: reads from serial port and fills SERIAL_BUFFER."""
    global SERIAL_OBJ
    import serial
    try:
        with serial.Serial(port, baud, timeout=0.1) as ser:
            SERIAL_OBJ = ser
            while SERIAL_OBJ is not None:          # FIX #4: explicit None check
                if ser.in_waiting:
                    data = ser.read(ser.in_waiting).decode(errors="replace")
                    with SERIAL_LOCK:
                        SERIAL_BUFFER.append(data)
                        if len(SERIAL_BUFFER) > 200:
                            SERIAL_BUFFER.pop(0)
                time.sleep(0.05)                   # FIX #4: use time.sleep, not Event().wait()
    except Exception as e:
        with SERIAL_LOCK:
            SERIAL_BUFFER.append(f"\n[SERIAL ERROR] {e}\n")
    finally:
        SERIAL_OBJ = None


def stop_serial():
    """Safely stop the serial reader thread from any context."""
    global SERIAL_OBJ                              # FIX #2: always declare global when writing
    SERIAL_OBJ = None


os.environ["QT_LOGGING_RULES"] = "qt.qpa.wayland=false"

# ── Signature → chip name map ──────────────────────────────────────────────────
SIGNATURE_MAP = {
    "1e9507": "ATmega8",     "1e9307": "ATmega8A",
    "1e9403": "ATmega16",    "1e940a": "ATmega16A",
    "1e9502": "ATmega32",    "1e9505": "ATmega32A",
    "1e950f": "ATmega328P",  "1e9506": "ATmega328PA",
    "1e9414": "ATmega328",
    "1e930a": "ATmega88",    "1e940f": "ATmega88P",
    "1e9411": "ATmega88PA",
    "1e9406": "ATmega168",   "1e940b": "ATmega168P",
    "1e9415": "ATmega168PA",
    "1e9602": "ATmega644",   "1e9609": "ATmega644P",
    "1e9702": "ATmega128",   "1e9703": "ATmega128A",
    "1e9801": "ATmega1280",  "1e9802": "ATmega2560",
    "1e930b": "ATtiny85",    "1e930c": "ATtiny84",
    "1e930d": "ATtiny44",    "1e9208": "ATtiny2313",
    "1e9007": "ATtiny13",    "1e9008": "ATtiny13A",
}


def identify_chip(sig_raw):
    sig = sig_raw.lower().replace(" ", "").replace("0x", "")
    if len(sig) >= 6:
        sig = sig[:6]
    return SIGNATURE_MAP.get(sig)


# ── Blocked command patterns (FIX #6: extended + regex-based) ─────────────────
# Patterns that should NEVER be executed via the raw terminal.
_BLOCKED_PATTERNS = [
    # Filesystem nukes
    r"rm\s+-[a-z]*r[a-z]*\s+-[a-z]*f[a-z]*\s+/",   # rm -rf /
    r"rm\s+-[a-z]*f[a-z]*\s+-[a-z]*r[a-z]*\s+/",   # rm -fr /
    r"rm\s+.*--no-preserve-root",
    r"rm\s+-rf\s+~",
    r"rm\s+-rf\s+\$HOME",
    # Disk/format wipes
    r"\bmkfs\b",
    r"\bdd\s+if=",
    r">\s*/dev/(s|h|v|xv)d[a-z]",                   # redirect into disk device
    # Fork bombs
    r":\(\)\{.*\|.*:.*&.*\}.*:",
    # Shutdown/reboot
    r"\b(shutdown|reboot|halt|poweroff|init\s+0)\b",
    # Windows format
    r"\bformat\s+[a-z]:",
    r"\bdel\s+/[fs]",
    # Pipe-download-execute
    r"(curl|wget).*\|\s*(ba)?sh",
    # Privilege escalation
    r"\bsudo\s+rm\b",
    r"\bsudo\s+dd\b",
    r"\bsudo\s+mkfs\b",
    r"\bsudo\s+shutdown\b",
    r"\bsudo\s+reboot\b",
]
_BLOCKED_RE = [re.compile(p, re.IGNORECASE) for p in _BLOCKED_PATTERNS]


def is_blocked(cmd: str) -> bool:
    return any(rx.search(cmd) for rx in _BLOCKED_RE)


# ── PySide6 GUI ────────────────────────────────────────────────────────────────
def try_pyside6(url):
    try:
        from PySide6.QtCore import QUrl, QSize
        from PySide6.QtGui import QPalette, QColor
        from PySide6.QtWidgets import QApplication, QMainWindow
        from PySide6.QtWebEngineWidgets import QWebEngineView
        from PySide6.QtWebEngineCore import QWebEngineSettings

        class CaptureWebView(QWebEngineView):
            def __init__(self, parent=None):
                super().__init__(parent)
                s = self.settings()
                s.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
                s.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
                s.setAttribute(QWebEngineSettings.JavascriptCanOpenWindows, False)

            def createWindow(self, wt, *a, **k):
                return None  # block all popups

        class AvrWindow(QMainWindow):
            def __init__(self, home_url):
                super().__init__()
                self.setWindowTitle("AVR Control Plane")
                self.setMinimumSize(QSize(900, 600))
                self.resize(1280, 820)

                self.browser = CaptureWebView()
                self.browser.setUrl(QUrl(home_url))
                self.setCentralWidget(self.browser)

                # Minimal status bar — shows load state only, no URL
                self.statusBar().setStyleSheet(
                    "QStatusBar{background:#0a0b10;color:#444;"
                    "font-family:'Courier New',monospace;font-size:11px;}"
                )
                self.statusBar().showMessage("AVR Control Plane  //  " + get_platform().upper())
                self.browser.loadStarted.connect(
                    lambda: self.statusBar().showMessage("Loading…")
                )
                self.browser.loadFinished.connect(
                    lambda ok: self.statusBar().showMessage(
                        "AVR Control Plane  //  " + get_platform().upper()
                    )
                )

        app = QApplication(sys.argv)
        app.setApplicationName("AVR Control Plane")
        pal = QPalette()
        pal.setColor(QPalette.Window,          QColor("#0a0b10"))
        pal.setColor(QPalette.WindowText,      QColor("#ccc"))
        pal.setColor(QPalette.Base,            QColor("#0a0b10"))
        pal.setColor(QPalette.AlternateBase,   QColor("#12131a"))
        pal.setColor(QPalette.Text,            QColor("#ccc"))
        pal.setColor(QPalette.Button,          QColor("#1a1b26"))
        pal.setColor(QPalette.ButtonText,      QColor("#7a7d9e"))
        pal.setColor(QPalette.Highlight,       QColor("#00d4ff"))
        pal.setColor(QPalette.HighlightedText, QColor("#000"))
        pal.setColor(QPalette.ToolTipBase,     QColor("#1a1b26"))
        pal.setColor(QPalette.ToolTipText,     QColor("#ccc"))
        pal.setColor(QPalette.PlaceholderText, QColor("#333"))
        app.setPalette(pal)
        w = AvrWindow(url); w.show()
        app.exec()
        return True
    except ImportError:
        return False
    except Exception as e:
        print(f"[PySide6] Failed: {e}")
        return False


def open_browser(url):
    plat = get_platform()
    try:
        if plat == "windows":
            os.startfile(url)
        elif plat == "mac":
            subprocess.Popen(["open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            for c in ["xdg-open", "sensible-browser", "firefox", "google-chrome"]:
                if shutil.which(c):
                    subprocess.Popen([c, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return
            print(f"[WARN] No browser found. Open manually: {url}")
    except Exception as e:
        print(f"[WARN] Could not open browser: {e}")


# ── HTTP Handler ───────────────────────────────────────────────────────────────
class AVRHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        if "/ping" not in str(args[0]):
            print(f"  [{self.client_address[0]}] {args[0]}")

    def _send(self, code, body, ctype="text/plain"):
        try:
            self.send_response(code)
            self.send_header("Content-Type", f"{ctype}; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body.encode(errors="replace"))
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        try:
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            def p(key, default=""):
                return params.get(key, [default])[0]
            route = parsed.path

            # ── /ping ──────────────────────────────────────────────────────────
            if route == "/ping":
                self._send(200, "pong"); return

            # ── /ports ─────────────────────────────────────────────────────────
            if route == "/ports":
                try:
                    ports = list_ports()
                    self._send(200, ",".join(ports))
                except Exception as e:
                    self._send(500, str(e))
                return

            # ── /serial ────────────────────────────────────────────────────────
            if route == "/serial":
                global SERIAL_THREAD, SERIAL_OBJ   # FIX #2: declare global at top of handler
                action = p("action", "read")
                port   = p("port", "")
                baud   = p("baud", "9600")

                if action == "start":
                    if SERIAL_OBJ:
                        self._send(200, "Already running")
                        return
                    if not port:
                        self._send(400, "No port provided")
                        return
                    SERIAL_THREAD = threading.Thread(
                        target=serial_reader, args=(port, int(baud)), daemon=True
                    )
                    SERIAL_THREAD.start()
                    self._send(200, "Started")
                    return

                if action == "stop":
                    stop_serial()              # FIX #2: use helper that correctly sets global
                    self._send(200, "Stopped")
                    return

                if action == "read":
                    with SERIAL_LOCK:
                        data = "".join(SERIAL_BUFFER)
                        SERIAL_BUFFER.clear()
                    self._send(200, data)
                    return

                self._send(400, "Invalid serial action")
                return

            # ── /avr ───────────────────────────────────────────────────────────
            if route == "/avr":
                action   = p("action", "flash")
                filename = p("filename", "")
                board    = p("board", "atmega8")
                port_dev = p("port", "")
                f_cpu    = p("f_cpu", "")
                prog_key = p("programmer", "")
                bitclock = p("bitclock", "")
                do_fuses = p("do_fuses", "0") == "1"

                if not filename and not do_fuses:
                    self._send(400, "Error: No filename provided."); return

                f_cpu_int = None
                if f_cpu:
                    try:
                        f_cpu_int = int(f_cpu)
                    except ValueError:
                        self._send(400, f"Error: Invalid F_CPU '{f_cpu}'. Use Hz."); return

                try:
                    if action == "elf":
                        _, output = generate_elf(filename, board, f_cpu_int)
                    elif action == "hex":
                        _, output = generate_hex(filename, board, f_cpu_int)
                    else:
                        # Stop serial monitor before flashing to free the port
                        stop_serial()          # FIX #2: use helper instead of bare assignment

                        _, output = flash_avr(
                            filename, board, port_dev or None, f_cpu_int,
                            prog_key  if prog_key  else None,
                            bitclock  if bitclock  else None,
                            do_fuses,
                        )

                    # Auto-detect chip from signature mismatch
                    if "Device signature =" in output and "expected signature for" in output:
                        sig_match = re.search(r'Device signature = ([0-9A-Fa-f ]+)', output)
                        if sig_match:
                            sig_raw  = sig_match.group(1).strip()
                            detected = identify_chip(sig_raw)
                            if detected:
                                output += (
                                    f"\n{'='*48}\n"
                                    f"[AUTO-DETECT] Real chip: {detected}\n"
                                    f"[AUTO-DETECT] Signature : {sig_raw}\n"
                                    f"[FIX] Select '{detected.lower()}' as TARGET_MCU"
                                )
                                if not prog_key or prog_key == "arduino":
                                    output += (
                                        f"\n[NOTE] The 'arduino' programmer talks to the Uno's\n"
                                        f"       onboard chip (ATmega328P), not an external chip.\n"
                                        f"       For external chips, use 'Arduino as ISP' as programmer\n"
                                        f"       and make sure the ArduinoISP sketch is uploaded.\n"
                                    )
                                output += f"{'='*48}"

                    self._send(200, output)
                except Exception as e:
                    self._send(500, f"Internal error: {e}")
                return

            # ── /run ───────────────────────────────────────────────────────────
            if route == "/run":
                cmd = p("command", "")
                if not cmd:
                    self._send(400, "Error: No command."); return
                if is_blocked(cmd):
                    self._send(403, "Error: Command blocked."); return
                try:
                    r = subprocess.run(
                        cmd, capture_output=True, text=True, shell=True, timeout=30
                    )
                    self._send(200, r.stdout if r.stdout else r.stderr or "(no output)")
                except subprocess.TimeoutExpired:
                    self._send(408, "Error: Timed out (30s).")
                except Exception as e:
                    self._send(500, f"Error: {e}")
                return

            # ── /about ─────────────────────────────────────────────────────────
            if route == "/about":
                info = (
                    f"Platform: {get_platform()}\n"
                    f"Python: {sys.version}\n"
                    f"Arch: {platform.machine()}\n"
                )
                for cn in ["fastfetch", "neofetch"]:
                    if shutil.which(cn):
                        try:
                            r = subprocess.run([cn], capture_output=True, text=True, timeout=5)
                            info += "\n" + (r.stdout or r.stderr)
                        except Exception:
                            pass
                        break
                self._send(200, info); return

            # ── Static files ───────────────────────────────────────────────────
            if route in ("/", "/index.html"):
                filepath = "index.html"
            else:
                filepath = route.lstrip("/")
            filepath = os.path.normpath(filepath)
            if filepath.startswith("..") or filepath.startswith("/"):
                self._send(403, "Forbidden"); return

            if os.path.isfile(filepath):
                try:
                    ext    = os.path.splitext(filepath)[1].lower()
                    binary = {
                        ".jpg", ".jpeg", ".png", ".gif",
                        ".mp4", ".mp3", ".avi", ".mkv", ".webm",
                        ".pdf", ".zip", ".hex", ".elf", ".bin",
                    }
                    if ext in binary:
                        with open(filepath, "rb") as f:
                            data = f.read()
                        mt = {
                            ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                            ".png": "image/png",  ".gif":  "image/gif",
                            ".mp4": "video/mp4",  ".webm": "video/webm",
                            ".mp3": "audio/mpeg", ".pdf":  "application/pdf",
                            ".zip": "application/zip",
                            ".hex": "text/plain",
                            ".elf": "application/octet-stream",
                            ".bin": "application/octet-stream",
                        }
                        try:
                            self.send_response(200)
                            self.send_header("Content-Type", mt.get(ext, "application/octet-stream"))
                            self.send_header("Content-Length", str(len(data)))
                            self.send_header("Access-Control-Allow-Origin", "*")
                            self.end_headers()
                            self.wfile.write(data)
                        except (BrokenPipeError, ConnectionResetError):
                            pass
                    else:
                        with open(filepath, "r", encoding="utf-8") as f:
                            self._send(200, f.read(), "text/html")
                except (BrokenPipeError, ConnectionResetError):
                    pass
                except Exception:
                    self._send(500, "Error reading file")
            else:
                self._send(404, f"404 — {filepath} not found")

        except (BrokenPipeError, ConnectionResetError):
            pass


# ── Entry point ────────────────────────────────────────────────────────────────
def main():
    url = f"http://localhost:{PORT}"
    print(f"""
  ╔══════════════════════════════════════════╗
  ║       AVR CONTROL PLANE  v3.5            ║
  ║       Platform: {get_platform():<24s}║
  ║       URL: {url:<32s}║
  ╚══════════════════════════════════════════╝
    """)
    server = HTTPServer(("0.0.0.0", PORT), AVRHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"[Server] Running on {url}")

    def shutdown(sig, frame):
        print("\n[Server] Shutting down...")
        server.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    if sys.platform != "win32":
        signal.signal(signal.SIGTERM, shutdown)

    print("[GUI] Attempting PySide6 window...")
    if not try_pyside6(url):
        print("[GUI] PySide6 not available — opening system browser...")
        open_browser(url)
        try:
            while True:
                if hasattr(signal, "pause"):
                    signal.pause()
                else:
                    threading.Event().wait(timeout=1)
        except (KeyboardInterrupt, SystemExit):
            pass


if __name__ == "__main__":
    main()
