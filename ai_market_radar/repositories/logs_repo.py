from __future__ import annotations

import json

from ai_market_radar.repositories.base import BaseRepository


class PipelineLogsRepository(BaseRepository):
    def log(self, stage: str, status: str, message: str, payload: dict | None = None) -> None:
        query = """
            insert into pipeline_logs (stage, status, message, payload)
            values (%s, %s, %s, %s::jsonb)
        """
        with self.connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (stage, status, message, json.dumps(payload or {})))


class PipelineMetricsRepository(BaseRepository):
    def increment_metric(self, metric_name: str, metric_value: float = 1.0) -> None:
        query = """
            insert into pipeline_metrics (metric_date, metric_name, metric_value)
            values (current_date, %s, %s)
            on conflict (metric_date, metric_name) do update set
                metric_value = pipeline_metrics.metric_value + excluded.metric_value
        """
        with self.connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (metric_name, metric_value))
