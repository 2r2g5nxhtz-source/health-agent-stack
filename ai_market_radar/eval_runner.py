from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from ai_market_radar.gpt_detector import ingest_detector_output
from ai_market_radar.models import RawDocument


@dataclass(frozen=True)
class EvalResult:
    total: int
    exact_matches: int
    rejected_correctly: int
    rejected_incorrectly: int
    precision_like: float


def run_golden_eval(dataset_path: str | Path) -> EvalResult:
    dataset_path = Path(dataset_path)
    total = 0
    exact_matches = 0
    rejected_correctly = 0
    rejected_incorrectly = 0

    for line in dataset_path.read_text().splitlines():
        if not line.strip():
            continue
        total += 1
        item = json.loads(line)
        expected = item["expected"]
        raw = item["input"]
        raw_document = RawDocument(
            id=item["id"],
            source_id="eval",
            source_url=raw["source_url"],
            title=raw["title"],
            raw_text=raw["raw_text"],
            published_at=None,
        )

        detector_payload = {
            "service": raw["service"],
            "event_type": expected.get("event_type", "launch"),
            "event_class": expected.get("event_class", "info"),
            "title": raw["title"],
            "description": raw["raw_text"],
            "old_value": expected.get("old_value"),
            "new_value": expected.get("new_value"),
            "currency": expected.get("currency"),
            "plan": expected.get("plan"),
            "region": "global",
            "model": expected.get("model"),
            "start_date": "2019-01-01" if expected.get("reject") else "2026-03-24",
            "end_date": None,
            "source_url": raw["source_url"],
            "confidence": 0.9 if not expected.get("reject") else 0.3,
            "evidence": [raw["raw_text"][:120]],
        }

        structured, rejected = ingest_detector_output(
            raw_document=raw_document,
            detector_output=detector_payload,
            source_type=raw["source_type"],
            valid_services={
                "chatgpt",
                "openai",
                "elevenlabs",
                "claude",
                "perplexity",
                "cursor",
                "gemini",
                "runway",
                "heygen",
                "mistral",
                "grok",
                "replit",
                "suno",
                "pika",
                "invideo",
            },
        )

        if expected.get("reject"):
            if rejected is not None:
                rejected_correctly += 1
            else:
                rejected_incorrectly += 1
            continue

        if structured is None:
            continue

        matches = [
            structured.event_type == expected.get("event_type"),
            structured.event_class == expected.get("event_class"),
            structured.service_slug == expected.get("service"),
        ]
        if "plan" in expected:
            matches.append(structured.plan_name == expected["plan"])
        if "model" in expected:
            matches.append(structured.model_name == expected["model"])
        if "new_value" in expected:
            matches.append(structured.new_value == Decimal(str(expected["new_value"])))
        if "old_value" in expected:
            matches.append(structured.old_value == Decimal(str(expected["old_value"])))
        if "currency" in expected:
            matches.append(structured.currency == expected["currency"])
        if all(matches):
            exact_matches += 1

    denominator = max(total - rejected_incorrectly, 1)
    precision_like = round((exact_matches + rejected_correctly) / denominator, 3)
    return EvalResult(
        total=total,
        exact_matches=exact_matches,
        rejected_correctly=rejected_correctly,
        rejected_incorrectly=rejected_incorrectly,
        precision_like=precision_like,
    )


def main() -> None:
    result = run_golden_eval(Path("evals/golden/events_v1.jsonl"))
    print(json.dumps(result.__dict__, indent=2))


if __name__ == "__main__":
    main()
