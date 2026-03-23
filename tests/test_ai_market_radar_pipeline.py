from decimal import Decimal
import unittest

from ai_market_radar.decision import Decision, EventStateRecord
from ai_market_radar.gpt_detector import ingest_detector_output
from ai_market_radar.models import RawDocument, StructuredEventRecord
from ai_market_radar.pipeline_worker import process_structured_event


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.valid_services = {"chatgpt", "claude", "openai", "elevenlabs"}

    def test_detector_accepts_valid_payload(self) -> None:
        raw_document = RawDocument(
            id="raw-1",
            source_id="src-1",
            source_url="https://chatgpt.com/pricing",
            title="ChatGPT pricing update",
            raw_text="ChatGPT Plus is now $25 per month.",
        )
        payload = {
            "service": "chatgpt",
            "event_type": "price_up",
            "event_class": "fact",
            "title": "ChatGPT Plus price increased to $25",
            "description": "OpenAI increased ChatGPT Plus price from $20 to $25",
            "old_value": 20,
            "new_value": 25,
            "currency": "USD",
            "plan": "plus",
            "region": "global",
            "model": None,
            "start_date": "2026-03-01",
            "end_date": None,
            "source_url": "https://chatgpt.com/pricing",
            "confidence": 0.82,
            "evidence": ["ChatGPT Plus is now $25 per month."],
        }
        structured, rejected = ingest_detector_output(
            raw_document=raw_document,
            detector_output=payload,
            source_type="pricing",
            valid_services=self.valid_services,
        )
        self.assertIsNone(rejected)
        self.assertIsNotNone(structured)
        assert structured is not None
        self.assertEqual(structured.service_slug, "chatgpt")
        self.assertEqual(structured.final_confidence, Decimal("0.872"))

    def test_detector_rejects_unknown_service(self) -> None:
        raw_document = RawDocument(
            id="raw-2",
            source_id="src-2",
            source_url="https://example.com",
            title="Unknown service rumor",
            raw_text="A rumor about credits.",
        )
        payload = {
            "service": "mystery_ai",
            "event_type": "credits",
            "event_class": "credit",
            "title": "Mystery AI gives credits",
            "source_url": "https://example.com",
            "confidence": 0.7,
        }
        structured, rejected = ingest_detector_output(
            raw_document=raw_document,
            detector_output=payload,
            source_type="community",
            valid_services=self.valid_services,
        )
        self.assertIsNone(structured)
        self.assertIsNotNone(rejected)
        assert rejected is not None
        self.assertEqual(rejected.rejection_reason, "unknown_service")

    def test_pipeline_creates_new_event_from_structured_event(self) -> None:
        structured_event = StructuredEventRecord(
            id="se-1",
            raw_document_id="raw-1",
            service_slug="chatgpt",
            event_type="price_up",
            event_class="fact",
            title="ChatGPT Plus price increased to $25",
            description="OpenAI increased ChatGPT Plus price from $20 to $25",
            plan_name="plus",
            model_name=None,
            region="global",
            old_value=Decimal("20"),
            new_value=Decimal("25"),
            currency="USD",
            start_date="2026-03-01",
            end_date=None,
            source_url="https://chatgpt.com/pricing",
            gpt_confidence=Decimal("0.82"),
            source_confidence=Decimal("0.95"),
            final_confidence=Decimal("0.872"),
        )
        result = process_structured_event(structured_event=structured_event)
        self.assertEqual(result["decision"].decision, Decision.NEW)
        self.assertIsNotNone(result["final_event"])
        self.assertEqual(result["structured_event"].processing_status, "decided")

    def test_pipeline_updates_existing_state(self) -> None:
        structured_event = StructuredEventRecord(
            id="se-2",
            raw_document_id="raw-2",
            service_slug="chatgpt",
            event_type="price_down",
            event_class="fact",
            title="ChatGPT Plus price decreased to $20",
            description="OpenAI decreased ChatGPT Plus price from $25 to $20",
            plan_name="plus",
            model_name=None,
            region="global",
            old_value=Decimal("25"),
            new_value=Decimal("20"),
            currency="USD",
            start_date="2026-04-01",
            end_date=None,
            source_url="https://chatgpt.com/pricing",
            gpt_confidence=Decimal("0.84"),
            source_confidence=Decimal("0.95"),
            final_confidence=Decimal("0.884"),
        )
        state = EventStateRecord(
            canonical_key="chatgpt|price_state|price_plus_global",
            current_value=Decimal("25"),
            currency="USD",
        )
        result = process_structured_event(structured_event=structured_event, state=state)
        self.assertEqual(result["decision"].decision, Decision.UPDATE)
        self.assertIsNotNone(result["final_event"])


if __name__ == "__main__":
    unittest.main()
