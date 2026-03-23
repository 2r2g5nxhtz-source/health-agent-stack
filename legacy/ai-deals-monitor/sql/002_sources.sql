create table if not exists sources (
  id uuid primary key default gen_random_uuid(),
  service text not null,
  source_type text not null,
  source_url text not null unique,
  is_active boolean not null default true,
  priority integer not null default 100,
  fetch_interval text not null default 'daily',
  parser_type text not null default 'generic',
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists sources_active_priority_idx
  on sources(is_active, priority asc, created_at asc);

create table if not exists source_fetch_logs (
  id uuid primary key default gen_random_uuid(),
  run_id uuid references monitor_runs(id) on delete set null,
  source_id uuid references sources(id) on delete cascade,
  source_url text not null,
  http_status integer,
  fetch_status text not null,
  error_message text,
  response_size integer,
  fetched_at timestamptz not null default now()
);

create index if not exists source_fetch_logs_run_idx
  on source_fetch_logs(run_id, fetched_at desc);

create or replace function set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists trg_sources_updated_at on sources;
create trigger trg_sources_updated_at
before update on sources
for each row execute function set_updated_at();

insert into sources (service, source_type, source_url, priority, fetch_interval, parser_type, notes)
values
  ('ChatGPT', 'official_pricing', 'https://chatgpt.com/pricing', 10, 'daily', 'html_pricing', 'Official pricing page'),
  ('Claude', 'official_pricing', 'https://www.anthropic.com/pricing', 10, 'daily', 'html_pricing', 'Official pricing page'),
  ('Gemini', 'official_pricing', 'https://one.google.com/about/ai-premium/', 15, 'daily', 'html_pricing', 'Official pricing page'),
  ('AppSumo', 'deal_marketplace', 'https://appsumo.com/search/?q=AI', 20, 'daily', 'html_marketplace', 'Marketplace search'),
  ('StackSocial', 'deal_marketplace', 'https://www.stacksocial.com/search?query=ai', 25, 'daily', 'html_marketplace', 'Marketplace search'),
  ('Reddit ChatGPT', 'community_json', 'https://www.reddit.com/r/ChatGPT.json', 30, 'daily', 'reddit_json', 'Community feed')
on conflict (source_url) do update set
  service = excluded.service,
  source_type = excluded.source_type,
  priority = excluded.priority,
  fetch_interval = excluded.fetch_interval,
  parser_type = excluded.parser_type,
  notes = excluded.notes,
  is_active = true;
