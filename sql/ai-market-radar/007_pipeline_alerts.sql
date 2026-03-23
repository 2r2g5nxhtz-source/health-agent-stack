create table if not exists pipeline_alerts (
  id uuid primary key default gen_random_uuid(),
  alert_level text not null check (alert_level in ('INFO', 'WARNING', 'ERROR')),
  stage text not null,
  message text not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists pipeline_alerts_level_created_idx
  on pipeline_alerts(alert_level, created_at desc);
