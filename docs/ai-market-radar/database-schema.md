# AI Market Radar Database Schema

This schema shifts the system from a narrow deals monitor into an event-centric market intelligence database.

## Design principles

- `events` is the core table because Telegram and reports should be driven by market changes, not raw articles.
- `price_snapshots` and `model_snapshots` store factual history, so events can be derived from hard deltas.
- `raw_documents` preserves collector output for re-parsing, debugging, and prompt iteration.
- `event_history` and `event_notifications` make delta detection and anti-spam behavior explicit.
- `services.priority_tier` supports different scan cadences for Tier 1 through Tier 4.

## Core entities

### `services`

Registry of products being monitored.

Important fields:

- `slug`, `name`
- `priority_tier` for scan scheduling
- `category` and `market_segment`

Examples:

- ChatGPT, Claude, Gemini, Cursor as Tier 1
- Product Hunt-discovered tools as Tier 4

### `sources`

Defines where data comes from.

Examples:

- official pricing page
- official changelog
- Product Hunt page
- Reddit feed
- AppSumo listing

### `raw_documents`

Collector output before structuring.

Use it for:

- rerunning the GPT structurer
- parser debugging
- provenance and auditing

## Fact tables

### `price_snapshots`

Stores observed prices and plan limits over time.

Best for:

- price increase / decrease detection
- credits changed
- free tier limit changed
- annual vs monthly comparisons

Suggested unique logical grain:

- one row per `service + plan_name + billing_period + observed_at`

### `model_snapshots`

Stores observed model availability and related capabilities.

Best for:

- `new_model`
- model retirement
- context window change
- plan access change

Suggested unique logical grain:

- one row per `service + model_name + observed_at`

## Event system

### `events`

This is the main intelligence layer.

Recommended event types:

- `discount`
- `credits`
- `new_model`
- `price_up`
- `price_down`
- `new_plan`
- `ltd`
- `free_limit`
- `launch`

Why both `dedupe_key` and `canonical_fingerprint`:

- `dedupe_key` blocks inserting the exact same active event twice
- `canonical_fingerprint` helps merge semantically identical events seen from different sources

Suggested dedupe composition:

- `service_slug`
- `event_type`
- normalized value
- normalized plan or model name
- normalized effective date

Example:

```text
chatgpt|price_down|plus|monthly|20.00|2026-03-23
```

### `event_links`

Connects events to underlying facts.

Examples:

- `price_down` event linked to the new `price_snapshot`
- `new_model` event linked to the discovered `model_snapshot`

### `event_history`

Tracks lifecycle changes for delta detection.

Useful change types:

- `created`
- `updated`
- `expired`
- `reactivated`
- `score_changed`

### `event_notifications`

Prevents Telegram spam.

Before sending:

1. Check whether the event is already sent to the same channel for the same day.
2. Skip if already sent.
3. Send only if `is_delta = true` or score crossed a threshold.

## Reports

### `reports`

Stores final generated reports.

Typical report types:

- `daily_market_report`
- `weekly_market_report`
- `tier_1_digest`

## How delta detection works with this schema

### Pricing flow

1. Collector stores raw page in `raw_documents`
2. Parser extracts current plan facts into `price_snapshots`
3. Delta engine compares latest snapshot against previous snapshot
4. If changed, create or update an `events` row
5. Write lifecycle row to `event_history`
6. If not yet sent, log delivery in `event_notifications`

### Model flow

1. Collector stores release note or changelog in `raw_documents`
2. Structurer extracts model facts into `model_snapshots`
3. Detector compares current model set to previous model set
4. If new model appears, emit `new_model` event

## Scoring model

The schema separates score dimensions so scoring can evolve later:

- `base_score`: event-type baseline
- `importance_score`: tier, urgency, value magnitude
- `final_score`: final ranking used by reports and Telegram

Suggested base scores:

- `credits`: 80
- `discount`: 70
- `ltd`: 85
- `new_model`: 60
- `price_down`: 65
- `price_up`: 40
- `launch`: 50

## Recommended next migrations

After this initial schema, the next SQL steps should be:

1. seed `services` and `sources` for Tier 1 to Tier 3
2. add enums or check constraints for `event_type`, `status`, and `run_type`
3. add SQL views for `active_events`, `urgent_events`, and `latest_prices`
4. add materialized stats for daily market summaries

## Minimal MVP read model

If we want to ship fast, the report generator only needs:

- active events from `events`
- latest prices from `price_snapshots`
- latest models from `model_snapshots`
- already-sent markers from `event_notifications`

That gives enough for daily digests, score sorting, and Telegram deduplication.
