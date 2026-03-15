create extension if not exists pgcrypto;

create table if not exists monitor_runs (
  id uuid primary key default gen_random_uuid(),
  run_started_at timestamptz not null default now(),
  run_finished_at timestamptz,
  status text not null default 'running',
  mode text not null,
  raw_items_count integer not null default 0,
  normalized_items_count integer not null default 0,
  notes text
);

create table if not exists deals (
  id uuid primary key default gen_random_uuid(),
  service text not null,
  source text not null,
  source_url text not null,
  title text not null,
  deal_type text,
  price_before text,
  price_now text,
  discount_text text,
  score integer,
  status text not null default 'active',
  content_hash text not null,
  first_seen_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  expired_at timestamptz,
  last_run_id uuid references monitor_runs(id) on delete set null
);

create unique index if not exists deals_content_hash_key on deals(content_hash);
create index if not exists deals_service_idx on deals(service);
create index if not exists deals_status_idx on deals(status);
create index if not exists deals_last_seen_at_idx on deals(last_seen_at desc);

create table if not exists deal_events (
  id uuid primary key default gen_random_uuid(),
  deal_id uuid not null references deals(id) on delete cascade,
  run_id uuid references monitor_runs(id) on delete set null,
  event_type text not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists deal_events_deal_id_idx on deal_events(deal_id);
create index if not exists deal_events_created_at_idx on deal_events(created_at desc);

create table if not exists reports (
  id uuid primary key default gen_random_uuid(),
  run_id uuid unique references monitor_runs(id) on delete set null,
  report_date date not null,
  summary_text text not null,
  report_json jsonb not null,
  new_count integer not null default 0,
  changed_count integer not null default 0,
  expired_count integer not null default 0,
  created_at timestamptz not null default now()
);

create index if not exists reports_report_date_idx on reports(report_date desc);
