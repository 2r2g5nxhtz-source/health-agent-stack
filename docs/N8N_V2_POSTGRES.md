# n8n v2: Postgres Delta Engine

## Файл

- `workflows/ai-deals-monitor-v2-postgres.workflow.json`

## Что добавлено

- `monitor_runs` создаётся в начале запуска
- читается прошлый `report`
- читаются активные сделки из `deals`
- OpenAI получает `ACTIVE_DEALS_JSON` и `PREV_REPORT`
- результаты записываются обратно в `deals`, `deal_events`, `reports`
- сделки из блока `expired` переводятся в статус `expired`

## Что настроить после импорта

1. Создать `Postgres` credential в `n8n`
2. Открыть 4 Postgres-ноды и выбрать этот credential:
   - `Create Run`
   - `Load Previous Data`
   - `Upsert Deals`
   - `Expire Missing Deals`
   - `Insert Report + Finish Run`
3. Проверить env:
   - `OPENAI_API_KEY`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `DEALS_MONITOR_MODE`

## Ограничения v2

- список источников пока ещё зашит в `Build Sources`
- парсинг pricing/deal-страниц пока базовый
- `content_hash` строится из очищенного текста, поэтому возможны ложные `CHANGED`
- нет отдельной error branch для failed sources

## Что рекомендую сделать дальше

1. вынести sources в отдельную таблицу `sources`
2. читать services/sources из БД или файла `/data/services.json`
3. добавить `If` branch для пустых/ошибочных ответов
4. добавить `retry` и `backoff`
5. разделить official pricing и marketplace/community parsers
