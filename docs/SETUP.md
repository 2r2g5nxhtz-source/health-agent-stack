# Health Agent Setup

## Scope

This setup guide is for the current Health Agent stack:

- iPhone app in `ios/HealthAgentIOS`
- private webhook receiver in `n8n`
- optional Telegram alerts
- optional CSV logging

It does not use the archived `AI Deals Monitor` assets under `legacy/ai-deals-monitor/`.

## Prerequisites

- macOS with Xcode installed
- an iPhone with Apple Health data
- `xcodegen` installed if you want to regenerate the Xcode project
- a running `n8n` instance reachable from your iPhone

## Important for n8n 2.x

- keep an explicit `webhookId` on the webhook node
- after importing a workflow, publish it
- restart n8n after publishing
- run `scripts/smoke-test.sh` before using the iPhone app

## 1. Prepare the webhook endpoint

Create or choose an `n8n` webhook that accepts `POST` requests with JSON.

Expected path example:

```text
https://YOUR_N8N_HOST/webhook/apple-health
```

For local testing on your LAN, an HTTP URL is acceptable if you trust the network:

```text
http://YOUR_LOCAL_IP:5678/webhook/apple-health
```

Secure workflow example:

```text
https://YOUR_N8N_HOST/webhook/apple-health-secure
```

## 2. Open the iPhone app

```bash
cd ios/HealthAgentIOS
xcodegen generate
open HealthAgentIOS.xcodeproj
```

In Xcode:

1. Choose your Apple Developer team in `Signing & Capabilities`
2. Run the app on your iPhone
3. Grant Apple Health read access when prompted

## 3. Configure the webhook in the app

On first launch, the app starts with an empty webhook field.

Before tapping `Send Now`:

1. Paste your own webhook URL
2. If you use the secure workflow, enter the same shared secret that is configured in `n8n`
3. Tap `Save Settings`
4. Trigger a manual send

## 4. Verify the received payload

Current payload shape:

```json
{
  "heart_rate": 79,
  "glucose": 112,
  "weight": 81.9,
  "sleep_hours": 5.5,
  "timestamp": "2026-03-15T08:00:00Z"
}
```

Possible `null` values are expected when a sample is unavailable.

## 5. Add downstream automation

Typical `n8n` flow:

```text
Webhook
-> Code or Set node for normalization
-> IF / rules for thresholds
-> Telegram notification
-> CSV or database logging
```

Suggested first thresholds:

- `heart_rate > 85`
- `glucose_mmol > 6.0`
- `sleep_hours < 6`

The secure workflow converts incoming glucose from `mg/dL` to `mmol/L` by dividing by `18` before threshold checks.

## 6. Export an IPA if needed

```bash
cd ios/HealthAgentIOS
./scripts/export-ipa.sh
```

Before export, set your signing team and replace `REPLACE_WITH_YOUR_TEAM_ID` in:

- `ios/HealthAgentIOS/export/ExportOptions.ad-hoc.plist`
- `ios/HealthAgentIOS/export/ExportOptions.app-store.plist`

## Operational Notes

- Keep webhook endpoints private where possible
- Prefer HTTPS outside your local network
- Do not commit real webhook URLs, tokens, or health payloads
- Treat Apple Health data as sensitive personal information

## Smoke Test

After the stack is running, you can verify the end-to-end path with one command:

```bash
cd /Users/merdan/notebook\ lm\ claude/nenado
chmod +x scripts/smoke-test.sh
./scripts/smoke-test.sh
```

Optional overrides:

```bash
WEBHOOK_URL="http://127.0.0.1:5678/webhook/apple-health" ./scripts/smoke-test.sh
HEALTH_SECRET="your-secret" ./scripts/smoke-test.sh
N8N_CONTAINER="n8n" ./scripts/smoke-test.sh
```

Secure workflow example:

```bash
WEBHOOK_URL="http://127.0.0.1:5678/webhook/apple-health-secure" \
HEALTH_SECRET="your-secret" \
./scripts/smoke-test.sh
```

The smoke test checks:

- Docker availability
- `n8n` container state
- webhook reachability
- test payload delivery
- workflow visibility inside `n8n`

## Daily Summary Workflow

`workflows/health-agent-daily-summary.workflow.json` adds two scheduled Telegram messages:

| Time | Behaviour |
|---|---|
| 08:00 | Sends a morning summary with the latest readings (heart rate, glucose, weight, sleep). If today's data has not arrived yet, the message says so and prompts you to open the app. |
| 21:00 | Sends a reminder only if no data was received that day. Silent if data already arrived. |

### Prerequisites

The daily summary reads the CSV file produced by the secure webhook workflow using an `executeCommand` node. Add this variable to your n8n Docker environment before importing:

```
N8N_ALLOW_EXEC=true
```

Without it the `executeCommand` node will fail silently.

### Import and activate

1. Import `health-agent-daily-summary.workflow.json` into n8n
2. Publish the workflow (same as the webhook workflow — required for n8n 2.x)
3. Restart n8n
4. Verify by triggering the `Morning Schedule` node manually in the n8n UI

### Timezone

The workflow uses the `TZ` environment variable to display times in your local timezone. Make sure `TZ` is set in your n8n Docker env (e.g. `TZ=Asia/Dubai`). Defaults to `UTC`.

### CSV path

The workflow reads `/data/health-agent/health-log.csv` by default. This matches `HEALTH_AGENT_CSV_PATH` in the env example. If you changed the path, update the `command` field in both `Read CSV` nodes.

## Workflow Recovery

If the `n8n` production webhook stops responding after a workflow import or update, run:

```bash
cd /Users/merdan/notebook\ lm\ claude/nenado
chmod +x scripts/reactivate-health-workflow.sh
./scripts/reactivate-health-workflow.sh
```

This recovery script:

- reactivates the `Apple Health Logger` workflow
- restarts `n8n`
- waits for the webhook to register again
- runs the smoke test automatically

## Safe Workflow Updates

To update the live `n8n` workflow from a JSON export with backup + validation:

```bash
cd /Users/merdan/notebook\ lm\ claude/nenado
chmod +x scripts/update-n8n-workflow.sh
./scripts/update-n8n-workflow.sh
```

Optional overrides:

```bash
WORKFLOW_FILE="$PWD/workflows/health-agent-webhook-secure-csv.workflow.json" ./scripts/update-n8n-workflow.sh
WORKFLOW_ID="your-workflow-id" ./scripts/update-n8n-workflow.sh
N8N_CONTAINER="n8n" ./scripts/update-n8n-workflow.sh
```

The update script:

- exports a backup of the current workflow
- copies the new workflow JSON into the container
- imports it into `n8n`
- runs the recovery flow
- validates the production webhook with the smoke test
