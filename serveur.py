"""Serveur EduCert pour les tests sur le même Wi-Fi.

Détecte l'IP réseau du PC et l'injecte dans index.html afin que les QR
générés depuis localhost soient accessibles depuis le téléphone.
"""
import http.server
import socket
from socketserver import ThreadingTCPServer

PORT = 8082


def detect_lan_ip():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


LAN_IP = detect_lan_ip()


class EduCertHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Injection uniquement pour la page principale ; les autres fichiers
        # (config.js, qr éventuels, etc.) restent servis normalement.
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html", "/diplomeV2QR-pdf2.html"):
            try:
                with open("index.html", "r", encoding="utf-8") as file:
                    html = file.read()
                marker = "window.EDUCERT_PUBLIC_ORIGIN = window.location.origin;"
                injected = f"window.EDUCERT_PUBLIC_ORIGIN = 'http://{LAN_IP}:{PORT}';"
                html = html.replace(marker, injected, 1)
                body = html.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            except OSError:
                pass
        super().do_GET()


if __name__ == "__main__":
    with ThreadingTCPServer(("0.0.0.0", PORT), EduCertHandler) as server:
        print("✅ Serveur EduCert démarré")
        print(f"👉 PC : http://localhost:{PORT}/")
        print(f"📱 QR : http://{LAN_IP}:{PORT}/diplomeV2QR-pdf2.html?id=...")
        print("Arrêt : Ctrl+C")
        server.serve_forever()
