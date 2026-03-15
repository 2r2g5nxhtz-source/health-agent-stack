# Health Agent

Personal health automation stack built around Apple Health, n8n, Telegram alerts, and a lightweight iPhone app.

## What This Repo Contains

- `ios/HealthAgentIOS` — SwiftUI iPhone app that reads Apple Health data and sends it to `n8n`
- `workflows/` — n8n workflow exports and workflow variants
- `docs/` — setup notes and deployment guides
- `deploy/` — server and reverse-proxy scripts
- `sql/` — supporting SQL files

## Current Stack

| Service | Address | Status |
|---|---|---|
| n8n | `localhost:5678` | running |
| Ollama | `localhost:11434` | running |
| Open WebUI | `localhost:3000` | running |
| Webhook | `http://192.168.1.105:5678/webhook/apple-health` | active |

## iPhone App

The iOS app lives in [`ios/HealthAgentIOS`](./ios/HealthAgentIOS) and does the following:

- reads latest `heart_rate`
- reads latest `glucose`
- reads latest `weight`
- totals `sleep_hours` for the last 24 hours
- sends JSON to the configured `n8n` webhook
- handles missing samples safely by sending `null` instead of crashing
- lets you edit and save the webhook URL inside the app

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

### Local stack

```bash
docker start n8n open-webui && ollama serve &
```

### iPhone app

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

The repo includes an export script:

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

## Notes

- This project is designed for local-first health automation.
- Apple Health data stays on your Apple devices and your own infrastructure.
- Telegram alerts and CSV logging are handled downstream in `n8n`.

## License

MIT. See [`LICENSE`](./LICENSE).
