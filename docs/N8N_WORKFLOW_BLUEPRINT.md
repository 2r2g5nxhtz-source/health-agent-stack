# n8n workflow blueprint

## Узлы

1. `Schedule Trigger`
   - Every day
   - Time: `08:00`
   - Timezone: `UTC`

2. `Read Binary File` или `Code`
   - Загружает `/data/services.json`

3. `HTTP Request - pricing pages`
   - По одному запросу на источник
   - Возвращает HTML/JSON/RSS

4. `HTTP Request - deals sources`
   - AppSumo
   - StackSocial
   - Reddit JSON
   - Product Hunt / RSS

5. `Code - normalize`
   - превращает все ответы в единый формат:
   ```json
   {
     "service": "Claude",
     "source": "official_pricing",
     "source_url": "https://example.com",
     "title": "Claude Pro annual discount",
     "raw_text": "...",
     "price_before": "$240",
     "price_now": "$192"
   }
   ```

6. `Code - dedupe`
   - нормализует URL
   - строит `content_hash`
   - убирает повторы

7. `Postgres - select previous`
   - читает последний `report`
   - читает активные сделки

8. `OpenAI`
   - prompt: `/data/prompts/production-prompt-v6.1.md`
   - inputs:
     - `CURRENT_DATE`
     - `PREV_REPORT`
     - `MODE`
     - `SERVICES_JSON`
     - `RAW_ITEMS_JSON`

9. `Postgres - write results`
   - `insert monitor_runs`
   - `upsert deals`
   - `insert deal_events`
   - `insert reports`

10. `Telegram`
    - отправляет summary message

## Полезные SQL-операции

### Последний отчёт

```sql
select summary_text
from reports
order by report_date desc
limit 1;
```

### Активные сделки

```sql
select *
from deals
where status = 'active'
order by last_seen_at desc;
```
