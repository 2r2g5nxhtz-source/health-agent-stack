import unittest

from ai_market_radar.collectors.pricing_collector import PricingCollector


class PricingCollectorTests(unittest.TestCase):
    def test_collect_from_html_extracts_price_contexts(self) -> None:
        html = """
        <html>
          <body>
            <section>
              <h2>Plus</h2>
              <p>$20 per month</p>
            </section>
            <section>
              <h2>Team</h2>
              <p>$30 per seat monthly</p>
            </section>
          </body>
        </html>
        """
        collector = PricingCollector()
        items = collector.collect_from_html("https://example.com/pricing", html)
        self.assertGreaterEqual(len(items), 2)
        self.assertIn("$20", items[0].content)
        self.assertEqual(items[0].raw_payload["currency"], "USD")

