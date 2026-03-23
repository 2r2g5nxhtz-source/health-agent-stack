from __future__ import annotations

from dataclasses import replace

from ai_market_radar.gpt_detector import ingest_detector_output
from ai_market_radar.pipeline_worker import process_structured_event
from ai_market_radar.postgres import PostgresConnectionFactory
from ai_market_radar.repositories.alerts_repo import PipelineAlertsRepository
from ai_market_radar.repositories.delta_repo import DeltaDecisionsRepository
from ai_market_radar.repositories.event_state_repo import EventStateRepository
from ai_market_radar.repositories.events_repo import EventsRepository
from ai_market_radar.repositories.logs_repo import PipelineLogsRepository, PipelineMetricsRepository
from ai_market_radar.repositories.raw_documents_repo import RawDocumentsRepository
from ai_market_radar.repositories.rejected_repo import RejectedEventsRepository
from ai_market_radar.repositories.structured_events_repo import StructuredEventsRepository
from ai_market_radar.runtime import AdvisoryLockError, RunnerRuntime, timed


PIPELINE_LOCK_KEY = 41002


class PipelineRunner:
    def __init__(self, connection_factory: PostgresConnectionFactory) -> None:
        self.connection_factory = connection_factory
        self.raw_repo = RawDocumentsRepository(connection_factory)
        self.structured_repo = StructuredEventsRepository(connection_factory)
        self.events_repo = EventsRepository(connection_factory)
        self.event_state_repo = EventStateRepository(connection_factory)
        self.delta_repo = DeltaDecisionsRepository(connection_factory)
        self.rejected_repo = RejectedEventsRepository(connection_factory)
        self.logs_repo = PipelineLogsRepository(connection_factory)
        self.metrics_repo = PipelineMetricsRepository(connection_factory)
        self.alerts_repo = PipelineAlertsRepository(connection_factory)
        self.runtime = RunnerRuntime(connection_factory)

    def run_detector(self, detector_callable, valid_services: set[str], limit: int = 100) -> None:
        raw_documents = self.raw_repo.get_unprocessed(limit=limit)
        self.logs_repo.log("detector", "started", "Detector run started", {"count": len(raw_documents)})
        for raw_document in raw_documents:
            source_context = self.raw_repo.get_source_context(raw_document.source_id) or {}
            try:
                detector_output = detector_callable(raw_document, source_context)
                structured, rejected = ingest_detector_output(
                    raw_document=raw_document,
                    detector_output=detector_output,
                    source_type=source_context.get("source_type", "community"),
                    valid_services=valid_services,
                )
                if rejected is not None:
                    self.rejected_repo.insert(rejected)
                    self.metrics_repo.increment_metric("rejected_events", 1)
                    self.raw_repo.mark_error(raw_document.id)
                    continue
                assert structured is not None
                structured = replace(structured, processing_status="validated")
                self.structured_repo.insert(structured, source_id=raw_document.source_id)
                self.metrics_repo.increment_metric("structured_events", 1)
                self.raw_repo.mark_processed(raw_document.id)
            except Exception as exc:
                self.raw_repo.mark_error(raw_document.id)
                self.logs_repo.log("detector", "error", "Detector failed", {"raw_document_id": raw_document.id, "error": str(exc)})
        self.logs_repo.log("detector", "completed", "Detector run completed")

    def run_pipeline(self, limit: int = 100) -> None:
        try:
            with self.runtime.advisory_lock(PIPELINE_LOCK_KEY):
                with timed() as timer:
                    structured_events = self.structured_repo.get_unprocessed(limit=limit)
                    self.logs_repo.log("pipeline", "started", "Pipeline run started", {"count": len(structured_events)})
                    for structured_event in structured_events:
                        self._process_one(structured_event)
                runtime_sec = timer[1]
                self.metrics_repo.increment_metric("pipeline_runtime_sec", runtime_sec)
                self.logs_repo.log("pipeline", "completed", "Pipeline run completed", {"runtime_sec": runtime_sec})
        except AdvisoryLockError as exc:
            self.logs_repo.log("pipeline", "skipped", str(exc))

    def _process_one(self, structured_event) -> None:
        existing = None
        if structured_event.canonical_key:
            existing = self.events_repo.find_existing_by_canonical_key(structured_event.canonical_key)
        state = self.event_state_repo.get_by_canonical_key(structured_event.canonical_key or "")
        result = process_structured_event(structured_event=structured_event, state=state, existing_event=existing)
        decision = result["decision"]
        final_event = result["final_event"]
        next_state = result["event_state"]
        processed_event = result["structured_event"]

        try:
            with self.connection_factory.connection() as conn:
                existing_event_id = existing["id"] if existing else None
                self.delta_repo.insert(structured_event.id, decision, existing_event_id=existing_event_id, conn=conn)

                if final_event is not None:
                    self.events_repo.insert(final_event, raw_document_id=structured_event.raw_document_id, conn=conn)
                    if next_state is not None:
                        self.event_state_repo.upsert(
                            canonical_key=decision.canonical_key,
                            service_slug=final_event.service_slug,
                            event_type=final_event.event_type,
                            event_class=final_event.event_class,
                            value=decision.new_value,
                            currency=final_event.currency,
                            conn=conn,
                        )
                    self.metrics_repo.increment_metric("events_new" if decision.decision.value == "NEW" else "events_update", 1)
                else:
                    self.metrics_repo.increment_metric("events_ignored", 1)

                final_status = "finalized" if final_event is not None else "ignored"
                self.structured_repo.mark_status(
                    processed_event.id,
                    final_status,
                    canonical_key=decision.canonical_key,
                    conn=conn,
                )
        except Exception as exc:
            self.logs_repo.log(
                "pipeline",
                "error",
                "Pipeline failed for structured event",
                {"structured_event_id": structured_event.id, "error": str(exc)},
            )
            self.alerts_repo.create(
                "ERROR",
                "pipeline",
                "Pipeline failed for structured event",
                {"structured_event_id": structured_event.id, "error": str(exc)},
            )
            raise


def main() -> None:
    runner = PipelineRunner(PostgresConnectionFactory())
    raise SystemExit(
        "PipelineRunner is wired for Postgres. Instantiate it from an app entrypoint with a detector callable and service registry."
    )


if __name__ == "__main__":
    main()
