from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable

from ai_market_radar.market_stats import MarketStats, calculate_market_stats, estimate_event_score
from ai_market_radar.models import FinalEventRecord


@dataclass(frozen=True)
class DailyReport:
    report_date: str
    markdown: str
    stats: MarketStats


def _format_money(value: Decimal | None, currency: str | None = "USD") -> str:
    if value is None:
        return "n/a"
    if currency == "USD":
        return f"${value.quantize(Decimal('0.01'))}"
    return f"{value.quantize(Decimal('0.01'))} {currency or ''}".strip()


def _event_line(index: int, event: FinalEventRecord) -> str:
    score = estimate_event_score(event)
    if event.event_type == "discount" and event.old_value and event.new_value and event.old_value > 0:
        discount_percent = ((event.old_value - event.new_value) / event.old_value) * Decimal("100")
        return f"{index}. {event.service_slug} — {discount_percent.quantize(Decimal('0.1'))}% OFF — Score {score}"
    if event.event_type == "credits":
        return f"{index}. {event.service_slug} — {_format_money(event.new_value, event.currency)} credits — Score {score}"
    if event.event_type == "new_model":
        return f"{index}. {event.title} — Score {score}"
    return f"{index}. {event.title} — Score {score}"


def _select_top_events(events: list[FinalEventRecord], limit: int = 3) -> list[FinalEventRecord]:
    return sorted(events, key=lambda event: (estimate_event_score(event), event.confidence), reverse=True)[:limit]


def _filter_by_type(events: Iterable[FinalEventRecord], event_types: set[str]) -> list[FinalEventRecord]:
    return [event for event in events if event.event_type in event_types]


def _render_section(title: str, lines: list[str]) -> str:
    if not lines:
        lines = ["- none"]
    return "\n".join([title, *lines])


def generate_daily_report(
    events: Iterable[FinalEventRecord],
    *,
    report_date: str | None = None,
    rejected_events: int = 0,
    ignored_events: int = 0,
) -> DailyReport:
    event_list = list(events)
    report_date = report_date or date.today().isoformat()
    stats = calculate_market_stats(event_list, rejected_events=rejected_events, ignored_events=ignored_events)

    top_events = _select_top_events(event_list)
    expiring = [event for event in event_list if event.event_type in {"discount", "credits"} and event.event_status not in {"expired", "archived"}]
    price_changes = _filter_by_type(event_list, {"price_up", "price_down"})
    new_models = _filter_by_type(event_list, {"new_model"})
    new_tools = _filter_by_type(event_list, {"launch", "region_launch"})
    credits = _filter_by_type(event_list, {"credits"})

    markdown = "\n\n".join(
        [
            f"AI MARKET RADAR | {report_date}",
            _render_section("TOP EVENTS", [_event_line(index + 1, event) for index, event in enumerate(top_events)]),
            _render_section("EXPIRING", [f"- {event.title}" for event in expiring]),
            _render_section(
                "PRICE CHANGES",
                [f"- {event.title}" for event in price_changes],
            ),
            _render_section("NEW MODELS", [f"- {event.title}" for event in new_models]),
            _render_section("NEW TOOLS", [f"- {event.title}" for event in new_tools]),
            _render_section("CREDITS", [f"- {event.title}" for event in credits]),
            _render_section(
                "MARKET STATS",
                [
                    f"- New events: {stats.events_new}",
                    f"- Updates: {stats.events_update}",
                    f"- Ignored: {stats.events_ignored}",
                    f"- Rejected: {stats.rejected_events}",
                    f"- Discounts: {stats.discounts}",
                    f"- Credits: {stats.credits}",
                    f"- New models: {stats.new_models}",
                    f"- Avg LLM price: {_format_money(stats.avg_llm_price)}",
                    f"- Avg discount: {stats.avg_discount_percent}%" if stats.avg_discount_percent is not None else "- Avg discount: n/a",
                    f"- Signal / noise: {stats.signal_noise_ratio}",
                ],
            ),
        ]
    )

    return DailyReport(report_date=report_date, markdown=markdown, stats=stats)
