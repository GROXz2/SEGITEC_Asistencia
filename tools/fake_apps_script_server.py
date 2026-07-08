"""Small local HTTP server that simulates a Google Apps Script endpoint."""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class FakeAppsScriptHandler(BaseHTTPRequestHandler):
    received_marks: list[dict] = []

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API.
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length)
        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"ok": false, "error": "invalid json"}')
            return

        FakeAppsScriptHandler.received_marks.append(payload)
        print(f"fake-apps-script payload recibido: {json.dumps(payload, ensure_ascii=False, sort_keys=True)}")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"ok": True, "received": len(FakeAppsScriptHandler.received_marks)}).encode("utf-8"))

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - inherited signature.
        print(f"fake-apps-script: {format % args}")


def run(host: str, port: int) -> None:
    server = ThreadingHTTPServer((host, port), FakeAppsScriptHandler)
    print(f"Fake Apps Script escuchando en http://{host}:{port}/exec")
    server.serve_forever()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Servidor falso de Google Apps Script")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(args.host, args.port)
