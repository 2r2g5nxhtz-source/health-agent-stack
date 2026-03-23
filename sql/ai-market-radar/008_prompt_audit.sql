create table if not exists llm_extraction_logs (
  id uuid primary key default gen_random_uuid(),
  raw_document_id uuid references raw_documents(id) on delete set null,
  detector_version text not null,
  llm_provider text,
  llm_model text,
  prompt_text text not null,
  response_text text,
  response_json jsonb,
  input_tokens integer not null default 0,
  output_tokens integer not null default 0,
  estimated_cost_usd numeric(12,6) not null default 0,
  latency_ms integer,
  created_at timestamptz not null default now()
);

create index if not exists llm_extraction_logs_created_idx
  on llm_extraction_logs(created_at desc);

create index if not exists llm_extraction_logs_raw_document_idx
  on llm_extraction_logs(raw_document_id, created_at desc);
