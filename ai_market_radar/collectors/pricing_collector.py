from __future__ import annotations

import hashlib
import html
import re
import urllib.error
import urllib.request
from dataclasses import dataclass


class PricingCollectorError(RuntimeError):
    pass


PRICE_PATTERN = re.compile(r"(?P<currency>\$|USD\s*)(?P<amount>\d+(?:\.\d{1,2})?)", re.IGNORECASE)


@dataclass(frozen=True)
class PricingItem:
    external_id: str
    title: str
    url: str
    content: str
    published_at: str | None
    author_name: str | None
    content_hash: str
    raw_payload: dict


def _strip_html(html_text: str) -> str:
    text = re.sub(r"<script.*?>.*?</script>", " ", html_text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style.*?>.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return " ".join(text.split())


class PricingCollector:
    def __init__(self, timeout_seconds: int = 30) -> None:
        self.timeout_seconds = timeout_seconds

    def collect(self, source_url: str) -> list[PricingItem]:
        try:
            with urllib.request.urlopen(source_url, timeout=self.timeout_seconds) as response:
                html_text = response.read().decode("utf-8", errors="ignore")
        except urllib.error.URLError as exc:
            raise PricingCollectorError(f"Failed to fetch pricing page: {exc}") from exc

        items = self.collect_from_html(source_url, html_text)
        if not items:
            raise PricingCollectorError("Pricing page did not yield any recognizable price blocks.")
        return items

    def collect_from_html(self, source_url: str, html_text: str) -> list[PricingItem]:
        plain_text = _strip_html(html_text)
        matches = list(PRICE_PATTERN.finditer(plain_text))
        items: list[PricingItem] = []

        for index, match in enumerate(matches[:10], start=1):
            amount = match.group("amount")
            start = max(match.start() - 80, 0)
            end = min(match.end() + 120, len(plain_text))
            context = plain_text[start:end].strip()
            normalized_currency = "USD"
            external_id = f"pricing-{index}-{amount}"
            title = f"Pricing snapshot {index} at {amount} {normalized_currency}"
            content_hash = hashlib.sha256(context.encode("utf-8")).hexdigest()
            items.append(
                PricingItem(
                    external_id=external_id,
                    title=title,
                    url=source_url,
                    content=context,
                    published_at=None,
                    author_name=None,
                    content_hash=content_hash,
                    raw_payload={
                        "price_amount": amount,
                        "currency": normalized_currency,
                        "context": context,
                        "source_url": source_url,
                    },
                )
            )

        return items
