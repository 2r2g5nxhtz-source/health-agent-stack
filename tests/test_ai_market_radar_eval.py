import unittest
from pathlib import Path

from ai_market_radar.eval_runner import run_golden_eval


class EvalTests(unittest.TestCase):
    def test_golden_eval_scaffold_runs(self) -> None:
        result = run_golden_eval(Path("evals/golden/events_v1.jsonl"))
        self.assertEqual(result.total, 30)
        self.assertGreaterEqual(result.exact_matches, 18)
        self.assertGreaterEqual(result.rejected_correctly, 5)
        self.assertGreaterEqual(result.precision_like, 0.8)


if __name__ == "__main__":
    unittest.main()
