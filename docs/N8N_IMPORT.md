# Import The Health Workflow

## Workflow File

Use:

`workflows/health-agent-webhook.workflow.json`

Advanced version:

`workflows/health-agent-webhook-secure-csv.workflow.json`

## What It Does

- receives `POST /webhook/apple-health`
- normalizes numeric and nullable fields
- checks simple threshold rules
- sends a Telegram alert only if:
  - at least one threshold is triggered
  - `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are configured in `n8n`
- returns a JSON response to the caller

The advanced version additionally:

- receives `POST /webhook/apple-health-secure`
- expects `X-Health-Agent-Secret` header
- rejects unauthorized requests with `401`
- appends each received payload to a CSV log path

## Thresholds Included

- `heart_rate > 85`
- `glucose_mmol > 6.0`
- `sleep_hours < 6`

Incoming glucose is normalized from the older `mg/dL` format to `mmol/L` by dividing by `18` inside the workflow.

## Import Steps

1. Open your `n8n` editor
2. Create a new workflow
3. Import either:
   - `workflows/health-agent-webhook.workflow.json`
   - or `workflows/health-agent-webhook-secure-csv.workflow.json`
4. Save the workflow
5. Publish or activate the workflow
6. Restart `n8n` if you are on `n8n 2.x`
7. Copy the webhook URL from the `Apple Health Webhook` node
8. Paste that URL into the iPhone app
9. If you imported the advanced workflow, also enter the same shared secret in the app
10. Tap `Save Settings`

## Environment Variables For The Advanced Version

- `HEALTH_AGENT_WEBHOOK_SECRET`
- `HEALTH_AGENT_CSV_PATH`
- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` if you want alerts

Recommended `.env` values:

```text
HEALTH_AGENT_SECURE_WEBHOOK_URL=https://n8n.example.com/webhook/apple-health-secure
HEALTH_AGENT_WEBHOOK_SECRET=replace-with-a-long-random-secret
HEALTH_AGENT_CSV_PATH=/data/health-agent/health-log.csv
```

Example request header:

```text
X-Health-Agent-Secret: your-shared-secret
```

## Secure Smoke Test

You can validate the secure webhook with:

```bash
cd /Users/merdan/notebook\ lm\ claude/nenado
WEBHOOK_URL="http://127.0.0.1:5678/webhook/apple-health-secure" \
HEALTH_SECRET="your-shared-secret" \
./scripts/smoke-test.sh
```

If the secret is wrong, the smoke test should fail with `HTTP 401`.

## Recommended Follow-Up

- add authentication or network restrictions in front of the webhook
- add CSV or database logging after `Build Alerts`
- tune thresholds to your own health workflow
