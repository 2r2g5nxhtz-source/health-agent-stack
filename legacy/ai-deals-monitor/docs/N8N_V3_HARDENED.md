# n8n v3: Hardened workflow

## Новые файлы

- `sql/002_sources.sql`
- `workflows/ai-deals-monitor-v3-hardened.workflow.json`

## Что нового в v3

- источники читаются из таблицы `sources`
- каждый fetch логируется в `source_fetch_logs`
- есть явная ветка `HTTP OK?`
- неуспешные источники пишутся в БД отдельно
- цикл fetch идёт через `Split In Batches`
- можно управлять приоритетом и активностью источников без правки workflow

## Как включить

1. Применить SQL:
   - `sql/001_init.sql`
   - `sql/002_sources.sql`
2. Импортировать:
   - `workflows/ai-deals-monitor-v3-hardened.workflow.json`
3. Назначить `Postgres` credential всем Postgres-нодам

## Как управлять источниками

### Отключить источник

```sql
update sources
set is_active = false
where source_url = 'https://www.stacksocial.com/search?query=ai';
```

### Поднять приоритет

```sql
update sources
set priority = 5
where source_url = 'https://chatgpt.com/pricing';
```

### Добавить новый источник

```sql
insert into sources (service, source_type, source_url, priority, fetch_interval, parser_type, notes)
values ('Perplexity', 'official_pricing', 'https://www.perplexity.ai/pro', 12, 'daily', 'html_pricing', 'Official pricing');
```

## Ограничения

- retry сейчас мягкий: failed source логируется и цикл идёт дальше
- нет отдельного second-attempt fetch
- парсеры пока универсальные, без site-specific extraction
- OpenAI всё ещё получает довольно сырой текст

## Следующий уровень

1. добавить `sources` admin UI в Notion/Supabase
2. сделать отдельные parser-ноды для `reddit_json`, `rss`, `pricing_html`
3. добавить alert, если подряд упало больше N источников
4. добавить weekly/monthly выборку по `fetch_interval`
