from __future__ import annotations

from decimal import Decimal

from ai_market_radar.models import StructuredEventRecord
from ai_market_radar.repositories.base import BaseRepository


class StructuredEventsRepository(BaseRepository):
    def insert(self, event: StructuredEventRecord, source_id: str | None = None, run_id: str | None = None) -> None:
        query = """
            insert into structured_events (
                id, raw_document_id, service_id, source_id, run_id, event_type, event_class,
                title, description, plan_name, model_name, region, old_value, new_value, currency,
                start_date, end_date, source_url, gpt_confidence, source_confidence, final_confidence,
                evidence, detector_version, canonical_key, canonical_payload, processing_status
            )
            select
                %s::uuid, %s::uuid, s.id, %s::uuid, %s::uuid, %s::event_type_enum, %s::event_class_enum,
                %s, %s, %s, %s, %s, %s, %s, %s,
                %s::date, %s::date, %s, %s, %s, %s,
                %s::jsonb, %s, %s, '{}'::jsonb, %s
            from services s
            where s.slug = %s
        """
        evidence_json = "[" + ",".join(f'"{item.replace(chr(34), "\\\"")}"' for item in event.evidence) + "]"
        params = (
            event.id,
            event.raw_document_id,
            source_id,
            run_id,
            event.event_type,
            event.event_class,
            event.title,
            event.description,
            event.plan_name,
            event.model_name,
            event.region,
            event.old_value,
            event.new_value,
            event.currency,
            event.start_date,
            event.end_date,
            event.source_url,
            event.gpt_confidence,
            event.source_confidence,
            event.final_confidence,
            evidence_json,
            event.detector_version,
            event.canonical_key,
            event.processing_status,
            event.service_slug,
        )
        with self.connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)

    def get_unprocessed(self, limit: int = 100) -> list[StructuredEventRecord]:
        query = """
            select
                se.id::text,
                se.raw_document_id::text,
                svc.slug,
                se.event_type::text,
                se.event_class::text,
                se.title,
                se.description,
                se.plan_name,
                se.model_name,
                se.region,
                se.old_value,
                se.new_value,
                se.currency,
                se.start_date::text,
                se.end_date::text,
                se.source_url,
                se.gpt_confidence,
                se.source_confidence,
                se.final_confidence,
                coalesce(se.evidence, '[]'::jsonb)::text,
                se.detector_version,
                se.canonical_key,
                se.processing_status
            from structured_events se
            join services svc on svc.id = se.service_id
            where se.processing_status in ('extracted', 'validated')
            order by se.extracted_at asc
            limit %s
        """
        with self.connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (limit,))
                rows = cur.fetchall()
        return [
            StructuredEventRecord(
                id=row[0],
                raw_document_id=row[1],
                service_slug=row[2],
                event_type=row[3],
                event_class=row[4],
                title=row[5],
                description=row[6],
                plan_name=row[7],
                model_name=row[8],
                region=row[9],
                old_value=row[10],
                new_value=row[11],
                currency=row[12],
                start_date=row[13],
                end_date=row[14],
                source_url=row[15],
                gpt_confidence=Decimal(str(row[16])),
                source_confidence=Decimal(str(row[17])),
                final_confidence=Decimal(str(row[18])),
                evidence=[],
                detector_version=row[20] or "v1",
                canonical_key=row[21],
                processing_status=row[22],
            )
            for row in rows
        ]

    def mark_status(self, structured_event_id: str, status: str, canonical_key: str | None = None, conn=None) -> None:
        query = """
            update structured_events
            set processing_status = %s,
                canonical_key = coalesce(%s, canonical_key),
                processed_at = now()
            where id = %s::uuid
        """
        if conn is None:
            with self.connection_factory.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (status, canonical_key, structured_event_id))
            return
        with conn.cursor() as cur:
            cur.execute(query, (status, canonical_key, structured_event_id))
