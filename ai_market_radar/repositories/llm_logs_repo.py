from __future__ import annotations

import json

from ai_market_radar.repositories.base import BaseRepository


class LLMExtractionLogsRepository(BaseRepository):
    def insert(
        self,
        *,
        raw_document_id: str,
        detector_version: str,
        llm_provider: str | None,
        llm_model: str | None,
        prompt_text: str,
        response_text: str | None,
        response_json: dict | None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        estimated_cost_usd: float = 0.0,
        latency_ms: int | None = None,
    ) -> None:
        query = """
            insert into llm_extraction_logs (
                raw_document_id, detector_version, llm_provider, llm_model, prompt_text,
                response_text, response_json, input_tokens, output_tokens, estimated_cost_usd, latency_ms
            )
            values (
                %s::uuid, %s, %s, %s, %s,
                %s, %s::jsonb, %s, %s, %s, %s
            )
        """
        with self.connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    query,
                    (
                        raw_document_id,
                        detector_version,
                        llm_provider,
                        llm_model,
                        prompt_text,
                        response_text,
                        json.dumps(response_json) if response_json is not None else None,
                        input_tokens,
                        output_tokens,
                        estimated_cost_usd,
                        latency_ms,
                    ),
                )
