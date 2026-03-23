from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_market_radar.models import RawDocument


DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MAX_RETRIES = 2
DEFAULT_PRICING_PER_1K_TOKENS = {
    "input": 0.0,
    "output": 0.0,
}


class LLMClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class LLMUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0


@dataclass(frozen=True)
class LLMExtractionResult:
    prompt_text: str
    raw_text: str
    payload: dict[str, Any]
    usage: LLMUsage
    latency_sec: float
    model: str
    provider: str = "openai-compatible"


def load_prompt_template() -> str:
    prompt_path = Path(__file__).parent / "prompts" / "event_extraction.txt"
    return prompt_path.read_text()


def render_event_extraction_prompt(raw_document: RawDocument, source_context: dict[str, Any]) -> str:
    template = load_prompt_template()
    service_hint = source_context.get("service_slug_hint") or source_context.get("service_slug") or "unknown"
    return template.format(
        service_hint=service_hint,
        source_type=source_context.get("source_type", "unknown"),
        source_url=raw_document.source_url,
        title=raw_document.title,
        published_at=raw_document.published_at or "unknown",
        raw_text=raw_document.raw_text,
    )


def parse_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise LLMClientError("Model response did not contain a JSON object.")
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise LLMClientError(f"Failed to parse JSON from model response: {exc}") from exc


def _estimate_cost(input_tokens: int, output_tokens: int) -> float:
    input_price = float(os.getenv("AI_MARKET_RADAR_LLM_INPUT_PRICE_PER_1K", DEFAULT_PRICING_PER_1K_TOKENS["input"]))
    output_price = float(os.getenv("AI_MARKET_RADAR_LLM_OUTPUT_PRICE_PER_1K", DEFAULT_PRICING_PER_1K_TOKENS["output"]))
    return round((input_tokens / 1000.0) * input_price + (output_tokens / 1000.0) * output_price, 6)


class OpenAICompatibleLLMClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        self.api_key = api_key or os.getenv("AI_MARKET_RADAR_LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("AI_MARKET_RADAR_LLM_MODEL")
        self.base_url = (base_url or os.getenv("AI_MARKET_RADAR_LLM_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        if not self.api_key:
            raise LLMClientError("Missing AI_MARKET_RADAR_LLM_API_KEY or OPENAI_API_KEY.")
        if not self.model:
            raise LLMClientError("Missing AI_MARKET_RADAR_LLM_MODEL.")

    def extract_event(self, raw_document: RawDocument, source_context: dict[str, Any]) -> LLMExtractionResult:
        prompt = render_event_extraction_prompt(raw_document, source_context)
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Return exactly one JSON object."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            started = time.monotonic()
            try:
                response = self._post_json("/chat/completions", body)
                latency_sec = time.monotonic() - started
                content = self._extract_content(response)
                payload = parse_json_object(content)
                usage = self._extract_usage(response)
                return LLMExtractionResult(
                    prompt_text=prompt,
                    raw_text=content,
                    payload=payload,
                    usage=usage,
                    latency_sec=latency_sec,
                    model=self.model,
                )
            except Exception as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(min(2**attempt, 5))
        raise LLMClientError(f"LLM extraction failed after retries: {last_error}")

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            url=f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            raise LLMClientError(f"HTTP {exc.code} from LLM API: {body}") from exc
        except urllib.error.URLError as exc:
            raise LLMClientError(f"Failed to reach LLM API: {exc}") from exc

    @staticmethod
    def _extract_content(response: dict[str, Any]) -> str:
        try:
            return response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMClientError("Unexpected LLM response shape: missing choices[0].message.content") from exc

    @staticmethod
    def _extract_usage(response: dict[str, Any]) -> LLMUsage:
        usage = response.get("usage") or {}
        input_tokens = int(usage.get("prompt_tokens") or 0)
        output_tokens = int(usage.get("completion_tokens") or 0)
        return LLMUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=_estimate_cost(input_tokens, output_tokens),
        )
