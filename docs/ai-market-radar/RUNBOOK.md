# AI Market Radar Runbook

This runbook describes the minimum operational path for the current project state.

## Reality check

This is not production-ready yet.

Current status:

- schema and pipeline code exist
- unit tests exist
- runtime entrypoints exist
- dockerized smoke test now exists and can run end-to-end when prerequisites are available
- live database, live LLM, and live Telegram delivery are still not verified for a real external provider in this repository

Use this runbook as an operator guide for a controlled first deployment, not as proof of production-readiness.

## Required environment

Copy [/.env.example](/Users/merdan/notebook%20lm%20claude/nenado/.env.example) into your own environment manager and set all required values.

Required variables:

- `AI_MARKET_RADAR_DATABASE_URL`
- `AI_MARKET_RADAR_LLM_API_KEY`
- `AI_MARKET_RADAR_LLM_MODEL`
- `AI_MARKET_RADAR_TELEGRAM_BOT_TOKEN`
- `AI_MARKET_RADAR_TELEGRAM_CHAT_ID`

Optional variables:

- `AI_MARKET_RADAR_LLM_BASE_URL`
- `AI_MARKET_RADAR_LLM_INPUT_PRICE_PER_1K`
- `AI_MARKET_RADAR_LLM_OUTPUT_PRICE_PER_1K`

## Docker bootstrap

Local database bootstrap is available in [docker-compose.ai-market-radar.yml](/Users/merdan/notebook%20lm%20claude/nenado/docker-compose.ai-market-radar.yml).

Example:

```bash
docker compose -f docker-compose.ai-market-radar.yml up -d
```

This starts:

- Postgres on `localhost:55432`
- pgAdmin on `localhost:55433`

## Database setup

Apply migrations in this exact order:

1. [001_market_radar_init.sql](/Users/merdan/notebook%20lm%20claude/nenado/sql/ai-market-radar/001_market_radar_init.sql)
2. [002_event_taxonomy.sql](/Users/merdan/notebook%20lm%20claude/nenado/sql/ai-market-radar/002_event_taxonomy.sql)
3. [003_pipeline_state.sql](/Users/merdan/notebook%20lm%20claude/nenado/sql/ai-market-radar/003_pipeline_state.sql)
4. [004_seed_services_and_sources.sql](/Users/merdan/notebook%20lm%20claude/nenado/sql/ai-market-radar/004_seed_services_and_sources.sql)
5. [005_event_pipeline_hardening.sql](/Users/merdan/notebook%20lm%20claude/nenado/sql/ai-market-radar/005_event_pipeline_hardening.sql)
6. [006_runtime_ops.sql](/Users/merdan/notebook%20lm%20claude/nenado/sql/ai-market-radar/006_runtime_ops.sql)
7. [007_pipeline_alerts.sql](/Users/merdan/notebook%20lm%20claude/nenado/sql/ai-market-radar/007_pipeline_alerts.sql)

Example:

```bash
psql "$AI_MARKET_RADAR_DATABASE_URL" -f sql/ai-market-radar/001_market_radar_init.sql
psql "$AI_MARKET_RADAR_DATABASE_URL" -f sql/ai-market-radar/002_event_taxonomy.sql
psql "$AI_MARKET_RADAR_DATABASE_URL" -f sql/ai-market-radar/003_pipeline_state.sql
psql "$AI_MARKET_RADAR_DATABASE_URL" -f sql/ai-market-radar/004_seed_services_and_sources.sql
psql "$AI_MARKET_RADAR_DATABASE_URL" -f sql/ai-market-radar/005_event_pipeline_hardening.sql
psql "$AI_MARKET_RADAR_DATABASE_URL" -f sql/ai-market-radar/006_runtime_ops.sql
psql "$AI_MARKET_RADAR_DATABASE_URL" -f sql/ai-market-radar/007_pipeline_alerts.sql
```

## First controlled run

Run each step manually before any cron automation:

```bash
python -m ai_market_radar.cli ingest
python -m ai_market_radar.cli detect
python -m ai_market_radar.cli pipeline
python -m ai_market_radar.cli report --no-telegram
```

Smoke-test shortcut:

```bash
bash scripts/smoke-ai-market-radar.sh
```

Only after the report looks sane:

```bash
python -m ai_market_radar.cli report
```

## Acceptance checks

Minimum checks after a manual run:

- `raw_documents` contains new rows after `ingest`
- `structured_events` contains rows after `detect`
- `rejected_events / structured_events < 0.30`
- `events` contains rows after `pipeline`
- `reports` contains one row after `report`
- `pipeline_logs` contains one `completed` row per executed stage
- `pipeline_alerts` contains no unexpected `ERROR` rows

Golden-eval shortcut:

```bash
python -m ai_market_radar.eval_runner
```

## Suggested cron

Use only after manual checks succeed.

```cron
0 * * * * cd "/Users/merdan/notebook lm claude/nenado" && python -m ai_market_radar.cli ingest
10 * * * * cd "/Users/merdan/notebook lm claude/nenado" && python -m ai_market_radar.cli detect
20 * * * * cd "/Users/merdan/notebook lm claude/nenado" && python -m ai_market_radar.cli pipeline
0 2 * * * cd "/Users/merdan/notebook lm claude/nenado" && python -m ai_market_radar.cli expire
0 8 * * * cd "/Users/merdan/notebook lm claude/nenado" && python -m ai_market_radar.cli report
```

## Known gaps

These are not solved yet:

- no live-provider integration test across external LLM + Telegram
- no provider failover
- no circuit breaker
- no pricing collector yet
- no weekly report specialization
- no precision/recall dashboard beyond the initial golden scaffold

## Immediate next hardening tasks

Priority order:

1. expand golden dataset from 5 to 30-50 cases
2. add provider-level integration run with real LLM and masked prompt/response logging
3. Telegram failure alerts and report delivery retries
4. pricing collector
5. weekly analytics report
