# Event Detector Design

`Event Detector` is the system boundary that converts unstructured market text into normalized events.

Pipeline:

```text
collectors -> raw_documents -> GPT structurer -> normalized candidate events
-> validation -> dedupe hints -> scoring input -> events
```

## Detector responsibilities

The detector must answer four questions for each raw document:

1. Is there an event at all?
2. If yes, what `event_type` and `event_class` is it?
3. What exact structured values can be extracted?
4. How confident are we that the extraction is correct?

## Supported taxonomy

### Event types

- `discount`
- `credits`
- `price_up`
- `price_down`
- `new_model`
- `new_plan`
- `free_tier`
- `ltd`
- `launch`
- `region_launch`

### Event classes

- `fact`: hard measurable change, usually from snapshots
- `deal`: commercial opportunity like discount or LTD
- `credit`: bonus credits, free usage, expanded free limits
- `signal`: product move like new model or new plan
- `info`: broader market launch or release info

## Detector architecture

The detector should run in two stages.

### Stage 1: rule pre-classifier

Cheap deterministic signals identify likely event families before GPT runs.

Examples:

- `% off`, `save`, `discount`, `annual` -> likely `discount`
- `credits`, `$10 credit`, `bonus` -> likely `credits`
- `now costs`, `price increased`, `from $20 to $25` -> `price_up`
- `price reduced`, `now $15`, `down from` -> `price_down`
- `introduced`, `launches`, `now available`, `announces` -> `launch` or `new_model`
- `new plan`, `team plan`, `enterprise tier` -> `new_plan`
- `lifetime deal`, `one-time payment` -> `ltd`

Purpose:

- lower GPT ambiguity
- reduce prompt size
- provide fallback when model output is weak

### Stage 2: GPT structurer

GPT receives:

- service metadata
- source metadata
- raw title
- raw body
- optional pre-classifier hints
- optional latest known facts from `price_snapshots` or `model_snapshots`

GPT returns a strict JSON object with candidate events and extraction confidence.

## GPT output contract

Recommended top-level response:

```json
{
  "document_summary": "Pricing page now shows ChatGPT Plus at $25/month.",
  "has_market_event": true,
  "reasoning_short": "Explicit price change on official pricing page.",
  "candidate_events": [
    {
      "event_type": "price_up",
      "event_class": "fact",
      "title": "ChatGPT Plus price increased",
      "description": "ChatGPT Plus changed from $20/month to $25/month.",
      "service_name": "ChatGPT",
      "plan_name": "Plus",
      "model_name": null,
      "region": null,
      "old_value": 20,
      "new_value": 25,
      "value_unit": "usd_month",
      "currency": "USD",
      "start_date": "2026-03-23",
      "end_date": null,
      "expires_at": null,
      "confidence": 97,
      "evidence": [
        "ChatGPT Plus is now $25/month",
        "Previous archived price reference was $20/month"
      ],
      "dedupe_components": {
        "service": "chatgpt",
        "event_type": "price_up",
        "plan": "plus",
        "value": "25.00",
        "effective_date": "2026-03-23"
      },
      "should_create_price_snapshot": true,
      "should_create_model_snapshot": false
    }
  ]
}
```

## Extraction rules by event type

### `discount`

Extract:

- `plan_name`
- `old_value`
- `new_value`
- discount percent if present
- `start_date`
- `end_date`
- region if limited

Confidence is high when:

- source is official or marketplace
- old and new price both present
- expiry date present

### `credits`

Extract:

- `new_value`
- `currency` or credit unit
- eligibility or plan
- expiry if stated

Confidence drops when:

- credit amount is implied but not explicit
- source is social/community only

### `price_up` and `price_down`

Extract:

- `plan_name`
- `old_value`
- `new_value`
- billing period
- effective date

Hard rule:

- if both old and new values are absent, detector should not emit price events

### `new_model`

Extract:

- `model_name`
- `model_family`
- access plan
- release date
- capability text like context or modality

Important:

- a document saying "improved GPT-4o" is not automatically `new_model`
- detector should emit `new_model` only if a newly named model or newly available variant is explicit

### `new_plan`

Extract:

- `plan_name`
- plan audience
- included limits or seat count
- launch/effective date

### `free_tier`

Extract:

- old free limit
- new free limit
- unit such as messages, credits, tokens, renders

### `ltd`

Extract:

- one-time price
- included credits or limits
- expiry if promotional

### `launch` and `region_launch`

Extract:

- product or feature name
- region when applicable
- launch date

## Confidence scoring

Confidence should be a 0-100 integer.

Suggested formula:

```text
confidence =
  source_reliability_weight
  + explicit_value_bonus
  + explicit_date_bonus
  + entity_match_bonus
  - ambiguity_penalty
  - rumor_penalty
```

Heuristic bands:

- `90-100`: official source, explicit values, explicit entity, low ambiguity
- `75-89`: reliable source, mostly explicit, minor inference
- `50-74`: partially inferred, missing one important field
- `<50`: noisy or speculative, should usually stay out of notifications

Suggested source weight anchors:

- official/pricing: `+40`
- marketplace: `+30`
- community: `+15`
- social: `+10`

## New vs not new

The detector itself should not be the final authority on novelty.

Instead it should produce:

- normalized type
- normalized values
- dedupe components
- confidence

Novelty is then decided by the delta engine:

1. Build canonical key from detector output
2. Compare against active or recent events
3. Compare against latest relevant snapshot
4. If unchanged, mark `is_delta = false`
5. If materially changed, create or update the event

Examples:

- same discount seen again on Reddit -> not new
- same price still present on pricing page -> not new
- price changed from 20 to 25 -> new delta
- existing event gains an expiry date -> update existing event, not duplicate

## Validation layer after GPT

Never write GPT output directly to `events`.

Post-processing checks should enforce:

- `event_type` is from allowed taxonomy
- `event_class` matches event type
- numeric fields are parseable
- dates are valid ISO dates
- `old_value != new_value` for price changes
- `end_date >= start_date` when both exist
- confidence is clamped to `0..100`

If validation fails:

- keep document in `raw_documents`
- mark extraction failure in app logs or run logs
- optionally retry with a narrower prompt

## Recommended persistence flow

### For price-related events

1. detector emits `price_up`, `price_down`, `discount`, or `free_tier`
2. validator normalizes currency, plan, and billing period
3. system writes `price_snapshots`
4. delta engine compares with prior snapshot
5. if changed, upsert `events`

### For model-related events

1. detector emits `new_model`
2. validator normalizes model family and name
3. system writes `model_snapshots`
4. delta engine checks if this model already exists
5. if not, create `events`

## Report-facing fields

To make reports simple, each emitted event should end up with:

- `event_type`
- `event_class`
- `title`
- `description`
- `old_value`
- `new_value`
- `currency`
- `confidence`
- `score`
- `detected_at`

## Recommended next implementation artifacts

The next code pieces should be:

1. `003_seed_services_and_sources.sql`
2. detector JSON schema for strict model output
3. prompt template for GPT structurer
4. post-processing validator
5. canonical key builder for dedupe

If we keep this contract stable, the rest of the system becomes much easier to build and test.
