from __future__ import annotations

import json

from ai_market_radar.models import RejectedEventRecord
from ai_market_radar.repositories.base import BaseRepository


class RejectedEventsRepository(BaseRepository):
    def insert(self, rejected: RejectedEventRecord) -> None:
        query = """
            insert into rejected_events (
                raw_document_id, service_slug, source_url, rejection_reason, rejection_details
            )
            values (%s::uuid, %s, %s, %s, %s::jsonb)
        """
        with self.connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    query,
                    (
                        rejected.raw_document_id,
                        rejected.service_slug,
                        rejected.source_url,
                        rejected.rejection_reason,
                        json.dumps(rejected.rejection_details),
                    ),
                )
