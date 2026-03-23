from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from ai_market_radar.models import FinalEventRecord


SIGNAL_SCORE_THRESHOLD = 70
FALLBACK_BASE_SCORES = {
    "ltd": 90,
    "credits": 85,
    "discount": 80,
    "price_down": 70,
    "new_model": 65,
    "new_plan": 60,
    "launch": 50,
    "region_launch": 50,
    "price_up": 40,
}


@dataclass(frozen=True)
class MarketStats:
    events_new: int
    events_update: int
    events_ignored: int
    rejected_events: int
    discounts: int
    credits: int
    new_models: int
    avg_llm_price: Decimal | None
    avg_discount_percent: Decimal | None
    signal_noise_ratio: Decimal


def estimate_event_score(event: FinalEventRecord) -> int:
    if event.version > 1:
        return max(event.version * 5, 10)
    base = FALLBACK_BASE_SCORES.get(event.event_type, 20)
    confidence_bonus = int((event.confidence * Decimal("100")) * Decimal("0.2"))
    return base + confidence_bonus


def calculate_market_stats(
    events: Iterable[FinalEventRecord],
    *,
    rejected_events: int = 0,
    ignored_events: int = 0,
) -> MarketStats:
    event_list = list(events)
    discounts = [event for event in event_list if event.event_type == "discount"]
    credits = [event for event in event_list if event.event_type == "credits"]
    new_models = [event for event in event_list if event.event_type == "new_model"]
    price_events = [event for event in event_list if event.event_type in {"price_up", "price_down"} and event.new_value is not None]

    discount_percents: list[Decimal] = []
    for event in discounts:
        if event.old_value and event.new_value and event.old_value > 0:
            discount_percents.append(((event.old_value - event.new_value) / event.old_value) * Decimal("100"))

    avg_price = None
    if price_events:
        avg_price = sum((event.new_value for event in price_events if event.new_value is not None), Decimal("0")) / Decimal(len(price_events))

    avg_discount = None
    if discount_percents:
        avg_discount = sum(discount_percents, Decimal("0")) / Decimal(len(discount_percents))

    useful_events = sum(1 for event in event_list if estimate_event_score(event) > SIGNAL_SCORE_THRESHOLD)
    total_events = len(event_list) + ignored_events
    signal_noise_ratio = Decimal("0")
    if total_events > 0:
        signal_noise_ratio = Decimal(useful_events) / Decimal(total_events)

    return MarketStats(
        events_new=sum(1 for event in event_list if event.version == 1),
        events_update=sum(1 for event in event_list if event.version > 1),
        events_ignored=ignored_events,
        rejected_events=rejected_events,
        discounts=len(discounts),
        credits=len(credits),
        new_models=len(new_models),
        avg_llm_price=avg_price.quantize(Decimal("0.01")) if avg_price is not None else None,
        avg_discount_percent=avg_discount.quantize(Decimal("0.01")) if avg_discount is not None else None,
        signal_noise_ratio=signal_noise_ratio.quantize(Decimal("0.01")),
    )
