-- Upgrade conversations to support agent workflow state + owner summaries.

alter table public.conversations
  add column if not exists summary_for_owner text,
  add column if not exists recommended_next_step text,
  add column if not exists last_agent_decision text,
  add column if not exists updated_at timestamptz not null default now();

-- Broaden allowed states if the original table was created with a narrower check.
alter table public.conversations drop constraint if exists conversations_status_check;
alter table public.conversations
  add constraint conversations_status_check
  check (status in ('active', 'paused', 'closed', 'needs_human', 'mutual', 'conversation_started', 'handoff_ready', 'closed_not_fit'));

create index if not exists conversations_status_updated_idx
on public.conversations (status, updated_at desc);
