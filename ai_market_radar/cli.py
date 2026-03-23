from __future__ import annotations

import argparse
import json
from pathlib import Path

from ai_market_radar.detector_runner import DetectorRunner
from ai_market_radar.expiry_runner import ExpiryRunner
from ai_market_radar.ingestion_runner import IngestionRunner
from ai_market_radar.llm_client import OpenAICompatibleLLMClient
from ai_market_radar.pipeline_runner import PipelineRunner
from ai_market_radar.postgres import PostgresConnectionFactory
from ai_market_radar.report_runner import ReportRunner


def _load_services(args: argparse.Namespace) -> set[str]:
    if not args.services_file:
        return {
            "chatgpt",
            "claude",
            "gemini",
            "copilot",
            "cursor",
            "midjourney",
            "perplexity",
            "elevenlabs",
            "runway",
            "heygen",
            "mistral",
            "grok",
            "replit",
            "suno",
            "pika",
            "invideo",
            "openai",
        }
    payload = json.loads(Path(args.services_file).read_text())
    return set(payload)


def _build_live_detector():
    client = OpenAICompatibleLLMClient()

    def _detector(raw_document, source_context):
        return client.extract_event(raw_document, source_context)

    return _detector


def main() -> None:
    parser = argparse.ArgumentParser(prog="ai_market_radar")
    subparsers = parser.add_subparsers(dest="command", required=True)

    detect_parser = subparsers.add_parser("detect")
    detect_parser.add_argument("--limit", type=int, default=100)
    detect_parser.add_argument("--services-file")

    pipeline_parser = subparsers.add_parser("pipeline")
    pipeline_parser.add_argument("--limit", type=int, default=100)

    subparsers.add_parser("expire")
    ingest_parser = subparsers.add_parser("ingest")
    ingest_parser.add_argument("--limit-sources", type=int, default=100)
    report_parser = subparsers.add_parser("report")
    report_parser.add_argument("--date")
    report_parser.add_argument("--no-telegram", action="store_true")
    weekly_parser = subparsers.add_parser("weekly")
    weekly_parser.add_argument("--date")

    args = parser.parse_args()
    connection_factory = PostgresConnectionFactory()

    if args.command == "detect":
        DetectorRunner(connection_factory).run(
            detector_callable=_build_live_detector(),
            valid_services=_load_services(args),
            limit=args.limit,
        )
        return

    if args.command == "pipeline":
        PipelineRunner(connection_factory).run_pipeline(limit=args.limit)
        return

    if args.command == "expire":
        ExpiryRunner(connection_factory).run()
        return

    if args.command == "ingest":
        IngestionRunner(connection_factory).run(limit_sources=args.limit_sources)
        return

    if args.command == "report":
        markdown = ReportRunner(connection_factory).run_daily(
            report_date=args.date,
            send_telegram=not args.no_telegram,
        )
        print(markdown)
        return

    if args.command == "weekly":
        markdown = ReportRunner(connection_factory).run_daily(
            report_date=args.date,
            send_telegram=not getattr(args, "no_telegram", False),
        )
        print(markdown)
        return

    raise SystemExit(f"Command `{args.command}` is scaffolded but not implemented yet.")


if __name__ == "__main__":
    main()
