import socket
import os
import subprocess
import urllib.parse

# Import AVR helpers (must live in same folder as main.py)
from flash_avr import flash_avr, generate_hex, generate_elf

# ── Socket setup ───────────────────────────────────────────────────────────────
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

port = 8090
server_socket.bind(("0.0.0.0", port))
server_socket.listen(5)
print(f"Server started! Visit http://localhost:{port}")

# ── Helpers ────────────────────────────────────────────────────────────────────
def read_file(filename):
    """Return file contents or a 404 response string."""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return True, f.read()
    except FileNotFoundError:
        return False, f"<h1>404 – {filename} Not Found</h1>"

def http_ok(body, content_type="text/html"):
    return f"HTTP/1.1 200 OK\r\nContent-Type: {content_type}; charset=utf-8\r\n\r\n{body}"

def http_404(body="Not Found"):
    return f"HTTP/1.1 404 Not Found\r\nContent-Type: text/html\r\n\r\n{body}"

def http_405():
    return "HTTP/1.1 405 Method Not Allowed\r\nAllow: GET\r\n\r\n"

# ── Main loop ──────────────────────────────────────────────────────────────────
while True:
    try:
        client_socket, client_address = server_socket.accept()
        request = client_socket.recv(4096).decode(errors="replace")

        if not request:
            client_socket.close()
            continue

        print(f"\n[{client_address[0]}] {request.splitlines()[0]}")

        parts = request.split('\n')[0].split()
        if len(parts) < 2:
            client_socket.close()
            continue

        method = parts[0]
        path   = parts[1]

        if method != "GET":
            client_socket.sendall(http_405().encode())
            client_socket.close()
            continue

        # Parse query params once
        parsed = urllib.parse.urlparse(path)
        params = urllib.parse.parse_qs(parsed.query)
        def p(key, default=""):
            return params.get(key, [default])[0]

        # ── /avr  →  AVR build / flash ────────────────────────────────────────
        if parsed.path == "/avr":
            action   = p("action", "flash")
            filename = p("filename")
            board    = p("board", "atmega8")
            port_dev = p("port")          # empty = auto-detect inside flash_avr

            if not filename:
                output = "Error: No filename provided."
                ok = False
            elif action == "elf":
                ok, output = generate_elf(filename, board)
            elif action == "hex":
                ok, output = generate_hex(filename, board)
            else:  # flash
                ok, output = flash_avr(filename, board, port_dev)

            response = http_ok(output, "text/plain")

        # ── /run  →  Raw shell command ─────────────────────────────────────────
        elif parsed.path == "/run":
            cmd = p("command")
            if cmd:
                result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
                output = result.stdout if result.stdout else result.stderr or "(no output)"
            else:
                output = "Error: No command provided."
            response = http_ok(output, "text/plain")

        # ── / or /index.html ──────────────────────────────────────────────────
        elif parsed.path in ("/", "/index.html"):
            ok, content = read_file("index.html")
            response = http_ok(content) if ok else http_404(content)

        # ── /about ────────────────────────────────────────────────────────────
        elif parsed.path == "/about":
            r = subprocess.run(["fastfetch"], capture_output=True, text=True, shell=True)
            body = ("<h1>About</h1>"
                    "<p>Created by <a href='index.html'>Discipline@Fedora</a></p>"
                    f"<pre>{r.stdout or r.stderr}</pre>")
            response = http_ok(body)

        # ── Static file fallback ───────────────────────────────────────────────
        else:
            filename = parsed.path.lstrip("/")
            ok, content = read_file(filename)
            response = http_ok(content) if ok else http_404(content)

        client_socket.sendall(response.encode(errors="replace"))
        client_socket.close()

    except BlockingIOError:
        continue
    except Exception as e:
        print(f"[Server Error] {e}")
        try:
            client_socket.close()
        except:
            pass