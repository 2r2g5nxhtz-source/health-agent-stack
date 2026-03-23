do $$
begin
  if not exists (select 1 from pg_type where typname = 'event_type_enum') then
    create type event_type_enum as enum (
      'discount',
      'credits',
      'price_up',
      'price_down',
      'new_model',
      'new_plan',
      'free_tier',
      'ltd',
      'launch',
      'region_launch'
    );
  end if;

  if not exists (select 1 from pg_type where typname = 'event_class_enum') then
    create type event_class_enum as enum (
      'fact',
      'deal',
      'credit',
      'signal',
      'info'
    );
  end if;

  if not exists (select 1 from pg_type where typname = 'source_type_enum') then
    create type source_type_enum as enum (
      'official',
      'pricing',
      'launch',
      'deals',
      'community',
      'social',
      'marketplace'
    );
  end if;
end $$;

create table if not exists event_types (
  id smallserial primary key,
  code event_type_enum not null unique,
  event_class event_class_enum not null,
  description text not null,
  default_base_score integer not null default 0,
  created_at timestamptz not null default now()
);

insert into event_types (code, event_class, description, default_base_score)
values
  ('discount', 'deal', 'Discount or promotional price reduction', 70),
  ('credits', 'credit', 'Bonus credits or usage grants', 80),
  ('price_up', 'fact', 'Observed price increase', 40),
  ('price_down', 'fact', 'Observed price decrease', 65),
  ('new_model', 'signal', 'New model availability or release', 60),
  ('new_plan', 'signal', 'New plan or tier introduced', 55),
  ('free_tier', 'credit', 'Free tier or free usage limit changed', 60),
  ('ltd', 'deal', 'Lifetime deal detected', 85),
  ('launch', 'info', 'New product or major launch', 50),
  ('region_launch', 'info', 'Product launch in a specific region', 45)
on conflict (code) do update set
  event_class = excluded.event_class,
  description = excluded.description,
  default_base_score = excluded.default_base_score;

alter table sources
  alter column source_type type source_type_enum
  using source_type::source_type_enum;

alter table events
  add column if not exists event_class event_class_enum,
  add column if not exists description text,
  add column if not exists old_value numeric(14,2),
  add column if not exists new_value numeric(14,2),
  add column if not exists confidence integer,
  add column if not exists detected_at timestamptz not null default now(),
  add column if not exists source_url text;

alter table events
  alter column event_type type event_type_enum
  using event_type::event_type_enum;

alter table events
  add constraint events_confidence_range_chk
  check (confidence is null or (confidence between 0 and 100));

create index if not exists idx_events_type on events(event_type);
create index if not exists idx_events_detected_at on events(detected_at desc);
create index if not exists idx_events_service on events(service_id);
create index if not exists idx_raw_documents_processed
  on raw_documents((coalesce((raw_payload->>'processed')::boolean, false)));
