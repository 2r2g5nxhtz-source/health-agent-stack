create extension if not exists pgcrypto;

create table if not exists services (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  name text not null,
  category text not null,
  website_url text,
  priority_tier smallint not null check (priority_tier between 1 and 4),
  market_segment text,
  is_active boolean not null default true,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists monitor_runs (
  id uuid primary key default gen_random_uuid(),
  run_type text not null,
  run_scope text not null,
  tier smallint check (tier between 1 and 4),
  status text not null default 'running',
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  items_fetched_count integer not null default 0,
  items_parsed_count integer not null default 0,
  events_created_count integer not null default 0,
  events_updated_count integer not null default 0,
  notes text
);

create table if not exists sources (
  id uuid primary key default gen_random_uuid(),
  service_id uuid references services(id) on delete cascade,
  source_type text not null,
  source_url text not null unique,
  parser_type text not null,
  priority integer not null default 100,
  fetch_frequency text not null,
  is_active boolean not null default true,
  last_fetched_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists raw_documents (
  id uuid primary key default gen_random_uuid(),
  run_id uuid references monitor_runs(id) on delete set null,
  source_id uuid references sources(id) on delete cascade,
  external_id text,
  title text,
  author_name text,
  published_at timestamptz,
  source_url text not null,
  content_hash text not null,
  raw_text text,
  raw_payload jsonb not null default '{}'::jsonb,
  fetched_at timestamptz not null default now()
);

create unique index if not exists raw_documents_source_external_key
  on raw_documents(source_id, external_id)
  where external_id is not null;

create index if not exists raw_documents_content_hash_idx
  on raw_documents(content_hash);

create table if not exists price_snapshots (
  id uuid primary key default gen_random_uuid(),
  service_id uuid not null references services(id) on delete cascade,
  run_id uuid references monitor_runs(id) on delete set null,
  source_id uuid references sources(id) on delete set null,
  plan_name text not null,
  billing_period text not null,
  currency_code text not null default 'USD',
  price_amount numeric(12,2),
  price_amount_usd numeric(12,2),
  seats_included integer,
  credits_included numeric(14,2),
  usage_limit_text text,
  is_active boolean not null default true,
  observed_at timestamptz not null default now(),
  raw_payload jsonb not null default '{}'::jsonb
);

create index if not exists price_snapshots_service_observed_idx
  on price_snapshots(service_id, observed_at desc);

create table if not exists model_snapshots (
  id uuid primary key default gen_random_uuid(),
  service_id uuid not null references services(id) on delete cascade,
  run_id uuid references monitor_runs(id) on delete set null,
  source_id uuid references sources(id) on delete set null,
  model_name text not null,
  model_family text,
  model_version text,
  capability_type text,
  access_plan text,
  status text not null default 'active',
  context_window integer,
  output_limit integer,
  released_at timestamptz,
  observed_at timestamptz not null default now(),
  raw_payload jsonb not null default '{}'::jsonb
);

create index if not exists model_snapshots_service_observed_idx
  on model_snapshots(service_id, observed_at desc);

create table if not exists events (
  id uuid primary key default gen_random_uuid(),
  service_id uuid references services(id) on delete set null,
  run_id uuid references monitor_runs(id) on delete set null,
  source_id uuid references sources(id) on delete set null,
  raw_document_id uuid references raw_documents(id) on delete set null,
  event_type text not null,
  event_subtype text,
  title text not null,
  summary text,
  event_date timestamptz not null,
  expires_at timestamptz,
  status text not null default 'active',
  value_text text,
  value_numeric numeric(14,2),
  value_currency text,
  urgency smallint not null default 0 check (urgency between 0 and 5),
  base_score integer not null default 0,
  importance_score integer not null default 0,
  final_score integer not null default 0,
  dedupe_key text not null,
  canonical_fingerprint text not null,
  first_seen_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  last_changed_at timestamptz not null default now(),
  is_delta boolean not null default true,
  metadata jsonb not null default '{}'::jsonb
);

create unique index if not exists events_dedupe_key_key
  on events(dedupe_key);

create unique index if not exists events_canonical_fingerprint_key
  on events(canonical_fingerprint);

create index if not exists events_service_score_idx
  on events(service_id, final_score desc, event_date desc);

create index if not exists events_status_expiry_idx
  on events(status, expires_at asc);

create table if not exists event_links (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null references events(id) on delete cascade,
  price_snapshot_id uuid references price_snapshots(id) on delete cascade,
  model_snapshot_id uuid references model_snapshots(id) on delete cascade,
  relationship_type text not null,
  created_at timestamptz not null default now()
);

create table if not exists event_history (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null references events(id) on delete cascade,
  run_id uuid references monitor_runs(id) on delete set null,
  change_type text not null,
  previous_payload jsonb,
  new_payload jsonb not null default '{}'::jsonb,
  changed_at timestamptz not null default now()
);

create index if not exists event_history_event_changed_idx
  on event_history(event_id, changed_at desc);

create table if not exists event_notifications (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null references events(id) on delete cascade,
  channel text not null,
  notification_date date not null,
  sent_at timestamptz not null default now(),
  delivery_status text not null default 'sent',
  payload jsonb not null default '{}'::jsonb
);

create unique index if not exists event_notifications_daily_key
  on event_notifications(event_id, channel, notification_date);

create table if not exists reports (
  id uuid primary key default gen_random_uuid(),
  run_id uuid references monitor_runs(id) on delete set null,
  report_type text not null,
  report_date date not null,
  top_event_ids uuid[] not null default '{}',
  report_markdown text not null,
  report_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create unique index if not exists reports_type_date_key
  on reports(report_type, report_date);

create or replace function set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists trg_services_updated_at on services;
create trigger trg_services_updated_at
before update on services
for each row execute function set_updated_at();

drop trigger if exists trg_sources_updated_at on sources;
create trigger trg_sources_updated_at
before update on sources
for each row execute function set_updated_at();
