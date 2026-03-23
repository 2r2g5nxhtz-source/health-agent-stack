import unittest
from unittest.mock import MagicMock

from ai_market_radar.collectors.rss_collector import RSSItem
from ai_market_radar.ingestion_runner import IngestionRunner


class IngestionTests(unittest.TestCase):
    def test_ingestion_runner_collects_and_inserts_raw_documents(self) -> None:
        runner = IngestionRunner.__new__(IngestionRunner)
        runner.raw_repo = MagicMock()
        runner.logs_repo = MagicMock()
        runner.metrics_repo = MagicMock()
        runner.alerts_repo = MagicMock()

        class _Runtime:
            def advisory_lock(self, _key):
                class _Ctx:
                    def __enter__(self_inner):
                        return None

                    def __exit__(self_inner, exc_type, exc, tb):
                        return False

                return _Ctx()

        runner.runtime = _Runtime()
        runner.rss_collector = MagicMock()
        runner.raw_repo.list_active_sources.return_value = [
            {
                "id": "src-1",
                "source_type": "official",
                "source_url": "https://example.com/feed.xml",
            }
        ]
        runner.rss_collector.collect.return_value = [
            RSSItem(
                external_id="item-1",
                title="Launch post",
                url="https://example.com/post",
                content="New model launched",
                published_at=None,
                author_name=None,
                content_hash="abc",
                raw_payload={"title": "Launch post"},
            )
        ]

        IngestionRunner.run(runner, limit_sources=10)
        runner.raw_repo.insert_raw_document.assert_called_once()
        runner.metrics_repo.increment_metric.assert_any_call("raw_documents_collected", 1)

