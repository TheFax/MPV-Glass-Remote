import os
import sys
import json
import socket
import subprocess
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler


# Configuration file
CONFIG_FILE = 'config.json'


def load_config():
    # Check if config file exists
    if not os.path.exists(CONFIG_FILE):
        print(f"ERROR: Configuration file '{CONFIG_FILE}' not found.")
        sys.exit(1)

    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)

        if os.name == 'nt':
            required_keys = ["WINDOWS_media_dir", "allowed_extensions", "port", "WINDOWS_mpv_executable"]
        else:
            required_keys = ["LINUX_media_dir", "allowed_extensions", "port", "LINUX_mpv_executable"]

        missing = [key for key in required_keys if key not in config]

        if missing:
            print(f"ERROR: Missing keys in JSON: {', '.join(missing)}")
            sys.exit(1)

        if os.name == 'nt':
            config["media_dir"] = config["WINDOWS_media_dir"]
            config["mpv_executable"] = config["WINDOWS_mpv_executable"]
            config["ipc_socket"] = "\\\\.\\pipe\\mpvpipe"
            config["screenshot_file"] = ".\\mpv_screenshot.jpg"
        else:
            config["media_dir"] = config["LINUX_media_dir"]
            config["mpv_executable"] = config["LINUX_mpv_executable"]
            config["ipc_socket"] = "/tmp/mpv-socket"
            config["screenshot_file"] = "/tmp/mpv_screenshot.jpg"

        return config

    except json.JSONDecodeError as e:
        print(f"ERROR: '{CONFIG_FILE}' is not a valid JSON file.")
        print(f"Details: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Unexpected error while loading configuration: {e}")
        sys.exit(1)


# Initialize configuration
CONF = load_config()

# Configuration Shortcuts
MEDIA_DIR = CONF['media_dir']
ALLOWED_EXTENSIONS = set(CONF['allowed_extensions'])
PORT = CONF['port']
MPV_EXE = CONF['mpv_executable']
IPC_SOCKET = CONF['ipc_socket']
SCREENSHOT_TEMP = CONF['screenshot_file']


def send_mpv_command(command):
    msg = json.dumps({"command": command}) + "\n"
    # print(f"MPV command: {command}")
    try:
        if os.name == 'nt':
            # Implementazione specifica per Windows Named Pipes
            with open(IPC_SOCKET, 'r+b', buffering=0) as pipe:
                pipe.write(msg.encode())
                res = pipe.readline()
                # print(f"MPV res: {res}")
                return json.loads(res.decode())
        else:
            client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client.settimeout(0.2)
            client.connect(IPC_SOCKET)
            client.send(msg.encode())
            res = client.recv(4096)
            client.close()
            # print(f"MPV res: {res}")
            return json.loads(res.decode())
    except Exception as e:
        # print(f"\n[Socket Error] {e}")
        return {"offline": "offline"}


def old_send_mpv_command(command):
    client = None
    try:
        print(f"sendmpv: {command}")

        # Estrazione IP e porta dal config
        ip, port = IPC_SOCKET.split(':')

        # Creazione socket TCP
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(2)  # Timeout rapido: se non risponde subito, mpv è spento

        client.connect((ip, int(port)))

        msg = json.dumps({"command": command}) + "\n"
        client.send(msg.encode())

        res = client.recv(4096)
        print(res)
        return json.loads(res.decode())
    # except (ConnectionRefusedError, ConnectionAbortedError, socket.timeout, OSError):
    except Exception as e:
        # MPV non sta girando o la connessione è stata rifiutata
        print(f"\n[Socket Error] {e}")
        return {"error": "offline", "data": None}
    finally:
        if client:
            client.close()


class MPVRemoteHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        # Create standard log message
        message = format % args
        # Print \r at beginning of the line, in order to delete the previous log text.
        # end="" to terminate the string without a new line.
        # flush=True to update immediately the screen

        # print(f"\r[Realtime Log] {message}".ljust(80), end="", flush=True)

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(url.query)
        path = url.path

        # Index
        if path == "/" or path == "/index.html":
            self.serve_file('index.html', 'text/html')

        # Static files
        elif os.path.isfile(path.lstrip('/')):
            self.serve_file(path.lstrip('/'))

        # API: List Files
        elif path == "/api/files":
            req_path = params.get('path', [''])[0]
            full_path = os.path.normpath(os.path.join(MEDIA_DIR, req_path))

            if not os.path.exists(full_path):
                self.send_json([])
                return

            items = []
            current_folder_thumb = None
            if os.path.exists(os.path.join(full_path, "folder.jpg")):
                current_folder_thumb = f"/api/thumb?path={urllib.parse.quote(os.path.join(req_path, 'folder.jpg'))}"

            for entry in os.scandir(full_path):
                if entry.is_dir():
                    thumb = None
                    if os.path.exists(os.path.join(entry.path, "folder.jpg")):
                        rel = os.path.relpath(entry.path, MEDIA_DIR)
                        thumb = f"/api/thumb?path={urllib.parse.quote(os.path.join(rel, 'folder.jpg'))}"
                    items.append({
                        "name": entry.name, "is_dir": True,
                        "rel_path": os.path.relpath(entry.path, MEDIA_DIR), "thumb": thumb
                    })
                else:
                    ext = os.path.splitext(entry.name)[1].lower()
                    if ext in ALLOWED_EXTENSIONS:
                        items.append({
                            "name": entry.name, "is_dir": False,
                            "rel_path": os.path.relpath(entry.path, MEDIA_DIR), "thumb": None, "ext": ext
                        })

            self.send_json({
                "items": sorted(items, key=lambda x: (not x['is_dir'], x['name'])),
                "current_thumb": current_folder_thumb
            })

        # API: Thumbnail
        elif path == "/api/thumb":
            rel_path = params.get('path', [''])[0]
            full_path = os.path.abspath(os.path.join(MEDIA_DIR, rel_path))
            if os.path.exists(full_path) and full_path.startswith(os.path.abspath(MEDIA_DIR)):
                self.serve_file(full_path)
            else:
                self.send_error(404)

        # API: Status
        elif path == "/api/status":
            response = send_mpv_command(["get_property", "path"])

            # Se mpv è offline, restituiamo uno stato vuoto coerente
            if "offline" in response:
                status = {
                    "pos": 0, "duration": 0, "volume": 0,
                    "paused": True, "title": "MPV is offline",
                    "filename": "", "folder": "", "extension": ""
                }
            else:

                full_path = response.get("data", "")

                file_name = ""
                folder_rel = ""
                extension = ""

                if full_path:
                    # Extract the file name
                    file_name = os.path.basename(full_path)
                    # Extract the extension
                    extension = os.path.splitext(file_name)[1]
                    # Calcoliamo la cartella relativa rispetto a MEDIA_DIR
                    try:
                        # Rimuoviamo il prefisso MEDIA_DIR per avere solo la sottocartella
                        folder_rel = os.path.dirname(os.path.relpath(full_path, os.path.abspath(MEDIA_DIR)))
                        if folder_rel == ".":
                            folder_rel = ""
                    except:
                        folder_rel = ""

                status = {
                    "pos": send_mpv_command(["get_property", "time-pos"]).get("data", 0),
                    "duration": send_mpv_command(["get_property", "duration"]).get("data", 0),
                    "volume": send_mpv_command(["get_property", "volume"]).get("data", 100),
                    "paused": send_mpv_command(["get_property", "pause"]).get("data", False),
                    "title": send_mpv_command(["get_property", "media-title"]).get("data", "Select a file"),
                    "filename": file_name,
                    "folder": folder_rel,
                    "extension": extension
                }
            self.send_json(status)

        # API: Screenshot
        elif path == "/api/screenshot":
            response = send_mpv_command(["screenshot-to-file", SCREENSHOT_TEMP, "video"])

            if "offline" in response:
                self.serve_file("offline.jpg", 'image/jpeg')
            else:
                if os.path.exists(SCREENSHOT_TEMP):
                    self.serve_file(SCREENSHOT_TEMP, 'image/jpeg')
                else:
                    self.send_error(404)
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/api/control":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)

            cmd = data.get('cmd')
            params = data.get('params', [])

            if cmd == "play_file":
                file_path = os.path.abspath(os.path.join(MEDIA_DIR, params[0]))
                # Rileva se il sistema è Windows o Linux
                if os.name == 'nt':  # Windows
                    subprocess.run(["taskkill", "/F", "/IM", os.path.basename(MPV_EXE), "/T"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
                else:  # Linux/Unix
                    subprocess.run(["pkill", "-9", os.path.basename(MPV_EXE)])
                subprocess.Popen([MPV_EXE, f'--input-ipc-server={IPC_SOCKET}', '--idle', '--fullscreen', file_path])
                self.send_json({"status": "ok"})
            else:
                res = send_mpv_command([cmd] + params)
                self.send_json(res)

    def serve_file(self, file_path, content_type=None):
        try:
            with open(file_path, 'rb') as f:
                self.send_response(200)
                if content_type:
                    self.send_header('Content-type', content_type)
                self.end_headers()
                self.wfile.write(f.read())
        except:
            self.send_error(404)

    def send_json(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())


if __name__ == '__main__':
    if not os.path.exists(MEDIA_DIR):
        print("Media path doesn't exist.")
        sys.exit(1)

    # Recupero Hostname
    hostname = socket.gethostname()

    # Recupero IP Locale (metodo robusto che non richiede connessione internet attiva)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = "127.0.0.1"

    print(f"-------------------------")
    print(f"--- MPV Remote Server ---")
    print(f"-------------------------")
    print(f"Server started on:")
    print(f"   http://localhost:{PORT}")
    print(f"   http://{local_ip}:{PORT}")
    print(f"   http://{hostname}.local:{PORT}      (if mDNS is active)")
    print()

    httpd = HTTPServer(('0.0.0.0', PORT), MPVRemoteHandler)
    httpd.serve_forever()
