from __future__ import annotations

import json

from ai_market_radar.repositories.base import BaseRepository


class PipelineAlertsRepository(BaseRepository):
    def create(self, alert_level: str, stage: str, message: str, payload: dict | None = None) -> None:
        query = """
            insert into pipeline_alerts (alert_level, stage, message, payload)
            values (%s, %s, %s, %s::jsonb)
        """
        with self.connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (alert_level, stage, message, json.dumps(payload or {})))
