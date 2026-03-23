from decimal import Decimal
import unittest

from ai_market_radar.gpt_detector import ingest_detector_output
from ai_market_radar.models import RawDocument, StructuredEventRecord
from ai_market_radar.normalizer import normalize_structured_event
from ai_market_radar.sanity import SanityError, run_sanity_checks


class StabilizationTests(unittest.TestCase):
    def test_normalizer_normalizes_service_model_plan_currency_region(self) -> None:
        event = StructuredEventRecord(
            id="se-1",
            raw_document_id="raw-1",
            service_slug="ChatGPT",
            event_type="price_up",
            event_class="fact",
            title="Price changed",
            description=None,
            plan_name="Plus",
            model_name="GPT 4.1",
            region="Worldwide",
            old_value=Decimal("20"),
            new_value=Decimal("25"),
            currency="usd",
            start_date="2026-03-01",
            end_date=None,
            source_url="https://chatgpt.com/pricing",
            gpt_confidence=Decimal("0.8"),
            source_confidence=Decimal("0.95"),
            final_confidence=Decimal("0.86"),
        )
        normalized = normalize_structured_event(event)
        self.assertEqual(normalized.service_slug, "chatgpt")
        self.assertEqual(normalized.plan_name, "plus")
        self.assertEqual(normalized.model_name, "gpt-4.1")
        self.assertEqual(normalized.currency, "USD")
        self.assertEqual(normalized.region, "global")

    def test_normalizer_flips_price_change_to_price_down_when_values_drop(self) -> None:
        event = StructuredEventRecord(
            id="se-2",
            raw_document_id="raw-2",
            service_slug="chatgpt",
            event_type="price_change",
            event_class="fact",
            title="Price changed",
            description=None,
            plan_name="plus",
            model_name=None,
            region=None,
            old_value=Decimal("25"),
            new_value=Decimal("20"),
            currency="USD",
            start_date="2026-03-01",
            end_date=None,
            source_url="https://chatgpt.com/pricing",
            gpt_confidence=Decimal("0.8"),
            source_confidence=Decimal("0.95"),
            final_confidence=Decimal("0.86"),
        )
        normalized = normalize_structured_event(event)
        self.assertEqual(normalized.event_type, "price_down")
        self.assertEqual(normalized.event_class, "fact")

    def test_sanity_rejects_invalid_discount_percent(self) -> None:
        event = StructuredEventRecord(
            id="se-3",
            raw_document_id="raw-3",
            service_slug="elevenlabs",
            event_type="discount",
            event_class="deal",
            title="Huge discount",
            description=None,
            plan_name="creator",
            model_name=None,
            region="global",
            old_value=Decimal("100"),
            new_value=Decimal("1"),
            currency="USD",
            start_date="2026-03-01",
            end_date="2026-03-07",
            source_url="https://elevenlabs.io/pricing",
            gpt_confidence=Decimal("0.9"),
            source_confidence=Decimal("0.85"),
            final_confidence=Decimal("0.88"),
        )
        with self.assertRaises(SanityError):
            run_sanity_checks(event)

    def test_ingest_detector_output_applies_sanity_and_normalizer(self) -> None:
        raw_document = RawDocument(
            id="raw-4",
            source_id="src-1",
            source_url="https://chatgpt.com/pricing",
            title="Price update",
            raw_text="ChatGPT Plus is now $25.",
        )
        payload = {
            "service": "ChatGPT",
            "event_type": "price_up",
            "event_class": "fact",
            "title": "ChatGPT Plus price increased",
            "description": "ChatGPT Plus changed from $20 to $25",
            "old_value": 20,
            "new_value": 25,
            "currency": "usd",
            "plan": "Plus",
            "region": "Worldwide",
            "model": None,
            "start_date": "2026-03-01",
            "end_date": None,
            "source_url": "https://chatgpt.com/pricing",
            "confidence": 0.82,
            "evidence": ["ChatGPT Plus is now $25."],
        }
        structured, rejected = ingest_detector_output(
            raw_document=raw_document,
            detector_output=payload,
            source_type="pricing",
            valid_services={"chatgpt", "openai"},
        )
        self.assertIsNone(rejected)
        self.assertIsNotNone(structured)
        assert structured is not None
        self.assertEqual(structured.service_slug, "chatgpt")
        self.assertEqual(structured.plan_name, "plus")
        self.assertEqual(structured.currency, "USD")
        self.assertEqual(structured.region, "global")


if __name__ == "__main__":
    unittest.main()
