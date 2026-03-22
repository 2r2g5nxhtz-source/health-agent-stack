#!/usr/bin/env python3
import json
from http.server import BaseHTTPRequestHandler, HTTPServer


class HealthWebhookHandler(BaseHTTPRequestHandler):
    def _send_json(self, status_code: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length) if content_length > 0 else b"{}"

        try:
            payload = json.loads(raw_body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send_json(400, {"ok": False, "error": "Invalid JSON"})
            return

        print("Received payload:", json.dumps(payload, ensure_ascii=True), flush=True)
        self._send_json(
            200,
            {
                "ok": True,
                "message": "Health payload accepted",
                "received": payload,
            },
        )

    def do_GET(self) -> None:
        self._send_json(
            200,
            {
                "ok": True,
                "message": "Local Health Agent webhook is running",
            },
        )

    def log_message(self, format: str, *args) -> None:
        return


def main() -> None:
    server = HTTPServer(("127.0.0.1", 8765), HealthWebhookHandler)
    print("Local Health Agent webhook listening on http://127.0.0.1:8765/", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
