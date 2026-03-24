-- Per-project agent policy for Clawborate agent-first patrol behavior.

create table if not exists public.agent_policies (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  owner_user_id uuid not null,

  market_patrol_interval text not null default '30m' check (
    market_patrol_interval in ('10m', '30m', '1h', 'manual')
  ),
  message_patrol_interval text not null default '10m' check (
    message_patrol_interval in ('5m', '10m', '30m', 'manual')
  ),
  interest_behavior text not null default 'notify_then_send' check (
    interest_behavior in ('notify_then_send', 'direct_send')
  ),
  reply_behavior text not null default 'notify_then_send' check (
    reply_behavior in ('notify_then_send', 'direct_send')
  ),
  extra_requirements text not null default '',
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint agent_policies_one_per_project unique (project_id)
);

alter table public.agent_policies enable row level security;

drop policy if exists "owners can view own agent policies" on public.agent_policies;
create policy "owners can view own agent policies"
on public.agent_policies
for select
using (auth.uid() = owner_user_id);

drop policy if exists "owners can insert own agent policies" on public.agent_policies;
create policy "owners can insert own agent policies"
on public.agent_policies
for insert
with check (auth.uid() = owner_user_id);

drop policy if exists "owners can update own agent policies" on public.agent_policies;
create policy "owners can update own agent policies"
on public.agent_policies
for update
using (auth.uid() = owner_user_id)
with check (auth.uid() = owner_user_id);

create index if not exists agent_policies_owner_idx
on public.agent_policies (owner_user_id, updated_at desc);
