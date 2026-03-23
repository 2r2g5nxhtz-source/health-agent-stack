from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from typing import Any

from ai_market_radar.models import RawDocument
from ai_market_radar.repositories.base import BaseRepository


class RawDocumentsRepository(BaseRepository):
    def insert_raw_document(
        self,
        *,
        source_id: str,
        source_url: str,
        title: str,
        raw_text: str,
        external_id: str | None = None,
        author_name: str | None = None,
        published_at: str | None = None,
        raw_payload: dict | None = None,
        content_hash: str | None = None,
        conn=None,
    ) -> str:
        query = """
            insert into raw_documents (
                id, source_id, external_id, title, author_name, published_at, source_url,
                content_hash, raw_text, raw_payload, status
            )
            values (
                %s::uuid, %s::uuid, %s, %s, %s, %s::timestamptz, %s,
                %s, %s, %s::jsonb, 'new'
            )
            on conflict (source_id, external_id) where external_id is not null
            do update set
                title = excluded.title,
                author_name = excluded.author_name,
                published_at = excluded.published_at,
                raw_text = excluded.raw_text,
                raw_payload = excluded.raw_payload,
                content_hash = excluded.content_hash,
                source_url = excluded.source_url
            returning id::text
        """
        row_id = str(uuid4())
        payload_json = json.dumps(raw_payload or {})
        params = (
            row_id,
            source_id,
            external_id,
            title,
            author_name,
            published_at,
            source_url,
            content_hash or "",
            raw_text,
            payload_json,
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

    def get_unprocessed(self, limit: int = 100) -> list[RawDocument]:
        query = """
            select id::text, source_id::text, source_url, coalesce(title, '') as title,
                   coalesce(raw_text, '') as raw_text, published_at::text
            from raw_documents
            where status = 'new'
            order by fetched_at asc
            limit %s
        """
        with self.connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (limit,))
                rows = cur.fetchall()
        return [
            RawDocument(
                id=row[0],
                source_id=row[1],
                source_url=row[2],
                title=row[3],
                raw_text=row[4],
                published_at=row[5],
            )
            for row in rows
        ]

    def mark_processed(self, raw_document_id: str) -> None:
        self._set_status(raw_document_id, "processed")

    def mark_error(self, raw_document_id: str) -> None:
        self._set_status(raw_document_id, "error")

    def _set_status(self, raw_document_id: str, status: str) -> None:
        query = "update raw_documents set status = %s where id = %s::uuid"
        with self.connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (status, raw_document_id))

    def get_source_context(self, source_id: str) -> dict[str, Any] | None:
        query = """
            select source_type::text, source_url, service_id::text
            from sources
            where id = %s::uuid
        """
        with self.connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (source_id,))
                row = cur.fetchone()
        if row is None:
            return None
        return {"source_type": row[0], "source_url": row[1], "service_id": row[2]}

    def list_active_sources(self, source_types: tuple[str, ...] | None = None, limit: int = 100) -> list[dict[str, Any]]:
        if source_types:
            placeholders = ", ".join(["%s"] * len(source_types))
            query = f"""
                select id::text, service_id::text, source_type::text, source_url, parser_type, fetch_frequency
                from sources
                where is_active = true
                  and source_type::text in ({placeholders})
                order by priority asc, created_at asc
                limit %s
            """
            params = (*source_types, limit)
        else:
            query = """
                select id::text, service_id::text, source_type::text, source_url, parser_type, fetch_frequency
                from sources
                where is_active = true
                order by priority asc, created_at asc
                limit %s
            """
            params = (limit,)
        with self.connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
        return [
            {
                "id": row[0],
                "service_id": row[1],
                "source_type": row[2],
                "source_url": row[3],
                "parser_type": row[4],
                "fetch_frequency": row[5],
            }
            for row in rows
        ]
