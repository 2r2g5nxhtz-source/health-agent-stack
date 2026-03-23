# Canonicalizer And Delta Engine

This layer is the decision core of the system.

Pipeline:

```text
structured_events -> canonicalizer -> delta engine -> events
```

## Why this layer exists

`Event Detector` extracts meaning from text, but it should not decide whether something is truly new.

That decision belongs to deterministic system logic:

- canonicalization normalizes the extracted event
- delta compares it to existing state
- only then do we create, update, or ignore an event

## Staging model

Use `structured_events` as the only write target for GPT extraction.

It stores:

- the extracted event candidate
- detector confidence
- evidence
- canonicalization fields
- processing status

This keeps extraction separate from final market state.

## Canonicalizer responsibilities

The canonicalizer turns messy extraction output into a normalized identity.

It should normalize:

- `service_id`
- `event_type`
- `event_class`
- `plan_name`
- `model_name`
- `region`
- currency
- numeric precision
- effective date semantics

It should also build:

- `canonical_key`
- `canonical_payload`

## Canonical key rules

The canonical key should be stable enough to identify the same underlying state, but specific enough to distinguish material changes.

Recommended key parts:

- service
- event type
- scope key
- value key

### Scope key

Scope should be built from whichever dimensions matter for that event:

- `plan_name` when pricing or credits are plan-specific
- `model_name` when model-specific
- `region` for region launches
- otherwise `global`

### Value key

Value key should represent the current state or offer identity, depending on event type.

Examples:

- `price_up`: `25.00_usd_month`
- `credits`: `10.00_usd`
- `new_model`: `gpt-4.1`
- `launch`: `global`

## Different event types need different delta behavior

This is the critical rule.

### Stateful event types

These represent current market state and should usually `UPDATE`:

- `price_up`
- `price_down`
- `free_tier`

For these, canonical key should be scope-based, not value-based.

Examples:

- `chatgpt|price_change|plus|global`
- `claude|free_tier|global|global`

Then delta compares old and new values:

- if current value differs -> `UPDATE`
- if same -> `IGNORE`

### Offer or release event types

These should usually create distinct `NEW` events:

- `discount`
- `credits`
- `new_model`
- `new_plan`
- `ltd`
- `launch`
- `region_launch`

For these, canonical key should include the distinguishing value or identifier.

Examples:

- `chatgpt|discount|plus|20.00_usd_month|2026-03-23`
- `claude|credits|pro|10.00_usd|2026-03-23`
- `openai|new_model|gpt-4.1`
- `perplexity|launch|labs`

Then delta behavior becomes:

- if exact key exists -> `IGNORE`
- if not -> `NEW`

## Canonical key patterns by event type

### Price changes

Use a stateful scope key:

```text
{service}|price_state|{plan_or_global}|{region_or_global}
```

Stored value lives in:

- `structured_events.new_value`
- `event_state.current_value`

This avoids creating infinite new events for every repeated observation of the same current price.

### Free tier changes

Use:

```text
{service}|free_tier_state|{plan_or_global}|{region_or_global}
```

### Discounts

Use:

```text
{service}|discount|{plan_or_global}|{new_value}|{currency}|{start_date}|{end_date_or_open}
```

Every materially different promo becomes a new event.

### Credits

Use:

```text
{service}|credits|{plan_or_global}|{new_value}|{currency}|{start_date}
```

### New model

Use:

```text
{service}|new_model|{model_name}
```

### New plan

Use:

```text
{service}|new_plan|{plan_name}
```

### Launch

Use:

```text
{service}|launch|{normalized_title_or_feature}
```

### Region launch

Use:

```text
{service}|region_launch|{region}|{normalized_title_or_feature}
```

## Delta engine responsibilities

The delta engine decides one of three actions:

- `NEW`
- `UPDATE`
- `IGNORE`

It should evaluate both:

- prior final events
- `event_state`

## Delta engine algorithm

### Step 1

Reject low-confidence candidates.

Recommended threshold:

- if `final_confidence < 0.5` -> ignore candidate

### Step 2

Load `event_state` by `canonical_key`.

### Step 3

Apply event-type behavior.

Pseudo-code:

```python
def decide(candidate, state, existing_event):
    if candidate.final_confidence < 0.5:
        return "IGNORE", "low_confidence"

    if candidate.event_type in {"price_up", "price_down", "free_tier"}:
        if state is None:
            return "NEW", "no_existing_state"
        if materially_equal(state.current_value, candidate.new_value, candidate.currency):
            return "IGNORE", "same_state"
        return "UPDATE", "state_changed"

    if candidate.event_type in {"discount", "credits", "new_model", "new_plan", "ltd", "launch", "region_launch"}:
        if existing_event is not None:
            return "IGNORE", "same_offer_or_release"
        return "NEW", "new_offer_or_release"

    return "IGNORE", "unsupported_type"
```

## Why `event_state` matters

Without `event_state`, stateful comparisons become harder and slower.

`event_state` gives a fast answer to:

- what is the current Plus price?
- what is the current free tier limit?
- what is the current known state for this scope?

Recommended row grain:

- one row per `service + event_type + scope`

Examples:

- ChatGPT + price state + Plus
- Claude + free tier + global

## Decision outputs

Every processed staging row should produce a `delta_decisions` row.

This is useful for:

- debugging
- audits
- prompt tuning
- understanding why something was ignored

Decision reasons should be explicit, for example:

- `low_confidence`
- `same_state`
- `same_offer_or_release`
- `no_existing_state`
- `state_changed`

## Final confidence model

Recommended calculation:

```text
final_confidence = gpt_confidence * 0.6 + source_confidence * 0.4
```

Suggested source anchors:

- official: `0.90`
- pricing: `0.95`
- AppSumo-like marketplace: `0.85`
- Product Hunt: `0.75`
- Reddit: `0.60`
- Twitter/X: `0.50`

## Final write behavior

### On `NEW`

1. insert row into `events`
2. insert row into `event_history` with `created`
3. upsert `event_state`
4. mark `structured_events.processing_status = 'finalized'`

### On `UPDATE`

1. update existing row in `events`
2. insert row into `event_history` with `updated`
3. update `event_state`
4. mark `structured_events.processing_status = 'finalized'`

### On `IGNORE`

1. do not notify
2. write `delta_decisions`
3. mark `structured_events.processing_status = 'ignored'`

## Important design note about price trackers

Price tracking should prefer deterministic parsers:

```text
pricing page -> parser -> price_snapshots -> delta -> price event
```

This is better than asking GPT to infer prices from arbitrary text.

GPT is still useful for:

- launch announcements
- new plans
- model releases
- promo language

## Recommended next implementation units

The next concrete code pieces should be:

1. SQL seed for Tier 1 to Tier 3 services and sources
2. strict JSON schema for `structured_events`
3. canonical key builder function
4. delta decision worker
5. scorer using final events, not staging rows
