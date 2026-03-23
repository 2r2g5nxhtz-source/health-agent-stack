from decimal import Decimal
import unittest

from ai_market_radar.decision import (
    Decision,
    EventStateRecord,
    ExistingEventRecord,
    StructuredEventCandidate,
    build_canonical_key,
    decide_delta,
)


class DecisionTests(unittest.TestCase):
    def test_price_state_key_ignores_value(self) -> None:
        candidate = StructuredEventCandidate(
            service_slug="chatgpt",
            event_type="price_up",
            event_class="fact",
            title="ChatGPT Plus price increased",
            plan_name="Plus",
            region="global",
            new_value=Decimal("25"),
            currency="USD",
            gpt_confidence=Decimal("0.95"),
            source_confidence=Decimal("0.95"),
        )
        self.assertEqual(build_canonical_key(candidate), "chatgpt|price_state|price_plus_global")

    def test_price_state_change_updates(self) -> None:
        candidate = StructuredEventCandidate(
            service_slug="chatgpt",
            event_type="price_down",
            event_class="fact",
            title="ChatGPT Plus price decreased",
            plan_name="Plus",
            new_value=Decimal("20"),
            currency="USD",
            gpt_confidence=Decimal("0.9"),
            source_confidence=Decimal("0.95"),
        )
        state = EventStateRecord(
            canonical_key="chatgpt|price_state|price_plus_global",
            current_value=Decimal("25"),
            currency="USD",
        )
        result = decide_delta(candidate, state=state)
        self.assertEqual(result.decision, Decision.UPDATE)
        self.assertEqual(result.reason, "state_changed")

    def test_same_state_is_ignored(self) -> None:
        candidate = StructuredEventCandidate(
            service_slug="chatgpt",
            event_type="price_up",
            event_class="fact",
            title="ChatGPT Plus price observed",
            plan_name="Plus",
            new_value=Decimal("25"),
            currency="USD",
            gpt_confidence=Decimal("0.9"),
            source_confidence=Decimal("0.95"),
        )
        state = EventStateRecord(
            canonical_key="chatgpt|price_state|price_plus_global",
            current_value=Decimal("25"),
            currency="USD",
        )
        result = decide_delta(candidate, state=state)
        self.assertEqual(result.decision, Decision.IGNORE)
        self.assertEqual(result.reason, "same_state")

    def test_discount_same_offer_is_ignored(self) -> None:
        candidate = StructuredEventCandidate(
            service_slug="elevenlabs",
            event_type="discount",
            event_class="deal",
            title="ElevenLabs 30% off annual plan",
            plan_name="Creator",
            new_value=Decimal("17"),
            currency="USD",
            start_date="2026-03-23",
            end_date="2026-03-30",
            gpt_confidence=Decimal("0.92"),
            source_confidence=Decimal("0.85"),
        )
        existing = ExistingEventRecord(canonical_key=build_canonical_key(candidate))
        result = decide_delta(candidate, existing_event=existing)
        self.assertEqual(result.decision, Decision.IGNORE)
        self.assertEqual(result.reason, "same_offer_or_release")

    def test_new_model_is_new(self) -> None:
        candidate = StructuredEventCandidate(
            service_slug="openai",
            event_type="new_model",
            event_class="signal",
            title="GPT-4.1 launched",
            model_name="GPT-4.1",
            gpt_confidence=Decimal("0.88"),
            source_confidence=Decimal("0.90"),
        )
        result = decide_delta(candidate)
        self.assertEqual(result.decision, Decision.NEW)
        self.assertEqual(result.canonical_key, "openai|new_model|gpt_4.1")

    def test_low_confidence_candidate_is_ignored(self) -> None:
        candidate = StructuredEventCandidate(
            service_slug="reddit-rumor",
            event_type="credits",
            event_class="credit",
            title="Rumored credits",
            new_value=Decimal("10"),
            currency="USD",
            gpt_confidence=Decimal("0.3"),
            source_confidence=Decimal("0.4"),
        )
        result = decide_delta(candidate)
        self.assertEqual(result.decision, Decision.IGNORE)
        self.assertEqual(result.reason, "low_confidence")


if __name__ == "__main__":
    unittest.main()
