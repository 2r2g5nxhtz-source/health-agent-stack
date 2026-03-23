from __future__ import annotations

import uuid
from dataclasses import replace
from typing import Iterable, Optional

from ai_market_radar.decision import (
    Decision,
    EventStateRecord,
    ExistingEventRecord,
    StructuredEventCandidate,
    build_canonical_key,
    decide_delta,
)
from ai_market_radar.models import FinalEventRecord, StructuredEventRecord


def to_candidate(event: StructuredEventRecord) -> StructuredEventCandidate:
    return StructuredEventCandidate(
        service_slug=event.service_slug,
        event_type=event.event_type,
        event_class=event.event_class,
        title=event.title,
        description=event.description,
        plan_name=event.plan_name,
        model_name=event.model_name,
        region=event.region,
        old_value=event.old_value,
        new_value=event.new_value,
        currency=event.currency,
        start_date=event.start_date,
        end_date=event.end_date,
        gpt_confidence=event.gpt_confidence,
        source_confidence=event.source_confidence,
    )


def build_final_event(
    *,
    structured_event: StructuredEventRecord,
    canonical_key: str,
    version: int,
    event_status: str,
) -> FinalEventRecord:
    return FinalEventRecord(
        id=str(uuid.uuid4()),
        canonical_key=canonical_key,
        service_slug=structured_event.service_slug,
        event_type=structured_event.event_type,
        event_class=structured_event.event_class,
        title=structured_event.title,
        description=structured_event.description,
        old_value=structured_event.old_value,
        new_value=structured_event.new_value,
        currency=structured_event.currency,
        source_url=structured_event.source_url,
        confidence=structured_event.final_confidence,
        event_status=event_status,
        version=version,
    )


def process_structured_event(
    *,
    structured_event: StructuredEventRecord,
    state: Optional[EventStateRecord] = None,
    existing_event: Optional[ExistingEventRecord] = None,
) -> dict[str, object]:
    candidate = to_candidate(structured_event)
    canonical_key = build_canonical_key(candidate)
    decision = decide_delta(candidate, state=state, existing_event=existing_event)
    processed_event = replace(structured_event, canonical_key=canonical_key)

    final_event = None
    next_state = state
    next_status = "ignored"

    if decision.decision == Decision.NEW:
        next_status = "decided"
        final_event = build_final_event(
            structured_event=processed_event,
            canonical_key=canonical_key,
            version=1,
            event_status="decided",
        )
        next_state = EventStateRecord(canonical_key=canonical_key, current_value=decision.new_value, currency=structured_event.currency)

    if decision.decision == Decision.UPDATE:
        next_status = "decided"
        current_version = 1
        if existing_event is not None and hasattr(existing_event, "version"):
            current_version = int(getattr(existing_event, "version")) + 1
        final_event = build_final_event(
            structured_event=processed_event,
            canonical_key=canonical_key,
            version=current_version,
            event_status="decided",
        )
        next_state = EventStateRecord(canonical_key=canonical_key, current_value=decision.new_value, currency=structured_event.currency)

    return {
        "structured_event": replace(processed_event, processing_status=next_status),
        "decision": decision,
        "final_event": final_event,
        "event_state": next_state,
    }


def process_structured_events(
    structured_events: Iterable[StructuredEventRecord],
    state_lookup: dict[str, EventStateRecord],
    existing_lookup: dict[str, ExistingEventRecord],
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for structured_event in structured_events:
        candidate = to_candidate(structured_event)
        canonical_key = build_canonical_key(candidate)
        result = process_structured_event(
            structured_event=structured_event,
            state=state_lookup.get(canonical_key),
            existing_event=existing_lookup.get(canonical_key),
        )
        if result["event_state"] is not None:
            state_lookup[canonical_key] = result["event_state"]  # type: ignore[assignment]
        if result["final_event"] is not None:
            existing_lookup[canonical_key] = ExistingEventRecord(canonical_key=canonical_key)
        results.append(result)
    return results
