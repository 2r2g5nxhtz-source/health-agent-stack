from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal, InvalidOperation
from datetime import date
from typing import Any

from ai_market_radar.decision import STATEFUL_EVENT_TYPES, STATELESS_EVENT_TYPES
from ai_market_radar.models import RejectedEventRecord, StructuredEventRecord


SUPPORTED_EVENT_CLASSES = {"fact", "deal", "credit", "signal", "info"}
EVENT_CLASS_BY_TYPE = {
    "discount": "deal",
    "credits": "credit",
    "price_up": "fact",
    "price_down": "fact",
    "new_model": "signal",
    "new_plan": "signal",
    "free_tier": "credit",
    "ltd": "deal",
    "launch": "info",
    "region_launch": "info",
    "context": "fact",
    "model_price": "fact",
    "rate_limit": "fact",
}
SUPPORTED_EVENT_TYPES = set(EVENT_CLASS_BY_TYPE)
SUPPORTED_CURRENCIES = {"USD", "EUR", "GBP", "CREDITS", "TOKENS", "MESSAGES", "RPM", "TPM"}


class ValidationError(Exception):
    def __init__(self, reason: str, details: dict[str, Any]) -> None:
        super().__init__(reason)
        self.reason = reason
        self.details = details


def _parse_decimal(value: Any, field_name: str) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise ValidationError("invalid_numeric", {"field": field_name, "value": value}) from exc


def _parse_date(value: Any, field_name: str) -> str | None:
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(str(value)).isoformat()
    except ValueError as exc:
        raise ValidationError("invalid_date", {"field": field_name, "value": value}) from exc


def _validate_required_string(payload: dict[str, Any], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("missing_required_field", {"field": field_name})
    return value.strip()


def _validate_confidence(value: Any) -> Decimal:
    confidence = _parse_decimal(value, "confidence")
    if confidence is None or confidence < Decimal("0") or confidence > Decimal("1"):
        raise ValidationError("invalid_confidence", {"field": "confidence", "value": value})
    return confidence


def validate_detector_payload(
    *,
    payload: dict[str, Any],
    raw_document_id: str,
    source_confidence: Decimal,
    valid_services: set[str],
    detector_version: str = "v1",
) -> StructuredEventRecord:
    service_slug = _validate_required_string(payload, "service").lower()
    if service_slug not in valid_services:
        raise ValidationError("unknown_service", {"service": service_slug})

    event_type = _validate_required_string(payload, "event_type")
    if event_type not in SUPPORTED_EVENT_TYPES:
        raise ValidationError("unsupported_event_type", {"event_type": event_type})

    event_class = _validate_required_string(payload, "event_class")
    if event_class not in SUPPORTED_EVENT_CLASSES:
        raise ValidationError("unsupported_event_class", {"event_class": event_class})
    expected_class = EVENT_CLASS_BY_TYPE[event_type]
    if event_class != expected_class:
        raise ValidationError(
            "event_class_mismatch",
            {"event_type": event_type, "event_class": event_class, "expected_class": expected_class},
        )

    title = _validate_required_string(payload, "title")
    source_url = _validate_required_string(payload, "source_url")
    confidence = _validate_confidence(payload.get("confidence"))
    old_value = _parse_decimal(payload.get("old_value"), "old_value")
    new_value = _parse_decimal(payload.get("new_value"), "new_value")
    start_date = _parse_date(payload.get("start_date"), "start_date")
    end_date = _parse_date(payload.get("end_date"), "end_date")

    currency = payload.get("currency")
    if currency is not None:
        if not isinstance(currency, str) or not currency.strip():
            raise ValidationError("invalid_currency", {"currency": currency})
        currency = currency.strip().upper()
        if currency not in SUPPORTED_CURRENCIES:
            raise ValidationError("unsupported_currency", {"currency": currency})

    if start_date and end_date and end_date < start_date:
        raise ValidationError("invalid_date_range", {"start_date": start_date, "end_date": end_date})

    if event_type in STATEFUL_EVENT_TYPES and new_value is None:
        raise ValidationError("missing_new_value", {"event_type": event_type})

    if event_type in {"price_up", "price_down"}:
        if old_value is not None and new_value is not None and old_value == new_value:
            raise ValidationError("price_values_equal", {"old_value": str(old_value), "new_value": str(new_value)})

    plan_name = payload.get("plan")
    model_name = payload.get("model")
    region = payload.get("region")
    description = payload.get("description")
    evidence = payload.get("evidence") or []
    if not isinstance(evidence, list):
        raise ValidationError("invalid_evidence", {"evidence": evidence})

    final_confidence = (confidence * Decimal("0.6")) + (source_confidence * Decimal("0.4"))

    return StructuredEventRecord(
        id="",
        raw_document_id=raw_document_id,
        service_slug=service_slug,
        event_type=event_type,
        event_class=event_class,
        title=title,
        description=description.strip() if isinstance(description, str) and description.strip() else None,
        plan_name=plan_name.strip() if isinstance(plan_name, str) and plan_name.strip() else None,
        model_name=model_name.strip() if isinstance(model_name, str) and model_name.strip() else None,
        region=region.strip() if isinstance(region, str) and region.strip() else None,
        old_value=old_value,
        new_value=new_value,
        currency=currency,
        start_date=start_date,
        end_date=end_date,
        source_url=source_url,
        gpt_confidence=confidence,
        source_confidence=source_confidence,
        final_confidence=final_confidence,
        evidence=[str(item) for item in evidence],
        detector_version=detector_version,
    )


def build_rejected_event(
    *,
    raw_document_id: str,
    payload: dict[str, Any],
    error: ValidationError,
) -> RejectedEventRecord:
    service_value = payload.get("service")
    source_url = payload.get("source_url")
    return RejectedEventRecord(
        raw_document_id=raw_document_id,
        service_slug=service_value.lower() if isinstance(service_value, str) else None,
        source_url=source_url if isinstance(source_url, str) else None,
        rejection_reason=error.reason,
        rejection_details=error.details,
    )
