from __future__ import annotations

from ai_market_radar.collectors.pricing_collector import PricingCollector, PricingCollectorError
from ai_market_radar.collectors.rss_collector import RSSCollector, RSSCollectorError
from ai_market_radar.postgres import PostgresConnectionFactory
from ai_market_radar.repositories.alerts_repo import PipelineAlertsRepository
from ai_market_radar.repositories.logs_repo import PipelineLogsRepository, PipelineMetricsRepository
from ai_market_radar.repositories.raw_documents_repo import RawDocumentsRepository
from ai_market_radar.runtime import AdvisoryLockError, RunnerRuntime, timed


INGESTION_LOCK_KEY = 41000


class IngestionRunner:
    def __init__(self, connection_factory: PostgresConnectionFactory) -> None:
        self.connection_factory = connection_factory
        self.raw_repo = RawDocumentsRepository(connection_factory)
        self.logs_repo = PipelineLogsRepository(connection_factory)
        self.metrics_repo = PipelineMetricsRepository(connection_factory)
        self.alerts_repo = PipelineAlertsRepository(connection_factory)
        self.runtime = RunnerRuntime(connection_factory)
        self.rss_collector = RSSCollector()
        self.pricing_collector = PricingCollector()

    def run(self, limit_sources: int = 100) -> None:
        try:
            with self.runtime.advisory_lock(INGESTION_LOCK_KEY):
                with timed() as timer:
                    sources = self.raw_repo.list_active_sources(
                        source_types=("official", "launch", "pricing", "community"),
                        limit=limit_sources,
                    )
                    self.logs_repo.log("ingestion", "started", "Ingestion run started", {"sources": len(sources)})
                    collected_count = 0
                    for source in sources:
                        collected_count += self._collect_source(source)
                runtime_sec = timer[1]
                self.metrics_repo.increment_metric("raw_documents_collected", collected_count)
                self.metrics_repo.increment_metric("ingestion_runtime_sec", runtime_sec)
                self.logs_repo.log(
                    "ingestion",
                    "completed",
                    "Ingestion run completed",
                    {"sources": len(sources), "raw_documents_collected": collected_count, "runtime_sec": runtime_sec},
                )
        except AdvisoryLockError as exc:
            self.logs_repo.log("ingestion", "skipped", str(exc))

    def _collect_source(self, source: dict) -> int:
        source_type = source["source_type"]
        if source_type not in {"official", "launch", "pricing", "community"}:
            return 0
        try:
            if source_type == "pricing":
                items = self.pricing_collector.collect(source["source_url"])
            else:
                items = self.rss_collector.collect(source["source_url"])
        except (RSSCollectorError, PricingCollectorError) as exc:
            self.logs_repo.log("ingestion", "error", "Collector failed", {"source_id": source["id"], "error": str(exc)})
            self.alerts_repo.create("ERROR", "ingestion", "Collector failed", {"source_id": source["id"], "error": str(exc)})
            return 0

        inserted = 0
        for item in items:
            self.raw_repo.insert_raw_document(
                source_id=source["id"],
                source_url=item.url,
                title=item.title,
                raw_text=item.content,
                external_id=item.external_id,
                author_name=item.author_name,
                published_at=item.published_at,
                raw_payload=item.raw_payload,
                content_hash=item.content_hash,
            )
            inserted += 1
        return inserted
