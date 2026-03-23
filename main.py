from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_API_BASE = os.getenv("GEMINI_API_BASE", "https://generativelanguage.googleapis.com/v1beta")


class ApiError(RuntimeError):
    pass


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload).encode("utf-8")


def _extract_prompt(payload: dict[str, Any]) -> str:
    prompt = payload.get("prompt")
    if isinstance(prompt, str) and prompt.strip():
        return prompt.strip()

    messages = payload.get("messages")
    if not isinstance(messages, list):
        raise ApiError("Request must include `prompt` or `messages`.")

    parts: list[str] = []
    for item in messages:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "user"))
        content = item.get("content", "")
        if isinstance(content, list):
            text_chunks = []
            for chunk in content:
                if isinstance(chunk, dict) and chunk.get("type") == "text":
                    text = chunk.get("text")
                    if isinstance(text, str) and text:
                        text_chunks.append(text)
            content = "\n".join(text_chunks)
        if isinstance(content, str) and content.strip():
            parts.append(f"{role}: {content.strip()}")

    if not parts:
        raise ApiError("Unable to extract prompt text from `messages`.")
    return "\n".join(parts)


def _gemini_generate(prompt: str, model: str) -> dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ApiError("Missing GEMINI_API_KEY.")

    url = f"{GEMINI_API_BASE}/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt,
                    }
                ]
            }
        ]
    }
    request = urllib.request.Request(
        url=url,
        data=_json_bytes(payload),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise ApiError(f"Gemini API returned HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise ApiError(f"Gemini API is unreachable: {exc}") from exc


def _extract_text(response_payload: dict[str, Any]) -> str:
    candidates = response_payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ApiError("Gemini response did not include candidates.")

    candidate = candidates[0]
    content = candidate.get("content", {})
    parts = content.get("parts", [])
    if not isinstance(parts, list):
        raise ApiError("Gemini response did not include content parts.")

    texts = []
    for part in parts:
        if isinstance(part, dict):
            text = part.get("text")
            if isinstance(text, str) and text:
                texts.append(text)

    if not texts:
        raise ApiError("Gemini response did not include text output.")
    return "\n".join(texts).strip()


class GeminiHandler(BaseHTTPRequestHandler):
    server_version = "GeminiRailwayAPI/1.0"

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = _json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ApiError(f"Invalid JSON body: {exc}") from exc
        if not isinstance(payload, dict):
            raise ApiError("JSON body must be an object.")
        return payload

    def log_message(self, format: str, *args: object) -> None:
        print(format % args)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._send_json({}, status=HTTPStatus.NO_CONTENT)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in {"/", "/health", "/healthz"}:
            self._send_json(
                {
                    "status": "ok",
                    "service": "gemini-railway-api",
                    "model": DEFAULT_MODEL,
                }
            )
            return

        if self.path == "/v1/models":
            self._send_json(
                {
                    "object": "list",
                    "data": [
                        {
                            "id": DEFAULT_MODEL,
                            "object": "model",
                            "owned_by": "google",
                        }
                    ],
                }
            )
            return

        self._send_json({"error": {"message": f"Path not found: {self.path}"}}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        started = time.time()
        try:
            payload = self._read_json()
            if self.path == "/v1/generate":
                model = str(payload.get("model") or DEFAULT_MODEL)
                prompt = _extract_prompt(payload)
                raw_response = _gemini_generate(prompt, model)
                text = _extract_text(raw_response)
                self._send_json(
                    {
                        "model": model,
                        "text": text,
                        "raw": raw_response,
                    }
                )
                return

            if self.path == "/v1/chat/completions":
                model = str(payload.get("model") or DEFAULT_MODEL)
                prompt = _extract_prompt(payload)
                raw_response = _gemini_generate(prompt, model)
                text = _extract_text(raw_response)
                now = int(time.time())
                self._send_json(
                    {
                        "id": f"chatcmpl-{now}",
                        "object": "chat.completion",
                        "created": now,
                        "model": model,
                        "choices": [
                            {
                                "index": 0,
                                "message": {"role": "assistant", "content": text},
                                "finish_reason": "stop",
                            }
                        ],
                        "usage": {
                            "prompt_tokens": 0,
                            "completion_tokens": 0,
                            "total_tokens": 0,
                        },
                        "provider": "gemini",
                        "latency_ms": int((time.time() - started) * 1000),
                        "raw": raw_response,
                    }
                )
                return

            self._send_json(
                {"error": {"message": f"Path not found: {self.path}"}},
                status=HTTPStatus.NOT_FOUND,
            )
        except ApiError as exc:
            self._send_json({"error": {"message": str(exc)}}, status=HTTPStatus.BAD_REQUEST)
        except Exception as exc:  # pragma: no cover
            self._send_json({"error": {"message": f"Internal server error: {exc}"}}, status=HTTPStatus.INTERNAL_SERVER_ERROR)


def main() -> None:
    port = int(os.getenv("PORT", "8080"))
    host = os.getenv("HOST", "0.0.0.0")
    server = ThreadingHTTPServer((host, port), GeminiHandler)
    print(f"Gemini Railway API listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
