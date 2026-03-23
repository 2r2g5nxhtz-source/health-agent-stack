from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Optional


STATEFUL_EVENT_TYPES = {"price_up", "price_down", "free_tier", "context", "model_price", "rate_limit"}
STATEFUL_PRICE_TYPES = {"price_up", "price_down"}
STATEFUL_SCOPE_VALUE_TYPES = {"free_tier", "context", "model_price", "rate_limit"}
STATELESS_EVENT_TYPES = {
    "discount",
    "credits",
    "new_model",
    "new_plan",
    "ltd",
    "launch",
    "region_launch",
}


class Decision(str, Enum):
    NEW = "NEW"
    UPDATE = "UPDATE"
    IGNORE = "IGNORE"


@dataclass(frozen=True)
class StructuredEventCandidate:
    service_slug: str
    event_type: str
    event_class: str
    title: str
    description: Optional[str] = None
    plan_name: Optional[str] = None
    model_name: Optional[str] = None
    region: Optional[str] = None
    old_value: Optional[Decimal] = None
    new_value: Optional[Decimal] = None
    currency: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    gpt_confidence: Decimal = Decimal("0")
    source_confidence: Decimal = Decimal("0")

    @property
    def final_confidence(self) -> Decimal:
        return (self.gpt_confidence * Decimal("0.6")) + (self.source_confidence * Decimal("0.4"))


@dataclass(frozen=True)
class EventStateRecord:
    canonical_key: str
    current_value: Optional[Decimal] = None
    currency: Optional[str] = None


@dataclass(frozen=True)
class ExistingEventRecord:
    canonical_key: str


@dataclass(frozen=True)
class DeltaDecisionResult:
    decision: Decision
    reason: str
    canonical_key: str
    previous_value: Optional[Decimal]
    new_value: Optional[Decimal]


def normalize_token(value: Optional[str], default: str = "global") -> str:
    if not value:
        return default
    normalized = value.strip().lower()
    for old, new in ((" ", "_"), ("/", "_"), ("-", "_")):
        normalized = normalized.replace(old, new)
    return normalized or default


def normalize_decimal(value: Optional[Decimal]) -> Optional[Decimal]:
    if value is None:
        return None
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def decimal_to_key(value: Optional[Decimal]) -> str:
    if value is None:
        return "na"
    return f"{normalize_decimal(value):.2f}"


def build_scope(candidate: StructuredEventCandidate) -> str:
    if candidate.event_type in STATEFUL_PRICE_TYPES:
        return f"price_{normalize_token(candidate.plan_name)}_{normalize_token(candidate.region)}"
    if candidate.event_type in STATEFUL_SCOPE_VALUE_TYPES:
        if candidate.model_name:
            return f"{normalize_token(candidate.event_type)}_{normalize_token(candidate.model_name)}"
        if candidate.plan_name:
            return f"{normalize_token(candidate.event_type)}_{normalize_token(candidate.plan_name)}"
        return normalize_token(candidate.event_type)
    if candidate.event_type == "new_model":
        return normalize_token(candidate.model_name)
    if candidate.event_type == "new_plan":
        return normalize_token(candidate.plan_name)
    if candidate.event_type == "region_launch":
        return f"{normalize_token(candidate.region)}_{normalize_token(candidate.title)}"
    if candidate.event_type == "launch":
        return normalize_token(candidate.title)
    if candidate.plan_name:
        return normalize_token(candidate.plan_name)
    if candidate.model_name:
        return normalize_token(candidate.model_name)
    return "global"


def build_canonical_key(candidate: StructuredEventCandidate) -> str:
    service = normalize_token(candidate.service_slug)
    currency = normalize_token(candidate.currency, default="na")
    scope = build_scope(candidate)

    if candidate.event_type in STATEFUL_PRICE_TYPES:
        return f"{service}|price_state|{scope}"

    if candidate.event_type in STATEFUL_SCOPE_VALUE_TYPES:
        return f"{service}|{normalize_token(candidate.event_type)}_state|{scope}"

    if candidate.event_type == "discount":
        return "|".join(
            [
                service,
                "discount",
                scope,
                decimal_to_key(candidate.new_value),
                currency,
                normalize_token(candidate.start_date, default="open"),
                normalize_token(candidate.end_date, default="open"),
            ]
        )

    if candidate.event_type == "credits":
        return "|".join(
            [
                service,
                "credits",
                scope,
                decimal_to_key(candidate.new_value),
                currency,
                normalize_token(candidate.start_date, default="open"),
            ]
        )

    if candidate.event_type == "new_model":
        return f"{service}|new_model|{scope}"

    if candidate.event_type == "new_plan":
        return f"{service}|new_plan|{scope}"

    if candidate.event_type == "ltd":
        return "|".join(
            [
                service,
                "ltd",
                scope,
                decimal_to_key(candidate.new_value),
                currency,
                normalize_token(candidate.start_date, default="open"),
            ]
        )

    if candidate.event_type == "launch":
        return f"{service}|launch|{scope}"

    if candidate.event_type == "region_launch":
        return f"{service}|region_launch|{scope}"

    return f"{service}|{normalize_token(candidate.event_type)}|{scope}"


def decide_delta(
    candidate: StructuredEventCandidate,
    state: Optional[EventStateRecord] = None,
    existing_event: Optional[ExistingEventRecord] = None,
    confidence_threshold: Decimal = Decimal("0.5"),
) -> DeltaDecisionResult:
    canonical_key = build_canonical_key(candidate)
    new_value = normalize_decimal(candidate.new_value)
    previous_value = normalize_decimal(state.current_value) if state else None

    if candidate.final_confidence < confidence_threshold:
        return DeltaDecisionResult(Decision.IGNORE, "low_confidence", canonical_key, previous_value, new_value)

    if candidate.event_type in STATEFUL_EVENT_TYPES:
        if state is None:
            return DeltaDecisionResult(Decision.NEW, "no_existing_state", canonical_key, previous_value, new_value)
        if previous_value == new_value and normalize_token(state.currency, "na") == normalize_token(candidate.currency, "na"):
            return DeltaDecisionResult(Decision.IGNORE, "same_state", canonical_key, previous_value, new_value)
        return DeltaDecisionResult(Decision.UPDATE, "state_changed", canonical_key, previous_value, new_value)

    if candidate.event_type in STATELESS_EVENT_TYPES:
        if existing_event is not None:
            return DeltaDecisionResult(
                Decision.IGNORE,
                "same_offer_or_release",
                canonical_key,
                previous_value,
                new_value,
            )
        return DeltaDecisionResult(Decision.NEW, "new_offer_or_release", canonical_key, previous_value, new_value)

    return DeltaDecisionResult(Decision.IGNORE, "unsupported_type", canonical_key, previous_value, new_value)
