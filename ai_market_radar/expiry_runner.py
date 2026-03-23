from __future__ import annotations

from ai_market_radar.postgres import PostgresConnectionFactory
from ai_market_radar.repositories.alerts_repo import PipelineAlertsRepository
from ai_market_radar.repositories.logs_repo import PipelineLogsRepository, PipelineMetricsRepository
from ai_market_radar.runtime import AdvisoryLockError, RunnerRuntime, timed


EXPIRY_LOCK_KEY = 41003


class ExpiryRunner:
    def __init__(self, connection_factory: PostgresConnectionFactory) -> None:
        self.connection_factory = connection_factory
        self.runtime = RunnerRuntime(connection_factory)
        self.logs_repo = PipelineLogsRepository(connection_factory)
        self.metrics_repo = PipelineMetricsRepository(connection_factory)
        self.alerts_repo = PipelineAlertsRepository(connection_factory)

    def run(self) -> None:
        try:
            with self.runtime.advisory_lock(EXPIRY_LOCK_KEY):
                with timed() as timer:
                    with self.connection_factory.connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                """
                                update events
                                set event_status = 'expired'
                                where event_status in ('active', 'published', 'decided')
                                  and expires_at is not null
                                  and expires_at < now()
                                """
                            )
                            expired_count = cur.rowcount
                runtime_sec = timer[1]
                self.metrics_repo.increment_metric("events_expired", expired_count)
                self.metrics_repo.increment_metric("expiry_runtime_sec", runtime_sec)
                self.logs_repo.log("expiry", "completed", "Expiry run completed", {"expired_count": expired_count})
        except AdvisoryLockError as exc:
            self.logs_repo.log("expiry", "skipped", str(exc))
        except Exception as exc:
            self.alerts_repo.create("ERROR", "expiry", "Expiry runner failed", {"error": str(exc)})
            raise
