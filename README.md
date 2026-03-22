# Health Agent

Local-first Apple Health automation stack with `n8n`, Telegram alerts, CSV logging, and a native iPhone `HealthKit` app.

## Why This Exists

Health Agent is designed for people who want their Apple Health data to stay on their own devices and infrastructure while still getting useful automations:

- Apple Health data collection on iPhone
- local or self-hosted workflow automation via `n8n`
- Telegram alerts for abnormal readings
- CSV logging for simple long-term tracking
- optional local AI layer via `Ollama`

## Features

- native iPhone app for Apple Health -> webhook sync
- editable webhook URL directly in the app
- safe handling of missing Health samples
- `n8n` webhook workflow with alert logic
- Telegram notifications for threshold breaches
- CSV logging for historical records
- local-first architecture

## Repository Layout

| Path | Purpose |
|---|---|
| `ios/HealthAgentIOS` | SwiftUI iPhone app |
| `docs` | setup and payload documentation for Health Agent |
| `workflows` | importable `n8n` workflow exports for Health Agent |
| `deploy` | starter deployment templates for the Health Agent webhook flow |
| `legacy/ai-deals-monitor` | archived AI Deals Monitor stack, workflows, SQL, deploy scripts, and docs |
| `health-stack-guide.html` | interactive setup guide |

## Repository Status

The iOS app in `ios/HealthAgentIOS` is the current Health Agent implementation.

The older `AI Deals Monitor` project has been moved under `legacy/ai-deals-monitor/` so the repository root stays focused on Health Agent. Legacy assets are preserved for reference only and are not the source of truth for the Health Agent app.

## Current Stack

| Service | Address | Status |
|---|---|---|
| n8n | `localhost:5678` | running |
| Ollama | `localhost:11434` | running |
| Open WebUI | `localhost:3000` | running |
| Webhook | configurable in the app | user-specified |

## iPhone App

The iOS app lives in [`ios/HealthAgentIOS`](./ios/HealthAgentIOS).

It currently:

- reads latest `heart_rate`
- reads latest `glucose`
- reads latest `weight`
- totals `sleep_hours` for the last 24 hours
- posts data to a configurable `n8n` webhook
- sends `null` instead of crashing when a sample is missing

Example payload:

```json
{
  "heart_rate": 79,
  "glucose": 112,
  "weight": 81.9,
  "sleep_hours": 5.5,
  "timestamp": "2026-03-15T08:00:00Z"
}
```

## Quick Start

### Start the local stack

```bash
docker start n8n open-webui && ollama serve &
```

Configure your own webhook endpoint in the app before tapping `Send Now`. The app no longer ships with a prefilled network target.

### Open the iPhone app in Xcode

```bash
cd ios/HealthAgentIOS
xcodegen generate
open HealthAgentIOS.xcodeproj
```

Then in Xcode:

1. Select your Apple Developer team in `Signing & Capabilities`
2. Run the app on your iPhone
3. Grant Health access on first launch

## Build IPA

An export helper is included:

```bash
cd ios/HealthAgentIOS
./scripts/export-ipa.sh
```

Before exporting:

1. Open the Xcode project once
2. Set your signing team
3. Replace `REPLACE_WITH_YOUR_TEAM_ID` in:
   - `ios/HealthAgentIOS/export/ExportOptions.ad-hoc.plist`
   - or `ios/HealthAgentIOS/export/ExportOptions.app-store.plist`

## Workflow Logic

The current webhook payload is designed to fit the downstream `n8n` flow:

```text
iPhone HealthKit app
-> POST /webhook/apple-health
-> n8n
-> code node / rules
-> Telegram alerts
-> CSV log
```

Example alert thresholds already used in the stack:

- `heart_rate > 85`
- `glucose > 110`
- `sleep_hours < 6`

## Roadmap

- TestFlight-ready iOS distribution
- background sync from iPhone
- Apple Watch-friendly flows
- better charts and local trends
- reusable workflow templates
- setup wizard for new users

## Open Source

Contributions, issues, and improvements are welcome.

- See [`CONTRIBUTING.md`](./CONTRIBUTING.md)
- See [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md)
- See [`SECURITY.md`](./SECURITY.md)

## Notes

- This project is local-first by design.
- Apple Health data stays on your Apple devices and your own infrastructure unless you choose otherwise.
- Telegram and CSV processing happen downstream in your own automation stack.

### n8n 2.x

For n8n 2.x, keep an explicit `webhookId` on webhook nodes and publish the workflow after import. After publishing, restart n8n and run `scripts/smoke-test.sh` to confirm the production webhook is registered and reachable.

## License

MIT. See [`LICENSE`](./LICENSE).
