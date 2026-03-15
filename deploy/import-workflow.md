# Как быстро довести до полностью рабочего состояния

## Что уже автоматизировано

- установка Docker
- открытие firewall
- загрузка проекта на VPS
- запуск `PostgreSQL`, `n8n`, `Caddy`
- применение SQL-миграций

## Что всё ещё нужно один раз руками

1. Создать owner account в `n8n`
2. Создать `Postgres` credential
3. Импортировать workflow:
   - `workflows/ai-deals-monitor-v4-parser-pack.workflow.json`
4. Сохранить workflow и запустить manual run

Это 5–10 минут после деплоя.
