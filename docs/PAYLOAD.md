# Health Payload

Health Agent sends a single JSON object per manual sync.

## Schema

```json
{
  "heart_rate": 70,
  "glucose": 100,
  "weight": 75.0,
  "sleep_hours": 8.0,
  "timestamp": "2026-03-15T08:00:00Z"
}
```

## Fields

- `heart_rate`: latest heart rate sample in beats per minute, or `null`
- `glucose`: latest blood glucose sample in mg/dL, or `null`
- `weight`: latest body mass sample in kilograms, or `null`
- `sleep_hours`: total sleep in the last 24 hours, rounded to one decimal place, or `null`
- `timestamp`: ISO 8601 timestamp generated at send time

## Notes

- Missing values are represented as `null` instead of failing the request
- The payload contains no user identifier by default
- If you need per-device attribution, add it downstream in your private automation stack
