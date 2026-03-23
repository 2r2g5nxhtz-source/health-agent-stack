from __future__ import annotations

import hashlib
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass


class RSSCollectorError(RuntimeError):
    pass


@dataclass(frozen=True)
class RSSItem:
    external_id: str
    title: str
    url: str
    content: str
    published_at: str | None
    author_name: str | None
    content_hash: str
    raw_payload: dict


class RSSCollector:
    def __init__(self, timeout_seconds: int = 30) -> None:
        self.timeout_seconds = timeout_seconds

    def collect(self, source_url: str) -> list[RSSItem]:
        try:
            with urllib.request.urlopen(source_url, timeout=self.timeout_seconds) as response:
                xml_text = response.read().decode("utf-8", errors="ignore")
        except urllib.error.URLError as exc:
            raise RSSCollectorError(f"Failed to fetch RSS feed: {exc}") from exc

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            raise RSSCollectorError(f"Failed to parse RSS feed: {exc}") from exc

        channel = root.find("channel")
        if channel is None:
            raise RSSCollectorError("RSS feed missing channel element.")

        items: list[RSSItem] = []
        for item in channel.findall("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            guid = (item.findtext("guid") or link or title).strip()
            description = (item.findtext("description") or "").strip()
            pub_date = (item.findtext("pubDate") or "").strip() or None
            author_name = (item.findtext("author") or "").strip() or None
            text = description or title
            content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            items.append(
                RSSItem(
                    external_id=guid,
                    title=title or link,
                    url=link or source_url,
                    content=text,
                    published_at=pub_date,
                    author_name=author_name,
                    content_hash=content_hash,
                    raw_payload={"title": title, "link": link, "description": description, "pubDate": pub_date},
                )
            )
        return items
