create table if not exists rejected_events (
  id uuid primary key default gen_random_uuid(),
  raw_document_id uuid references raw_documents(id) on delete set null,
  structured_event_id uuid references structured_events(id) on delete set null,
  service_slug text,
  source_url text,
  rejection_reason text not null,
  rejection_details jsonb not null default '{}'::jsonb,
  rejected_at timestamptz not null default now()
);

alter table events
  add column if not exists event_status text not null default 'detected',
  add column if not exists version integer not null default 1;

alter table events
  add constraint events_status_chk
  check (event_status in ('detected', 'validated', 'decided', 'published', 'archived'));

create index if not exists rejected_events_rejected_at_idx
  on rejected_events(rejected_at desc);

create index if not exists events_status_idx
  on events(event_status, detected_at desc);
