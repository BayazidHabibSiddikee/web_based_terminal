import socket
import os, subprocess, urllib.parse

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
            # Route: / or /motivational_page.html → main page
            if path == "/" or path == "/motivational_page.html":
                filename = "motivational_page.html"

            # Route: /index.html → secondary page
            elif path == "/index.html":
                filename = "index.html"

            # Route: /about → inline HTML response
            elif path == "/about":
                r = subprocess.run(["fastfetch"],capture_output=True, text=True, shell=True)
                body = f"<h1>About Page</h1><footer><p>Created by <a href='index.html'>Discipline@Fedora</a></p></footer>"
                response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n" + body + f"<footer>{r.stdout}</footer>"
                client_socket.sendall(response.encode())
                client_socket.close()
                continue

            else:
                # Strip leading slash and serve the file if it exists
                filename = path.lstrip("/")

            # Try to open and serve the file
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