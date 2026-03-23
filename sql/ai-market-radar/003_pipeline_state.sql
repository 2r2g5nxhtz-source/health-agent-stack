create table if not exists structured_events (
  id uuid primary key default gen_random_uuid(),
  raw_document_id uuid not null references raw_documents(id) on delete cascade,
  service_id uuid references services(id) on delete set null,
  source_id uuid references sources(id) on delete set null,
  run_id uuid references monitor_runs(id) on delete set null,
  event_type event_type_enum not null,
  event_class event_class_enum not null,
  title text not null,
  description text,
  plan_name text,
  model_name text,
  region text,
  old_value numeric(14,2),
  new_value numeric(14,2),
  currency text,
  start_date date,
  end_date date,
  source_url text,
  gpt_confidence numeric(5,4) not null check (gpt_confidence between 0 and 1),
  source_confidence numeric(5,4) not null check (source_confidence between 0 and 1),
  final_confidence numeric(5,4) not null check (final_confidence between 0 and 1),
  evidence jsonb not null default '[]'::jsonb,
  detector_version text,
  canonical_key text,
  canonical_payload jsonb not null default '{}'::jsonb,
  processing_status text not null default 'extracted',
  extracted_at timestamptz not null default now(),
  canonicalized_at timestamptz,
  processed_at timestamptz
);

create index if not exists structured_events_status_idx
  on structured_events(processing_status, extracted_at asc);

create index if not exists structured_events_service_type_idx
  on structured_events(service_id, event_type, extracted_at desc);

create index if not exists structured_events_canonical_key_idx
  on structured_events(canonical_key);

create table if not exists event_state (
  id uuid primary key default gen_random_uuid(),
  service_id uuid not null references services(id) on delete cascade,
  event_type event_type_enum not null,
  event_class event_class_enum not null,
  state_scope text not null default 'global',
  plan_name text,
  model_name text,
  region text,
  current_value numeric(14,2),
  currency text,
  current_event_id uuid references events(id) on delete set null,
  last_structured_event_id uuid references structured_events(id) on delete set null,
  canonical_key text not null unique,
  state_payload jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

create index if not exists event_state_service_type_idx
  on event_state(service_id, event_type, updated_at desc);

create table if not exists delta_decisions (
  id uuid primary key default gen_random_uuid(),
  structured_event_id uuid not null references structured_events(id) on delete cascade,
  existing_event_id uuid references events(id) on delete set null,
  canonical_key text not null,
  decision text not null check (decision in ('NEW', 'UPDATE', 'IGNORE')),
  decision_reason text,
  previous_payload jsonb,
  new_payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create unique index if not exists delta_decisions_structured_event_key
  on delta_decisions(structured_event_id);
