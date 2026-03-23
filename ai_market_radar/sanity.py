from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal
from typing import Any

from ai_market_radar.models import RejectedEventRecord, StructuredEventRecord


class SanityError(Exception):
    def __init__(self, reason: str, details: dict[str, Any]) -> None:
        super().__init__(reason)
        self.reason = reason
        self.details = details


def run_sanity_checks(event: StructuredEventRecord) -> StructuredEventRecord:
    if event.gpt_confidence < Decimal("0") or event.gpt_confidence > Decimal("1"):
        raise SanityError("invalid_confidence_range", {"confidence": str(event.gpt_confidence)})

    if event.final_confidence < Decimal("0") or event.final_confidence > Decimal("1"):
        raise SanityError("invalid_final_confidence_range", {"confidence": str(event.final_confidence)})

    if event.start_date and event.start_date < "2020-01-01":
        raise SanityError("implausible_start_date", {"start_date": event.start_date})

    if event.end_date and event.end_date < "2020-01-01":
        raise SanityError("implausible_end_date", {"end_date": event.end_date})

    if event.start_date and event.end_date and event.end_date < event.start_date:
        raise SanityError("invalid_date_range", {"start_date": event.start_date, "end_date": event.end_date})

    if event.event_type == "discount":
        if event.old_value is None or event.new_value is None:
            raise SanityError("discount_missing_price_values", {})
        if event.old_value <= 0 or event.new_value <= 0:
            raise SanityError("discount_non_positive_price", {})
        discount_percent = ((event.old_value - event.new_value) / event.old_value) * Decimal("100")
        if discount_percent < Decimal("0") or discount_percent > Decimal("95"):
            raise SanityError("discount_out_of_range", {"discount_percent": str(discount_percent)})

    if event.event_type == "credits":
        if event.new_value is None:
            raise SanityError("credits_missing_value", {})
        if event.new_value < 0 or event.new_value > Decimal("100000"):
            raise SanityError("credits_out_of_range", {"new_value": str(event.new_value)})

    if event.event_type in {"price_up", "price_down", "model_price", "ltd"}:
        if event.new_value is None or event.new_value <= 0:
            raise SanityError("price_must_be_positive", {"new_value": str(event.new_value)})

    if event.event_type in {"price_up", "price_down"}:
        if event.old_value is None or event.new_value is None:
            raise SanityError("price_change_missing_values", {})
        if event.old_value == event.new_value:
            raise SanityError("price_change_equal_values", {})

    if event.event_type == "new_model" and not event.model_name:
        raise SanityError("new_model_missing_model", {})

    if event.event_type == "ltd" and (event.new_value is None or event.new_value <= 0):
        raise SanityError("ltd_missing_positive_price", {})

    return event


def build_rejected_sanity_event(event: StructuredEventRecord, error: SanityError) -> RejectedEventRecord:
    return RejectedEventRecord(
        raw_document_id=event.raw_document_id,
        service_slug=event.service_slug,
        source_url=event.source_url,
        rejection_reason=error.reason,
        rejection_details=error.details,
    )
