import socket
import os
import subprocess
import urllib.parse

# Step 1: Create socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Step 2: Set socket options
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

port = 8090

# Step 3: Bind
server_socket.bind(("0.0.0.0", port))

# Step 4: Listen
server_socket.listen(5)
print(f"Server started! Visit http://localhost:{port}")

# Step 5: Accept and respond
while True:
    try:
        client_socket, client_address = server_socket.accept()
        request = client_socket.recv(1500).decode()

        print(f"Client address {client_address}:\n{request}")

        headers = request.split('\n')
        first_header_components = headers[0].split()

        # Guard against malformed/empty requests
        if len(first_header_components) < 2:
            client_socket.close()
            continue

        http_method = first_header_components[0]
        path = first_header_components[1]

        if http_method == "GET":

            # ── Route: /run?command=xxx → web terminal ──────────────────────
            if path.startswith("/run"):
                query = urllib.parse.urlparse(path).query
                params = urllib.parse.parse_qs(query)
                #print(params)
                cmd = params.get("command", [""])[0]

                if cmd:
                    #result = subprocess.run(f"xdg-open {cmd}")
                    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
                    output = result.stdout if result.stdout else result.stderr
                else:
                    output = "No command provided."

                body = f"<h1>Command Output</h1><pre>{output}</pre>"
                body += "<br><a href='/'>Back to Home</a>"
                response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n" + body

            # ── Route: / or /motivational_page.html → main page ────────────
            elif path == "/" or path == "/motivational_page.html":
                filename = "motivational_page.html"
                try:
                    with open(filename, "r") as f:
                        content = f.read()
                    response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n" + content
                except FileNotFoundError:
                    response = "HTTP/1.1 404 Not Found\r\nContent-Type: text/html\r\n\r\n<h1>404 - File Not Found</h1>"

            elif path == "/index.html":
                filename = "index.html"
                try:
                    with open(filename, "r") as f:
                        content = f.read()
                    response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n" + content
                except FileNotFoundError:
                    response = "HTTP/1.1 404 Not Found\r\nContent-Type: text/html\r\n\r\n<h1>404 - File Not Found</h1>"

            # ── Route: /about → system info via fastfetch ───────────────────
            elif path == "/about":
                r = subprocess.run(["fastfetch"], capture_output=True, text=True, shell=True)
                body = (
                    "<h1>About Page</h1>"
                    "<p>Created by <a href='index.html'>Discipline@Fedora</a></p>"
                    f"<pre>{r.stdout if r.stdout else r.stderr}</pre>"
                )
                response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n" + body

            # ── Fallback: try serving file by name ──────────────────────────
            else:
                filename = path.lstrip("/")
                try:
                    with open(filename, "r") as f:
                        content = f.read()
                    response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n" + content
                except FileNotFoundError:
                    response = "HTTP/1.1 404 Not Found\r\nContent-Type: text/html\r\n\r\n<h1>404 - File Not Found</h1>"

        else:
            response = "HTTP/1.1 405 Method Not Allowed\r\nAllow: GET\r\n\r\n"

        client_socket.sendall(response.encode())
        client_socket.close()

    except BlockingIOError:
        continue
    except Exception as e:
        print(f"Error: {e}")