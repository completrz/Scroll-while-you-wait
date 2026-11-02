-- Consent and administrator authorization. Run only after configuring Supabase.
create table if not exists public.research_consent (
  participant_id uuid primary key references auth.users(id) on delete cascade,
  consented_at timestamptz not null default now(),
  withdrawn_at timestamptz,
  policy_version text not null default 'v1'
);
create table if not exists public.research_admins (
  user_id uuid primary key references auth.users(id) on delete cascade
);
alter table public.research_consent enable row level security;
alter table public.research_admins enable row level security;
create policy "participant can see own consent" on public.research_consent
  for select to authenticated using (participant_id=auth.uid());
create policy "participant can withdraw own consent" on public.research_consent
  for update to authenticated using (participant_id=auth.uid())
  with check (participant_id=auth.uid() and withdrawn_at is not null);
-- Creation is performed by a privileged server action after explicit consent.
-- Admin list cannot be edited by participants.
create policy "admin can see own admin membership" on public.research_admins
  for select to authenticated using (user_id=auth.uid());
create policy "admin reads research rows" on public.research_events
  for select to authenticated using
  (exists (select 1 from public.research_admins a where a.user_id=auth.uid()));
-- Ordinary users have no direct read access to research events.
create index if not exists idx_events_participant on public.research_events(participant_id);
