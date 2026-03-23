from __future__ import annotations

import json

from ai_market_radar.repositories.base import BaseRepository
from ai_market_radar.report_generator import DailyReport


class ReportsRepository(BaseRepository):
    def upsert_daily_report(self, report: DailyReport, report_type: str = "daily_market_report") -> None:
        query = """
            insert into reports (report_type, report_date, report_markdown, report_json)
            values (%s, %s::date, %s, %s::jsonb)
            on conflict (report_type, report_date) do update set
                report_markdown = excluded.report_markdown,
                report_json = excluded.report_json
        """
        payload = {
            "stats": {
                "events_new": report.stats.events_new,
                "events_update": report.stats.events_update,
                "events_ignored": report.stats.events_ignored,
                "rejected_events": report.stats.rejected_events,
                "discounts": report.stats.discounts,
                "credits": report.stats.credits,
                "new_models": report.stats.new_models,
                "avg_llm_price": str(report.stats.avg_llm_price) if report.stats.avg_llm_price is not None else None,
                "avg_discount_percent": str(report.stats.avg_discount_percent)
                if report.stats.avg_discount_percent is not None
                else None,
                "signal_noise_ratio": str(report.stats.signal_noise_ratio),
            }
        }
        with self.connection_factory.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (report_type, report.report_date, report.markdown, json.dumps(payload)))
