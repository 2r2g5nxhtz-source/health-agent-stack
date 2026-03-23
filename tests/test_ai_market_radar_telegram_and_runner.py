import unittest
from unittest.mock import MagicMock, patch

from ai_market_radar.report_runner import ReportRunner
from ai_market_radar.telegram_sender import TelegramSenderError


class TelegramAndRunnerTests(unittest.TestCase):
    @patch("ai_market_radar.report_runner.TelegramSender")
    @patch("ai_market_radar.report_runner.ReportRunner.__init__", return_value=None)
    def test_runner_class_can_be_patched_for_daily_flow(self, _init, telegram_cls) -> None:
        runner = ReportRunner.__new__(ReportRunner)
        runner.events_repo = MagicMock()
        runner.reports_repo = MagicMock()
        runner.logs_repo = MagicMock()
        runner.metrics_repo = MagicMock()
        runner.alerts_repo = MagicMock()

        class _Runtime:
            def advisory_lock(self, _key):
                class _Ctx:
                    def __enter__(self_inner):
                        return None

                    def __exit__(self_inner, exc_type, exc, tb):
                        return False

                return _Ctx()

        runner.runtime = _Runtime()
        runner.events_repo.list_reportable_events.return_value = []
        telegram_cls.return_value.send_markdown.return_value = {"ok": True}

        markdown = ReportRunner.run_daily(runner, report_date="2026-03-24", send_telegram=True)
        self.assertIn("AI MARKET RADAR | 2026-03-24", markdown)
        runner.reports_repo.upsert_daily_report.assert_called_once()
        telegram_cls.return_value.send_markdown.assert_called_once()

    @patch("ai_market_radar.report_runner.TelegramSender")
    @patch("ai_market_radar.report_runner.ReportRunner.__init__", return_value=None)
    def test_runner_logs_telegram_failure_without_crashing(self, _init, telegram_cls) -> None:
        runner = ReportRunner.__new__(ReportRunner)
        runner.events_repo = MagicMock()
        runner.reports_repo = MagicMock()
        runner.logs_repo = MagicMock()
        runner.metrics_repo = MagicMock()
        runner.alerts_repo = MagicMock()

        class _Runtime:
            def advisory_lock(self, _key):
                class _Ctx:
                    def __enter__(self_inner):
                        return None

                    def __exit__(self_inner, exc_type, exc, tb):
                        return False

                return _Ctx()

        runner.runtime = _Runtime()
        runner.events_repo.list_reportable_events.return_value = []
        telegram_cls.return_value.send_markdown.side_effect = TelegramSenderError("boom")

        markdown = ReportRunner.run_daily(runner, report_date="2026-03-24", send_telegram=True)
        self.assertIn("AI MARKET RADAR | 2026-03-24", markdown)
        runner.alerts_repo.create.assert_called_once()

