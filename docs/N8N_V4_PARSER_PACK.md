# n8n v4: Parser Pack

## Файл

- `workflows/ai-deals-monitor-v4-parser-pack.workflow.json`

## Что улучшено

- есть parser pack в ноде `Parser Pack Normalize`
- отдельно обрабатываются:
  - `reddit_json`
  - `rss`
  - `generic/html`
- до OpenAI извлекаются:
  - `title`
  - `price_before`
  - `price_now`
  - `discount_text`
  - `deal_type`
  - `content_hash`

## Зачем это нужно

Раньше LLM получал почти сырой текст. Теперь он получает более структурированные сигналы, поэтому:

- меньше шум
- ниже token usage
- лучше dedupe
- выше шанс корректно найти реальные deals

## Как использовать parser types

В таблице `sources` поле `parser_type` может быть:

- `reddit_json`
- `rss`
- `html_pricing`
- `html_marketplace`
- `generic`

## Примеры

### Reddit

```sql
update sources
set parser_type = 'reddit_json'
where source_url = 'https://www.reddit.com/r/ChatGPT.json';
```

### RSS

```sql
update sources
set parser_type = 'rss'
where source_url = 'https://www.producthunt.com/feed';
```

### Pricing page

```sql
update sources
set parser_type = 'html_pricing'
where source_url = 'https://chatgpt.com/pricing';
```

## Ограничения

- HTML parsing всё ещё regex-based, не DOM-based
- price extraction эвристическая
- RSS parser ожидает стандартные `item/title/link/description`
- Reddit parser использует только top-level posts

## Что делать дальше

1. сделать `v5` с site-specific parsers
2. добавить blacklist/whitelist keywords
3. добавить confidence score до LLM
4. отправлять в LLM только top candidate items
