# AI Deals Monitor MVP

## Что внутри

- `docker-compose.yml` — `n8n` + `PostgreSQL` + `Caddy`
- `.env.example` — переменные окружения
- `services.json` — стартовый список сервисов
- `sql/001_init.sql` — схема БД
- `prompts/production-prompt-v6.1.md` — шаблон промпта для LLM

## 1. Подготовка VPS

Минимум:

- 2 vCPU
- 4 GB RAM
- Ubuntu 22.04 или 24.04
- DNS A-record на домен `n8n.example.com`

## 2. Установка Docker

Используй официальный Docker Engine и Compose Plugin.

## 3. Подготовка проекта

```bash
cp .env.example .env
```

Заполни:

- `N8N_HOST`
- `ACME_EMAIL`
- `POSTGRES_PASSWORD`
- `OPENAI_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## 4. Запуск

```bash
docker compose up -d
```

Проверка:

```bash
docker compose ps
```

После этого открой:

```text
https://YOUR_N8N_DOMAIN
```

При первом входе `n8n` предложит создать owner account.

## 5. Источники данных для MVP

Начни с 5–10 источников:

- официальные pricing pages
- AppSumo
- StackSocial
- Reddit JSON / RSS
- Product Hunt / RSS

Старайся сначала использовать JSON, RSS и официальные страницы, а не агрессивный HTML scraping.

## 6. Рекомендуемый workflow в n8n

```text
Schedule Trigger (daily, 08:00 UTC)
-> HTTP Request: official pricing pages
-> HTTP Request: deal sources
-> Code: normalize items
-> Code: dedupe + hash
-> Postgres: load previous active deals/report
-> OpenAI Chat / Responses
-> Postgres: upsert deals + insert report
-> Telegram: send message
```

## 7. Логика delta engine

На каждом запуске:

1. нормализуй сырые элементы
2. вычисли `content_hash`
3. сравни с активными сделками в `deals`
4. если hash новый — `NEW`
5. если hash известен, но изменились цена/текст — `CHANGED`
6. если ранее активная сделка не встретилась несколько запусков подряд — `EXPIRED`

## 8. Формат Telegram-отчёта

```text
AI TOOLS DEAL MONITOR
Date: 2026-03-11

Top deals today:
1. Claude Team — 20% off annual plan
2. Runway — limited promo for creators
3. Perplexity — education discount

New deals: 3
Changed: 1
Expired: 2
```

## 9. Что добавить после MVP

- retries / timeouts
- proxy layer для сложных сайтов
- weekly/monthly scan pools
- anti-duplicate rules по URL + hash
- healthcheck workflow
- separate table for sources
- admin dashboard
