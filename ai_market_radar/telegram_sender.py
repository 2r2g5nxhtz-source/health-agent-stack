from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request


class TelegramSenderError(RuntimeError):
    pass


class TelegramSender:
    def __init__(self, bot_token: str | None = None, chat_id: str | None = None) -> None:
        self.bot_token = bot_token or os.getenv("AI_MARKET_RADAR_TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("AI_MARKET_RADAR_TELEGRAM_CHAT_ID")
        if not self.bot_token or not self.chat_id:
            raise TelegramSenderError(
                "Missing AI_MARKET_RADAR_TELEGRAM_BOT_TOKEN or AI_MARKET_RADAR_TELEGRAM_CHAT_ID."
            )

    def send_markdown(self, text: str) -> dict:
        endpoint = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = urllib.parse.urlencode(
            {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": "true",
            }
        ).encode("utf-8")
        request = urllib.request.Request(endpoint, data=payload, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            raise TelegramSenderError(f"Telegram API error {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise TelegramSenderError(f"Failed to reach Telegram API: {exc}") from exc
