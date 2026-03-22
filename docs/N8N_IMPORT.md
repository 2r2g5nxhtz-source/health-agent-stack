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

- expects `X-Health-Agent-Secret` header
- rejects unauthorized requests with `401`
- appends each received payload to a CSV log path

## Thresholds Included

- `heart_rate > 85`
- `glucose > 110`
- `sleep_hours < 6`

## Import Steps

1. Open your `n8n` editor
2. Create a new workflow
3. Import either:
   - `workflows/health-agent-webhook.workflow.json`
   - or `workflows/health-agent-webhook-secure-csv.workflow.json`
4. Save the workflow
5. Copy the webhook URL from the `Apple Health Webhook` node
6. Paste that URL into the iPhone app
7. If you imported the advanced workflow, also enter the same shared secret in the app
8. Tap `Save Settings`

## Environment Variables For The Advanced Version

- `HEALTH_AGENT_WEBHOOK_SECRET`
- `HEALTH_AGENT_CSV_PATH`
- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` if you want alerts

Example request header:

```text
X-Health-Agent-Secret: your-shared-secret
```

## Recommended Follow-Up

- add authentication or network restrictions in front of the webhook
- add CSV or database logging after `Build Alerts`
- tune thresholds to your own health workflow
