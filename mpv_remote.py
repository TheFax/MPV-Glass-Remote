import os
import json
import socket
import subprocess
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler


MEDIA_DIR = "./media"


ALLOWED_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.m4v', '.mp3', '.flac'}
IPC_SOCKET = "/tmp/mpv-socket"
PORT = 5000


def send_mpv_command(command):
    try:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.settimeout(0.2)
        client.connect(IPC_SOCKET)
        msg = json.dumps({"command": command}) + "\n"
        client.send(msg.encode())
        res = client.recv(4096)
        client.close()
        return json.loads(res.decode())
    except:
        return {"error": "offline"}


class MPVRemoteHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        # Crea il messaggio di log standard
        message = format % args
        # Stampa con \r all'inizio per tornare a inizio riga, 
        # end="" per non andare a capo e flush=True per aggiornare subito
        print(f"\r[Realtime Log] {message}".ljust(80), end="", flush=True)

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
            # Full path of the file currently playing
            full_path = send_mpv_command(["get_property", "path"]).get("data", "")

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
            temp_img = "/tmp/mpv_thumb.jpg"
            send_mpv_command(["screenshot-to-file", temp_img, "video"])
            if os.path.exists(temp_img):
                self.serve_file(temp_img, 'image/jpeg')
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
                subprocess.run(["pkill", "-9", "mpv"])
                subprocess.Popen(['mpv', f'--input-ipc-server={IPC_SOCKET}', '--idle', '--fullscreen', file_path])
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
        quit()
    
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