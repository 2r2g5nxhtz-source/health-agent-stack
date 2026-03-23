from __future__ import annotations

from dataclasses import replace

from ai_market_radar.models import StructuredEventRecord


SERVICE_ALIASES = {
    "chatgpt": "chatgpt",
    "openai chatgpt": "chatgpt",
    "openai": "openai",
    "claude": "claude",
    "anthropic claude": "claude",
    "gemini": "gemini",
    "google gemini": "gemini",
    "copilot": "copilot",
    "microsoft copilot": "copilot",
    "cursor": "cursor",
    "midjourney": "midjourney",
    "perplexity": "perplexity",
    "elevenlabs": "elevenlabs",
    "runway": "runway",
    "heygen": "heygen",
    "mistral": "mistral",
    "grok": "grok",
    "replit": "replit",
    "suno": "suno",
    "pika": "pika",
    "invideo": "invideo",
}

MODEL_ALIASES = {
    "gpt4.1": "gpt-4.1",
    "gpt 4.1": "gpt-4.1",
    "gpt-4.1": "gpt-4.1",
    "gpt4o": "gpt-4o",
    "gpt 4o": "gpt-4o",
    "gpt-4o": "gpt-4o",
    "claude 3.7": "claude-3.7",
    "claude-3.7": "claude-3.7",
    "claude 3.7 sonnet": "claude-3.7-sonnet",
    "claude-3.7-sonnet": "claude-3.7-sonnet",
    "gemini 1.5 pro": "gemini-1.5-pro",
    "gemini-1.5-pro": "gemini-1.5-pro",
}

PLAN_ALIASES = {
    "plus": "plus",
    "chatgpt plus": "plus",
    "pro": "pro",
    "creator": "creator",
    "team": "team",
    "enterprise": "enterprise",
    "free": "free",
}

REGION_ALIASES = {
    "global": "global",
    "worldwide": "global",
    "us": "us",
    "usa": "us",
    "united states": "us",
    "eu": "eu",
    "europe": "eu",
}

EVENT_TYPE_ALIASES = {
    "price change": "price_up",
    "discount": "discount",
    "credits": "credits",
    "price up": "price_up",
    "price down": "price_down",
    "new model": "new_model",
    "new plan": "new_plan",
    "free tier": "free_tier",
    "ltd": "ltd",
    "launch": "launch",
    "region launch": "region_launch",
    "context": "context",
    "model price": "model_price",
    "rate limit": "rate_limit",
}

EVENT_CLASS_BY_TYPE = {
    "discount": "deal",
    "credits": "credit",
    "price_up": "fact",
    "price_down": "fact",
    "new_model": "signal",
    "new_plan": "signal",
    "free_tier": "credit",
    "ltd": "deal",
    "launch": "info",
    "region_launch": "info",
    "context": "fact",
    "model_price": "fact",
    "rate_limit": "fact",
}


def _normalize_key(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.strip().lower().replace("_", " ").replace("-", " ").split())
    return normalized or None


def normalize_service(value: str | None) -> str | None:
    key = _normalize_key(value)
    if key is None:
        return None
    return SERVICE_ALIASES.get(key, key.replace(" ", "_"))


def normalize_model(value: str | None) -> str | None:
    key = _normalize_key(value)
    if key is None:
        return None
    return MODEL_ALIASES.get(key, key.replace(" ", "-"))


def normalize_plan(value: str | None) -> str | None:
    key = _normalize_key(value)
    if key is None:
        return None
    return PLAN_ALIASES.get(key, key.replace(" ", "_"))


def normalize_currency(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip().upper() or None


def normalize_region(value: str | None) -> str | None:
    key = _normalize_key(value)
    if key is None:
        return None
    return REGION_ALIASES.get(key, key.replace(" ", "_"))


def normalize_event_type(value: str | None, *, old_value=None, new_value=None) -> str | None:
    key = _normalize_key(value)
    if key is None:
        return None
    normalized = EVENT_TYPE_ALIASES.get(key, key.replace(" ", "_"))
    if normalized == "price_up" and old_value is not None and new_value is not None and new_value < old_value:
        return "price_down"
    return normalized


def normalize_event_class(event_type: str | None, event_class: str | None) -> str | None:
    normalized_type = normalize_event_type(event_type)
    if normalized_type is None:
        return _normalize_key(event_class)
    return EVENT_CLASS_BY_TYPE.get(normalized_type, _normalize_key(event_class))


def normalize_structured_event(event: StructuredEventRecord) -> StructuredEventRecord:
    normalized_type = normalize_event_type(event.event_type, old_value=event.old_value, new_value=event.new_value)
    return replace(
        event,
        service_slug=normalize_service(event.service_slug) or event.service_slug,
        event_type=normalized_type or event.event_type,
        event_class=normalize_event_class(normalized_type, event.event_class) or event.event_class,
        plan_name=normalize_plan(event.plan_name),
        model_name=normalize_model(event.model_name),
        currency=normalize_currency(event.currency),
        region=normalize_region(event.region) or "global",
    )
