from __future__ import annotations

from decimal import Decimal

from ai_market_radar.models import FinalEventRecord
from ai_market_radar.repositories.base import BaseRepository


class EventsRepository(BaseRepository):
    def insert(self, event: FinalEventRecord, raw_document_id: str | None = None, conn=None) -> str:
        query = """
            insert into events (
                id, service_id, raw_document_id, event_type, event_class, title, description,
                source_url, old_value, new_value, value_currency, confidence, detected_at,
                event_date, status, event_status, version, canonical_fingerprint, dedupe_key,
                base_score, importance_score, final_score
            )
            select
                %s::uuid, s.id, %s::uuid, %s::event_type_enum, %s::event_class_enum, %s, %s,
                %s, %s, %s, %s, %s * 100, now(),
                now(), 'active', %s, %s, %s, %s,
                0, 0, 0
            from services s
            where s.slug = %s
            returning id::text
        """
        params = (
            event.id,
            raw_document_id,
            event.event_type,
            event.event_class,
            event.title,
            event.description,
            event.source_url,
            event.old_value,
            event.new_value,
            event.currency,
            event.confidence,
            event.event_status,
            event.version,
            event.canonical_key,
            event.canonical_key,
            event.service_slug,
        )
        if conn is None:
            with self.connection_factory.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    row = cur.fetchone()
            return row[0]
        with conn.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()
        return row[0]

    def find_existing_by_canonical_key(self, canonical_key: str) -> dict | None:
        query = """
            select id::text, canonical_fingerprint, version
            from events
            where canonical_fingerprint = %s
            order by last_changed_at desc
            limit 1
        """
        with self.connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (canonical_key,))
                row = cur.fetchone()
        if row is None:
            return None
        return {"id": row[0], "canonical_key": row[1], "version": row[2]}

    def list_reportable_events(self, report_date: str | None = None, limit: int = 200) -> list[FinalEventRecord]:
        query = """
            select
                e.id::text,
                s.slug,
                e.event_type::text,
                e.event_class::text,
                e.title,
                e.description,
                e.old_value,
                e.new_value,
                e.value_currency,
                e.source_url,
                e.confidence,
                e.event_status,
                e.version,
                e.canonical_fingerprint
            from events e
            join services s on s.id = e.service_id
            where e.event_status in ('active', 'published', 'decided')
              and (%s::date is null or e.detected_at::date = %s::date)
            order by e.final_score desc nulls last, e.confidence desc, e.detected_at desc
            limit %s
        """
        with self.connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (report_date, report_date, limit))
                rows = cur.fetchall()
        return [
            FinalEventRecord(
                id=row[0],
                service_slug=row[1],
                event_type=row[2],
                event_class=row[3],
                title=row[4],
                description=row[5],
                old_value=row[6] if row[6] is None else Decimal(str(row[6])),
                new_value=row[7] if row[7] is None else Decimal(str(row[7])),
                currency=row[8],
                source_url=row[9],
                confidence=Decimal(str(row[10])) / Decimal("100") if row[10] is not None else Decimal("0"),
                event_status=row[11],
                version=int(row[12]),
                canonical_key=row[13],
            )
            for row in rows
        ]
