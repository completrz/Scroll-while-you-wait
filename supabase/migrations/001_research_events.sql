-- Future opt-in research store. NOT deployed or connected to the extension.
-- Run only after consent, privacy and ingestion controls have been reviewed.
create table if not exists public.research_events (
  id uuid primary key default gen_random_uuid(),
  participant_id uuid not null,
  session_id uuid not null,
  ai_platform text not null check (length(ai_platform) between 2 and 40),
  video_source text check (video_source in ('instagram','youtube','tiktok')),
  condition text not null check (condition in ('treatment','control','observational')),
  response_duration_ms integer not null check (response_duration_ms between 0 and 3600000),
  playback_duration_ms integer check (playback_duration_ms between 0 and 3600000),
  return_latency_ms integer check (return_latency_ms between 0 and 86400000),
  returned boolean not null,
  recorded_day date not null,
  received_at timestamptz not null default now(),
  constraint return_consistency check (returned = (return_latency_ms is not null))
);
create index if not exists research_events_day on public.research_events(recorded_day);
create index if not exists research_events_participant on public.research_events(participant_id);
alter table public.research_events enable row level security;
-- No client read or write policies: deny all access via normal public/authenticated API.
-- Future server ingestion must validate consent and use dedicated backend auth.
