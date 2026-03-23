from __future__ import annotations

from dataclasses import replace
from typing import Callable

from ai_market_radar.gpt_detector import ingest_detector_output
from ai_market_radar.llm_client import LLMExtractionResult
from ai_market_radar.models import RawDocument
from ai_market_radar.postgres import PostgresConnectionFactory
from ai_market_radar.repositories.alerts_repo import PipelineAlertsRepository
from ai_market_radar.repositories.logs_repo import PipelineLogsRepository, PipelineMetricsRepository
from ai_market_radar.repositories.llm_logs_repo import LLMExtractionLogsRepository
from ai_market_radar.repositories.raw_documents_repo import RawDocumentsRepository
from ai_market_radar.repositories.rejected_repo import RejectedEventsRepository
from ai_market_radar.repositories.structured_events_repo import StructuredEventsRepository
from ai_market_radar.runtime import AdvisoryLockError, RunnerRuntime, timed


DETECTOR_LOCK_KEY = 41001


class DetectorRunner:
    def __init__(self, connection_factory: PostgresConnectionFactory) -> None:
        self.connection_factory = connection_factory
        self.raw_repo = RawDocumentsRepository(connection_factory)
        self.structured_repo = StructuredEventsRepository(connection_factory)
        self.rejected_repo = RejectedEventsRepository(connection_factory)
        self.logs_repo = PipelineLogsRepository(connection_factory)
        self.metrics_repo = PipelineMetricsRepository(connection_factory)
        self.alerts_repo = PipelineAlertsRepository(connection_factory)
        self.llm_logs_repo = LLMExtractionLogsRepository(connection_factory)
        self.runtime = RunnerRuntime(connection_factory)

    def run(self, detector_callable: Callable[[RawDocument, dict], dict | str | LLMExtractionResult], valid_services: set[str], limit: int = 100) -> None:
        try:
            with self.runtime.advisory_lock(DETECTOR_LOCK_KEY):
                with timed() as timer:
                    raw_documents = self.raw_repo.get_unprocessed(limit=limit)
                    self.logs_repo.log("detector", "started", "Detector run started", {"count": len(raw_documents)})
                    self.metrics_repo.increment_metric("raw_documents_loaded", len(raw_documents))
                    for raw_document in raw_documents:
                        source_context = self.raw_repo.get_source_context(raw_document.source_id) or {}
                        try:
                            detector_output = detector_callable(raw_document, source_context)
                            extraction_usage = None
                            if isinstance(detector_output, LLMExtractionResult):
                                extraction_usage = detector_output.usage
                                detector_payload = detector_output.payload
                                self.llm_logs_repo.insert(
                                    raw_document_id=raw_document.id,
                                    detector_version="v1",
                                    llm_provider=detector_output.provider,
                                    llm_model=detector_output.model,
                                    prompt_text=detector_output.prompt_text,
                                    response_text=detector_output.raw_text,
                                    response_json=detector_output.payload,
                                    input_tokens=detector_output.usage.input_tokens,
                                    output_tokens=detector_output.usage.output_tokens,
                                    estimated_cost_usd=detector_output.usage.estimated_cost_usd,
                                    latency_ms=int(detector_output.latency_sec * 1000),
                                )
                            else:
                                detector_payload = detector_output
                            structured, rejected = ingest_detector_output(
                                raw_document=raw_document,
                                detector_output=detector_payload,
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
                            self.raw_repo.mark_processed(raw_document.id)
                            self.metrics_repo.increment_metric("structured_events_created", 1)
                            self.metrics_repo.increment_metric("avg_confidence", float(structured.final_confidence))
                            if extraction_usage is not None:
                                self.metrics_repo.increment_metric("llm_input_tokens", extraction_usage.input_tokens)
                                self.metrics_repo.increment_metric("llm_output_tokens", extraction_usage.output_tokens)
                                self.metrics_repo.increment_metric("llm_cost_usd", extraction_usage.estimated_cost_usd)
                        except Exception as exc:
                            self.raw_repo.mark_error(raw_document.id)
                            self.logs_repo.log(
                                "detector",
                                "error",
                                "Detector failed for raw document",
                                {"raw_document_id": raw_document.id, "error": str(exc)},
                            )
                            self.alerts_repo.create(
                                "ERROR",
                                "detector",
                                "Detector failed for raw document",
                                {"raw_document_id": raw_document.id, "error": str(exc)},
                            )
                runtime_sec = timer[1]
                self.metrics_repo.increment_metric("pipeline_runtime_sec", runtime_sec)
                self.logs_repo.log("detector", "completed", "Detector run completed", {"runtime_sec": runtime_sec})
        except AdvisoryLockError as exc:
            self.logs_repo.log("detector", "skipped", str(exc))
