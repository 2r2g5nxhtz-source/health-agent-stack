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
- `glucose > 110`
- `sleep_hours < 6`

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

The smoke test checks:

- Docker availability
- `n8n` container state
- webhook reachability
- test payload delivery
- workflow visibility inside `n8n`

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
