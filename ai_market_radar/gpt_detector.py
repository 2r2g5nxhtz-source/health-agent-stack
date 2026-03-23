from __future__ import annotations

import json
import uuid
from dataclasses import replace
from decimal import Decimal
from typing import Any

from ai_market_radar.models import RawDocument, RejectedEventRecord, StructuredEventRecord
from ai_market_radar.normalizer import normalize_structured_event
from ai_market_radar.sanity import SanityError, build_rejected_sanity_event, run_sanity_checks
from ai_market_radar.validator import ValidationError, build_rejected_event, validate_detector_payload


SOURCE_CONFIDENCE_BY_TYPE = {
    "official": Decimal("0.90"),
    "pricing": Decimal("0.95"),
    "marketplace": Decimal("0.85"),
    "launch": Decimal("0.75"),
    "community": Decimal("0.60"),
    "social": Decimal("0.50"),
}


def detector_prompt(raw_document: RawDocument, service_slug_hint: str | None = None) -> str:
    service_hint_text = service_slug_hint or "unknown"
    return (
        "Extract a single market event as strict JSON.\n"
        "Return only JSON with fields: service, event_type, event_class, title, description, "
        "old_value, new_value, currency, plan, region, model, start_date, end_date, "
        "source_url, confidence, evidence.\n"
        f"Service hint: {service_hint_text}\n"
        f"Source URL: {raw_document.source_url}\n"
        f"Title: {raw_document.title}\n"
        f"Body:\n{raw_document.raw_text}\n"
    )


def ingest_detector_output(
    *,
    raw_document: RawDocument,
    detector_output: str | dict[str, Any],
    source_type: str,
    valid_services: set[str],
    detector_version: str = "v1",
) -> tuple[StructuredEventRecord | None, RejectedEventRecord | None]:
    if isinstance(detector_output, str):
        try:
            payload = json.loads(detector_output)
        except json.JSONDecodeError as exc:
            return None, RejectedEventRecord(
                raw_document_id=raw_document.id,
                service_slug=None,
                source_url=raw_document.source_url,
                rejection_reason="invalid_json",
                rejection_details={"error": str(exc)},
            )
    else:
        payload = detector_output

    source_confidence = SOURCE_CONFIDENCE_BY_TYPE.get(source_type, Decimal("0.50"))

    try:
        structured = validate_detector_payload(
            payload=payload,
            raw_document_id=raw_document.id,
            source_confidence=source_confidence,
            valid_services=valid_services,
            detector_version=detector_version,
        )
    except ValidationError as error:
        return None, build_rejected_event(raw_document_id=raw_document.id, payload=payload, error=error)

    try:
        structured = run_sanity_checks(structured)
    except SanityError as error:
        return None, build_rejected_sanity_event(structured, error)

    structured = normalize_structured_event(structured)
    return replace(structured, id=str(uuid.uuid4())), None
