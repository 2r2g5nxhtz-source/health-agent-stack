alter table raw_documents
  add column if not exists status text not null default 'new';

alter table raw_documents
  add constraint raw_documents_status_chk
  check (status in ('new', 'processed', 'error'));

alter table structured_events
  add constraint structured_events_processing_status_chk
  check (processing_status in ('extracted', 'validated', 'decided', 'finalized', 'ignored', 'rejected', 'error'));

alter table events
  drop constraint if exists events_status_chk;

alter table events
  add constraint events_status_chk
  check (event_status in ('detected', 'validated', 'decided', 'published', 'active', 'expired', 'archived'));

create index if not exists raw_documents_status_idx
  on raw_documents(status, fetched_at asc);

create table if not exists pipeline_logs (
  id uuid primary key default gen_random_uuid(),
  stage text not null,
  status text not null,
  message text not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists pipeline_logs_stage_created_idx
  on pipeline_logs(stage, created_at desc);

create table if not exists pipeline_metrics (
  id uuid primary key default gen_random_uuid(),
  metric_date date not null,
  metric_name text not null,
  metric_value numeric(18,2) not null,
  created_at timestamptz not null default now()
);

create unique index if not exists pipeline_metrics_date_name_key
  on pipeline_metrics(metric_date, metric_name);
