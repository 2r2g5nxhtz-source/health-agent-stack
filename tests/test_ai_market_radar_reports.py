from decimal import Decimal
import unittest

from ai_market_radar.market_stats import calculate_market_stats
from ai_market_radar.models import FinalEventRecord
from ai_market_radar.report_generator import generate_daily_report


def _event(
    *,
    service_slug: str,
    event_type: str,
    title: str,
    old_value=None,
    new_value=None,
    currency="USD",
    version=1,
    confidence="0.85",
) -> FinalEventRecord:
    event_class = {
        "discount": "deal",
        "credits": "credit",
        "price_up": "fact",
        "price_down": "fact",
        "new_model": "signal",
        "launch": "info",
    }.get(event_type, "info")
    return FinalEventRecord(
        id=f"{service_slug}-{event_type}-{title}",
        canonical_key=f"{service_slug}|{event_type}|{title}",
        service_slug=service_slug,
        event_type=event_type,
        event_class=event_class,
        title=title,
        description=None,
        old_value=Decimal(str(old_value)) if old_value is not None else None,
        new_value=Decimal(str(new_value)) if new_value is not None else None,
        currency=currency,
        source_url="https://example.com",
        confidence=Decimal(confidence),
        event_status="active",
        version=version,
    )


class ReportTests(unittest.TestCase):
    def test_market_stats_calculates_expected_aggregates(self) -> None:
        events = [
            _event(service_slug="elevenlabs", event_type="discount", title="ElevenLabs 30% OFF", old_value=20, new_value=14),
            _event(service_slug="perplexity", event_type="credits", title="Perplexity gives $10", new_value=10),
            _event(service_slug="openai", event_type="new_model", title="GPT-4.1 launched"),
            _event(service_slug="chatgpt", event_type="price_up", title="ChatGPT Plus now $25", new_value=25, version=2),
        ]
        stats = calculate_market_stats(events, rejected_events=2, ignored_events=4)
        self.assertEqual(stats.events_new, 3)
        self.assertEqual(stats.events_update, 1)
        self.assertEqual(stats.discounts, 1)
        self.assertEqual(stats.credits, 1)
        self.assertEqual(stats.new_models, 1)
        self.assertEqual(stats.avg_llm_price, Decimal("25.00"))
        self.assertEqual(stats.avg_discount_percent, Decimal("30.00"))
        self.assertEqual(stats.rejected_events, 2)
        self.assertEqual(stats.events_ignored, 4)

    def test_generate_daily_report_contains_expected_sections(self) -> None:
        events = [
            _event(service_slug="elevenlabs", event_type="discount", title="ElevenLabs 30% OFF", old_value=20, new_value=14),
            _event(service_slug="perplexity", event_type="credits", title="Perplexity gives $10", new_value=10),
            _event(service_slug="openai", event_type="new_model", title="GPT-4.1 launched"),
            _event(service_slug="chatgpt", event_type="price_down", title="ChatGPT Plus back to $20", old_value=25, new_value=20, version=2),
            _event(service_slug="newvideo", event_type="launch", title="New AI Video Tool launched"),
        ]
        report = generate_daily_report(events, report_date="2026-03-24", rejected_events=1, ignored_events=2)
        self.assertIn("AI MARKET RADAR | 2026-03-24", report.markdown)
        self.assertIn("TOP EVENTS", report.markdown)
        self.assertIn("EXPIRING", report.markdown)
        self.assertIn("PRICE CHANGES", report.markdown)
        self.assertIn("NEW MODELS", report.markdown)
        self.assertIn("NEW TOOLS", report.markdown)
        self.assertIn("CREDITS", report.markdown)
        self.assertIn("MARKET STATS", report.markdown)
        self.assertIn("Signal / noise", report.markdown)

