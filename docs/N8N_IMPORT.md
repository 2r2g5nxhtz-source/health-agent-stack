# Импорт workflow в n8n

## Файл

Готовый export JSON:

- `workflows/ai-deals-monitor.workflow.json`

## Как импортировать

1. Открой `n8n`
2. Нажми `Workflows`
3. Нажми `Import from file`
4. Выбери `workflows/ai-deals-monitor.workflow.json`

## Что нужно настроить после импорта

Workflow использует env-переменные:

- `OPENAI_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `DEALS_MONITOR_MODE`

Они уже предусмотрены в `/Users/merdan/notebook lm claude/nenado/.env.example:1`.

## Что делает текущая версия

- запускается каждый день в `08:00 UTC`
- запрашивает несколько стартовых источников
- нормализует ответы
- отправляет сырые данные в OpenAI Responses API
- собирает Telegram-отчёт
- шлёт его в Telegram через Bot API

## Ограничения текущего JSON

- `PREV_REPORT` пока пустой
- Postgres delta engine пока не подключён внутрь workflow
- список источников зашит в `Build Monitor Config`

## Что лучше сделать следующим шагом

1. заменить список источников на чтение из `/data/services.json`
2. добавить `Postgres` node для загрузки прошлого отчёта
3. добавить `Postgres` node для `upsert` в таблицы `deals`, `deal_events`, `reports`
4. добавить retry/error branch для нестабильных источников
