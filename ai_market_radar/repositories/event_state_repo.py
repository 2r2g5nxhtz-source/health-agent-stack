from __future__ import annotations

from ai_market_radar.decision import EventStateRecord
from ai_market_radar.repositories.base import BaseRepository


class EventStateRepository(BaseRepository):
    def get_by_canonical_key(self, canonical_key: str) -> EventStateRecord | None:
        query = """
            select canonical_key, current_value, currency
            from event_state
            where canonical_key = %s
            limit 1
        """
        with self.connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (canonical_key,))
                row = cur.fetchone()
        if row is None:
            return None
        return EventStateRecord(canonical_key=row[0], current_value=row[1], currency=row[2])

    def upsert(self, canonical_key: str, service_slug: str, event_type: str, event_class: str, value, currency: str | None, conn=None) -> None:
        query = """
            insert into event_state (
                service_id, event_type, event_class, canonical_key, current_value, currency, updated_at
            )
            select s.id, %s::event_type_enum, %s::event_class_enum, %s, %s, %s, now()
            from services s
            where s.slug = %s
            on conflict (canonical_key) do update set
                current_value = excluded.current_value,
                currency = excluded.currency,
                updated_at = now()
        """
        if conn is None:
            with self.connection_factory.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (event_type, event_class, canonical_key, value, currency, service_slug))
            return
        with conn.cursor() as cur:
            cur.execute(query, (event_type, event_class, canonical_key, value, currency, service_slug))
