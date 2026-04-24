import sys
import socket
import subprocess
import urllib.parse
import threading

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWidgets import QMainWindow

from flash_avr import flash_avr, generate_hex, generate_elf


# ── Browser window ─────────────────────────────────────────────────────────────
class BrowserWindow(QMainWindow):
    def __init__(self, url="http://localhost:8090"):
        super().__init__()
        self.setWindowTitle("Bayazid HS 53 — AVR Control Plane")
        self.browser = QWebEngineView()

        # Allow local file access and JS (needed for fetch() calls to localhost)
        settings = self.browser.settings()
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)

        self.browser.setUrl(QUrl(url))
        self.setCentralWidget(self.browser)
        self.showMaximized()


# ── HTTP Server ────────────────────────────────────────────────────────────────
class AVRServer:
    PORT = 8090

    def __init__(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(("0.0.0.0", self.PORT))
        self.server_socket.listen(5)
        print(f"[Server] Started → http://localhost:{self.PORT}")

    # ── Response helpers ───────────────────────────────────────────────────────
    @staticmethod
    def read_file(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return True, f.read()
        except FileNotFoundError:
            return False, f"<h1>404 – {filename} Not Found</h1>"

    @staticmethod
    def http_ok(body, content_type="text/html"):
        return f"HTTP/1.1 200 OK\r\nContent-Type: {content_type}; charset=utf-8\r\n\r\n{body}"

    @staticmethod
    def http_404(body="Not Found"):
        return f"HTTP/1.1 404 Not Found\r\nContent-Type: text/html\r\n\r\n{body}"

    @staticmethod
    def http_405():
        return "HTTP/1.1 405 Method Not Allowed\r\nAllow: GET\r\n\r\n"

    # ── Request handler (called per connection) ────────────────────────────────
    def handle(self, client_socket, client_address):
        try:
            request = client_socket.recv(4096).decode(errors="replace")
            if not request:
                return

            first_line = request.splitlines()[0]
            print(f"[{client_address[0]}] {first_line}")

            parts = first_line.split()
            if len(parts) < 2:
                return

            method, path = parts[0], parts[1]

            if method != "GET":
                client_socket.sendall(self.http_405().encode())
                return

            parsed = urllib.parse.urlparse(path)
            params = urllib.parse.parse_qs(parsed.query)

            def p(key, default=""):
                return params.get(key, [default])[0]

            route = parsed.path

            # /avr → AVR build / flash ─────────────────────────────────────────
            if route == "/avr":
                action   = p("action", "flash")
                filename = p("filename")
                board    = p("board", "atmega8")
                port_dev = p("port")

                if not filename:
                    output = "Error: No filename provided."
                elif action == "elf":
                    _, output = generate_elf(filename, board)
                elif action == "hex":
                    _, output = generate_hex(filename, board)
                else:
                    _, output = flash_avr(filename, board, port_dev)

                response = self.http_ok(output, "text/plain")

            # /run → Raw shell command ─────────────────────────────────────────
            elif route == "/run":
                cmd = p("command")
                if cmd:
                    r = subprocess.run(cmd, capture_output=True, text=True, shell=True)
                    output = r.stdout if r.stdout else r.stderr or "(no output)"
                else:
                    output = "Error: No command provided."
                response = self.http_ok(output, "text/plain")

            # / or /index.html ────────────────────────────────────────────────
            elif route in ("/", "/index.html"):
                ok, content = self.read_file("index.html")
                response = self.http_ok(content) if ok else self.http_404(content)

            # /about ──────────────────────────────────────────────────────────
            elif route == "/about":
                r = subprocess.run(["fastfetch"], capture_output=True, text=True, shell=True)
                body = ("<h1>About</h1>"
                        "<p>Created by <a href='index.html'>Discipline@Fedora</a></p>"
                        f"<pre>{r.stdout or r.stderr}</pre>")
                response = self.http_ok(body)

            # Static file fallback ─────────────────────────────────────────────
            else:
                fname = route.lstrip("/")
                ok, content = self.read_file(fname)
                response = self.http_ok(content) if ok else self.http_404(content)

            client_socket.sendall(response.encode(errors="replace"))

        except Exception as e:
            print(f"[Handler Error] {e}")
        finally:
            client_socket.close()

    # ── Main server loop (runs in background thread) ───────────────────────────
    def serve_forever(self):
        while True:
            try:
                client_socket, client_address = self.server_socket.accept()
                # Each request in its own thread so slow commands don't block
                t = threading.Thread(
                    target=self.handle,
                    args=(client_socket, client_address),
                    daemon=True
                )
                t.start()
            except Exception as e:
                print(f"[Accept Error] {e}")


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # 1. Start the HTTP server in a daemon thread
    server = AVRServer()
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    # 2. Start the Qt application in the main thread
    app = QApplication(sys.argv)
    QApplication.setApplicationName("Bayazid HS 53")

    window = BrowserWindow("http://localhost:8090")

    # App exits cleanly when the window is closed (daemon thread dies with it)
    sys.exit(app.exec())