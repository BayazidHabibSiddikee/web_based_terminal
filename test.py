import socket
import subprocess
import urllib.parse  # Built-in tool to clean up URL text

# ... (Socket setup code from before) ...

while True:
    try:
        client_socket, client_address = server_socket.accept()
        request = client_socket.recv(1500).decode()
        if not request: continue

        first_line = request.split('\n')[0]
        path = first_line.split()[1]

        if path.startswith("/run"):
            # 1. Extract the command from the URL
            # The path looks like: /run?command=ls
            query = urllib.parse.urlparse(path).query
            params = urllib.parse.parse_qs(query)
            cmd = params.get("command", [""])[0] # Get 'ls'

            if cmd:
                # 2. Run the command safely (using shell=True for things like fastfetch)
                # Warning: shell=True is dangerous if this was public!
                result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
                output = result.stdout if result.stdout else result.stderr
            else:
                output = "No command provided."

            # 3. Build the response
            body = f"<h1>Command Output</h1><pre>{output}</pre>"
            body += "<br><a href='/'>Back to Home</a>"
            response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n" + body

        elif path == "/" or path == "/index.html":
            with open("index.html", "r") as f:
                response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n" + f.read()
        
        else:
            response = "HTTP/1.1 404 NOT FOUND\r\n\r\nPage not found."

        client_socket.sendall(response.encode())
        client_socket.close()

    except Exception as e:
        print(f"Error: {e}")