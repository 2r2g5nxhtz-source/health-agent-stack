from __future__ import annotations

from datetime import date

from ai_market_radar.postgres import PostgresConnectionFactory
from ai_market_radar.report_generator import generate_daily_report
from ai_market_radar.repositories.alerts_repo import PipelineAlertsRepository
from ai_market_radar.repositories.events_repo import EventsRepository
from ai_market_radar.repositories.logs_repo import PipelineLogsRepository, PipelineMetricsRepository
from ai_market_radar.repositories.reports_repo import ReportsRepository
from ai_market_radar.runtime import AdvisoryLockError, RunnerRuntime, timed
from ai_market_radar.telegram_sender import TelegramSender, TelegramSenderError


REPORT_LOCK_KEY = 41004


class ReportRunner:
    def __init__(self, connection_factory: PostgresConnectionFactory) -> None:
        self.connection_factory = connection_factory
        self.events_repo = EventsRepository(connection_factory)
        self.reports_repo = ReportsRepository(connection_factory)
        self.logs_repo = PipelineLogsRepository(connection_factory)
        self.metrics_repo = PipelineMetricsRepository(connection_factory)
        self.alerts_repo = PipelineAlertsRepository(connection_factory)
        self.runtime = RunnerRuntime(connection_factory)

    def run_daily(self, *, report_date: str | None = None, send_telegram: bool = True) -> str:
        report_date = report_date or date.today().isoformat()
        try:
            with self.runtime.advisory_lock(REPORT_LOCK_KEY):
                with timed() as timer:
                    events = self.events_repo.list_reportable_events(report_date=report_date)
                    report = generate_daily_report(events, report_date=report_date)
                    self.reports_repo.upsert_daily_report(report)
                    self.metrics_repo.increment_metric("reports_generated", 1)
                    if send_telegram:
                        try:
                            TelegramSender().send_markdown(report.markdown)
                            self.metrics_repo.increment_metric("telegram_reports_sent", 1)
                        except TelegramSenderError as exc:
                            self.alerts_repo.create("ERROR", "report", "Telegram send failed", {"error": str(exc)})
                            self.logs_repo.log("report", "error", "Telegram send failed", {"error": str(exc)})
                runtime_sec = timer[1]
                self.metrics_repo.increment_metric("report_runtime_sec", runtime_sec)
                self.logs_repo.log(
                    "report",
                    "completed",
                    "Daily report generated",
                    {"report_date": report_date, "runtime_sec": runtime_sec, "event_count": len(events)},
                )
                return report.markdown
        except AdvisoryLockError as exc:
            self.logs_repo.log("report", "skipped", str(exc))
            raise
