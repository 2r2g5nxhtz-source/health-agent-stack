import unittest

from ai_market_radar.llm_client import parse_json_object, render_event_extraction_prompt
from ai_market_radar.models import RawDocument


class LLMClientTests(unittest.TestCase):
    def test_render_event_extraction_prompt_includes_document_context(self) -> None:
        raw_document = RawDocument(
            id="raw-1",
            source_id="src-1",
            source_url="https://chatgpt.com/pricing",
            title="Pricing changed",
            raw_text="ChatGPT Plus is now $25.",
            published_at="2026-03-24",
        )
        prompt = render_event_extraction_prompt(
            raw_document,
            {"source_type": "pricing", "service_slug_hint": "chatgpt"},
        )
        self.assertIn("Service hint: chatgpt", prompt)
        self.assertIn("Source type: pricing", prompt)
        self.assertIn("ChatGPT Plus is now $25.", prompt)

    def test_parse_json_object_extracts_json_from_wrapped_text(self) -> None:
        payload = parse_json_object("Here is the result:\n{\"service\":\"chatgpt\",\"confidence\":0.8}")
        self.assertEqual(payload["service"], "chatgpt")
        self.assertEqual(payload["confidence"], 0.8)


if __name__ == "__main__":
    unittest.main()
