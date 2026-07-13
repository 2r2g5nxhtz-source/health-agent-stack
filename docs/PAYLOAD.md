# Health Payload

Health Agent sends a single JSON object per sync (manual or background delivery).

## Schema

```json
{
  "heart_rate": 70,
  "glucose": 100,
  "weight": 75.0,
  "sleep_hours": 8.0,
  "hrv": 50,
  "resting_heart_rate": 60,
  "spo2": 98,
  "respiratory_rate": 16.0,
  "steps": 10000,
  "timestamp": "2026-03-15T08:00:00Z"
}
```

## Fields

- `heart_rate`: latest heart rate sample in beats per minute, or `null`
- `glucose`: latest blood glucose sample in mg/dL, or `null`
- `weight`: latest body mass sample in kilograms, or `null`
- `sleep_hours`: total sleep in the last 24 hours, rounded to one decimal place, or `null`
- `hrv`: latest heart rate variability (SDNN) in milliseconds, or `null`
- `resting_heart_rate`: latest resting heart rate in beats per minute, or `null`
- `spo2`: latest blood oxygen saturation as a percentage (0–100), or `null`
- `respiratory_rate`: latest respiratory rate in breaths per minute, or `null`
- `steps`: step count total, or `null`
- `timestamp`: ISO 8601 timestamp generated at send time

## Notes

- Missing values are represented as `null` instead of failing the request
- The payload contains no user identifier by default
- If you need per-device attribution, add it downstream in your private automation stack
