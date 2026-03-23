from __future__ import annotations

import json

from ai_market_radar.decision import DeltaDecisionResult
from ai_market_radar.repositories.base import BaseRepository


class DeltaDecisionsRepository(BaseRepository):
    def insert(self, structured_event_id: str, decision: DeltaDecisionResult, existing_event_id: str | None = None, conn=None) -> None:
        query = """
            insert into delta_decisions (
                structured_event_id, existing_event_id, canonical_key, decision, decision_reason,
                previous_payload, new_payload
            )
            values (
                %s::uuid, %s::uuid, %s, %s, %s, %s::jsonb, %s::jsonb
            )
            on conflict (structured_event_id) do update set
                existing_event_id = excluded.existing_event_id,
                canonical_key = excluded.canonical_key,
                decision = excluded.decision,
                decision_reason = excluded.decision_reason,
                previous_payload = excluded.previous_payload,
                new_payload = excluded.new_payload
        """
        previous_payload = json.dumps({"value": str(decision.previous_value) if decision.previous_value is not None else None})
        new_payload = json.dumps({"value": str(decision.new_value) if decision.new_value is not None else None})
        if conn is None:
            with self.connection_factory.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        query,
                        (
                            structured_event_id,
                            existing_event_id,
                            decision.canonical_key,
                            decision.decision.value,
                            decision.reason,
                            previous_payload,
                            new_payload,
                        ),
                    )
            return
        with conn.cursor() as cur:
            cur.execute(
                query,
                (
                    structured_event_id,
                    existing_event_id,
                    decision.canonical_key,
                    decision.decision.value,
                    decision.reason,
                    previous_payload,
                    new_payload,
                ),
            )
