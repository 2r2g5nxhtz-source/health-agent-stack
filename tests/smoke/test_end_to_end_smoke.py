from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import tempfile
import time
import unittest
from datetime import date
from pathlib import Path

from ai_market_radar.collectors.rss_collector import RSSItem
from ai_market_radar.detector_runner import DetectorRunner
from ai_market_radar.ingestion_runner import IngestionRunner
from ai_market_radar.pipeline_runner import PipelineRunner
from ai_market_radar.report_runner import ReportRunner
from ai_market_radar.postgres import PostgresConnectionFactory


ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = ROOT / "tests" / "fixtures" / "raw"
SQL_DIR = ROOT / "sql" / "ai-market-radar"
DOCKER_CONTAINER = "ai-market-radar-smoke-postgres"
TEST_DATABASE_URL = "postgresql://postgres:postgres@127.0.0.1:55432/ai_market_radar"


def _driver_available() -> bool:
    return importlib.util.find_spec("psycopg") is not None or importlib.util.find_spec("psycopg2") is not None


@unittest.skipUnless(_driver_available(), "psycopg/psycopg2 not installed; smoke test scaffold is present but live DB run is skipped.")
class EndToEndSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run(
            ["docker", "rm", "-f", DOCKER_CONTAINER],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "--name",
                DOCKER_CONTAINER,
                "-e",
                "POSTGRES_PASSWORD=postgres",
                "-e",
                "POSTGRES_DB=ai_market_radar",
                "-p",
                "55432:5432",
                "-d",
                "postgres:16",
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        cls._wait_for_postgres()
        cls._apply_migrations()
        os.environ["AI_MARKET_RADAR_DATABASE_URL"] = TEST_DATABASE_URL

    @classmethod
    def tearDownClass(cls) -> None:
        subprocess.run(["docker", "rm", "-f", DOCKER_CONTAINER], check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    @classmethod
    def _wait_for_postgres(cls) -> None:
        for _ in range(30):
            probe = subprocess.run(
                ["docker", "exec", DOCKER_CONTAINER, "pg_isready", "-U", "postgres"],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if probe.returncode == 0:
                return
            time.sleep(1)
        raise RuntimeError("Postgres container did not become ready in time.")

    @classmethod
    def _apply_migrations(cls) -> None:
        migration_order = [
            "001_market_radar_init.sql",
            "002_event_taxonomy.sql",
            "003_pipeline_state.sql",
            "004_seed_services_and_sources.sql",
            "005_event_pipeline_hardening.sql",
            "006_runtime_ops.sql",
            "007_pipeline_alerts.sql",
        ]
        for migration in migration_order:
            sql_path = SQL_DIR / migration
            subprocess.run(
                [
                    "docker",
                    "exec",
                    "-i",
                    DOCKER_CONTAINER,
                    "psql",
                    "-U",
                    "postgres",
                    "-d",
                    "ai_market_radar",
                    "-v",
                    "ON_ERROR_STOP=1",
                    "-f",
                    "-",
                ],
                input=sql_path.read_text(),
                text=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

    def test_end_to_end_smoke(self) -> None:
        connection_factory = PostgresConnectionFactory(TEST_DATABASE_URL)
        report_date = date.today().isoformat()
        fixtures = [json.loads(path.read_text()) for path in sorted(FIXTURES_DIR.glob("smoke_*.json"))]

        ingestion_runner = IngestionRunner(connection_factory)
        detector_runner = DetectorRunner(connection_factory)
        pipeline_runner = PipelineRunner(connection_factory)
        report_runner = ReportRunner(connection_factory)

        ingestion_runner.raw_repo.list_active_sources = lambda source_types=None, limit=100: [  # type: ignore[method-assign]
            {
                "id": self._ensure_source(connection_factory, fixture["source_url"], fixture["source_type"], fixture["service_slug"]),
                "source_type": fixture["source_type"],
                "source_url": fixture["source_url"],
            }
            for fixture in fixtures
        ]
        ingestion_runner.rss_collector.collect = lambda source_url: [self._fixture_to_rss_item(fixture) for fixture in fixtures if fixture["source_url"] == source_url]  # type: ignore[method-assign]

        detector_map = {fixture["title"]: fixture["detector_payload"] for fixture in fixtures}

        def fake_detector(raw_document, source_context):
            return detector_map[raw_document.title]

        ingestion_runner.run(limit_sources=10)
        detector_runner.run(detector_callable=fake_detector, valid_services={"chatgpt", "openai"}, limit=20)
        pipeline_runner.run_pipeline(limit=20)
        markdown = report_runner.run_daily(report_date=report_date, send_telegram=False)

        counts = self._fetch_counts(connection_factory)
        self.assertEqual(counts["raw_documents"], 4)
        self.assertGreaterEqual(counts["structured_events"], 2)
        self.assertGreaterEqual(counts["events"], 2)
        self.assertGreaterEqual(counts["reports"], 1)
        self.assertEqual(counts["pipeline_errors"], 0)
        self.assertIn(f"AI MARKET RADAR | {report_date}", markdown)
        self.assertIn("ChatGPT Plus price increased", markdown)

    def _ensure_source(self, connection_factory: PostgresConnectionFactory, source_url: str, source_type: str, service_slug: str) -> str:
        with connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into services (slug, name, category, website_url, priority_tier, market_segment, is_active)
                    values (%s, %s, 'llm', %s, 1, 'assistant', true)
                    on conflict (slug) do nothing
                    """,
                    (service_slug, service_slug.title(), source_url),
                )
                cur.execute(
                    """
                    insert into sources (service_id, source_type, source_url, parser_type, priority, fetch_frequency, is_active)
                    select s.id, %s::source_type_enum, %s, 'rss', 1, 'daily', true
                    from services s
                    where s.slug = %s
                    on conflict (source_url) do update set
                      source_type = excluded.source_type
                    returning id::text
                    """,
                    (source_type, source_url, service_slug),
                )
                return cur.fetchone()[0]

    def _fixture_to_rss_item(self, fixture: dict) -> RSSItem:
        return RSSItem(
            external_id=fixture["title"],
            title=fixture["title"],
            url=fixture["source_url"],
            content=fixture["raw_text"],
            published_at="2026-03-24T08:00:00Z",
            author_name=None,
            content_hash=fixture["title"],
            raw_payload=fixture,
        )

    def _fetch_counts(self, connection_factory: PostgresConnectionFactory) -> dict[str, int]:
        with connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("select count(*) from raw_documents")
                raw_documents = cur.fetchone()[0]
                cur.execute("select count(*) from structured_events")
                structured_events = cur.fetchone()[0]
                cur.execute("select count(*) from events")
                events = cur.fetchone()[0]
                cur.execute("select count(*) from reports")
                reports = cur.fetchone()[0]
                cur.execute("select count(*) from pipeline_logs where status = 'error'")
                pipeline_errors = cur.fetchone()[0]
        return {
            "raw_documents": raw_documents,
            "structured_events": structured_events,
            "events": events,
            "reports": reports,
            "pipeline_errors": pipeline_errors,
        }
