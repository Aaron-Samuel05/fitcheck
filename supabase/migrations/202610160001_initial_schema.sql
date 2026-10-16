-- FitCheck Supabase schema migration
-- Apply in Supabase SQL Editor after creating a project.
-- Auth identity is Supabase auth.users; all user-owned rows are scoped by auth.uid().
-- Stripe webhooks run server-side with the service role and must never expose that key.

create extension if not exists pgcrypto;

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null,
  name text not null default '',
  age integer check (age is null or age between 13 and 100),
  height_cm numeric check (height_cm is null or height_cm between 100 and 250),
  weight_kg numeric check (weight_kg is null or weight_kg between 25 and 300),
  goal text not null default '',
  plan text not null default 'free' check (plan in ('free', 'buddy_pro')),
  subscription_status text,
  current_period_end timestamptz,
  stripe_customer_id text unique,
  stripe_subscription_id text unique,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.workouts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  name text not null check (char_length(name) between 1 and 120),
  exercises jsonb not null default '[]'::jsonb,
  volume numeric not null default 0 check (volume >= 0),
  total_sets integer not null default 0 check (total_sets >= 0),
  workout_date date not null default current_date,
  notes text not null default '',
  created_at timestamptz not null default now()
);
create index if not exists workouts_user_date_idx on public.workouts(user_id, workout_date desc, created_at desc);

create table if not exists public.training_plans (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  name text not null check (char_length(name) between 1 and 120),
  goal text not null default '',
  days jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists training_plans_user_created_idx on public.training_plans(user_id, created_at desc);

create table if not exists public.chat_messages (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  session_id uuid not null,
  role text not null check (role in ('user', 'assistant')),
  message text not null check (char_length(message) between 1 and 12000),
  created_at timestamptz not null default now()
);
create index if not exists chat_messages_user_session_created_idx on public.chat_messages(user_id, session_id, created_at);
create index if not exists chat_messages_user_created_idx on public.chat_messages(user_id, created_at desc);

-- Stripe event IDs make webhook processing idempotent.
create table if not exists public.stripe_events (
  id text primary key,
  event_type text not null,
  processed_at timestamptz not null default now()
);

alter table public.profiles enable row level security;
alter table public.workouts enable row level security;
alter table public.training_plans enable row level security;
alter table public.chat_messages enable row level security;
alter table public.stripe_events enable row level security;

drop policy if exists "Users can read own profile" on public.profiles;
create policy "Users can read own profile" on public.profiles for select to authenticated using (id = auth.uid());
drop policy if exists "Users can update own profile" on public.profiles;
create policy "Users can update own profile" on public.profiles for update to authenticated using (id = auth.uid()) with check (id = auth.uid());

drop policy if exists "Users can manage own workouts" on public.workouts;
create policy "Users can manage own workouts" on public.workouts for all to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());
drop policy if exists "Users can manage own training plans" on public.training_plans;
create policy "Users can manage own training plans" on public.training_plans for all to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());
drop policy if exists "Users can read own chat messages" on public.chat_messages;
create policy "Users can read own chat messages" on public.chat_messages for select to authenticated using (user_id = auth.uid());
drop policy if exists "Users can insert own chat messages" on public.chat_messages;
create policy "Users can insert own chat messages" on public.chat_messages for insert to authenticated with check (user_id = auth.uid());
drop policy if exists "Users can delete own chat messages" on public.chat_messages;
create policy "Users can delete own chat messages" on public.chat_messages for delete to authenticated using (user_id = auth.uid());

-- No client-facing policy is intentionally created for Stripe events.

-- Create a profile automatically for each Supabase Auth identity.
create or replace function public.handle_new_auth_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.profiles (id, email, name)
  values (
    new.id,
    coalesce(new.email, ''),
    coalesce(new.raw_user_meta_data ->> 'full_name', new.raw_user_meta_data ->> 'name', '')
  )
  on conflict (id) do update set email = excluded.email;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created_fitcheck on auth.users;
create trigger on_auth_user_created_fitcheck
after insert on auth.users
for each row execute procedure public.handle_new_auth_user();

create or replace function public.handle_auth_user_email_update()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if new.email is distinct from old.email then
    update public.profiles set email = coalesce(new.email, ''), updated_at = now() where id = new.id;
  end if;
  return new;
end;
$$;

drop trigger if exists on_auth_user_email_updated_fitcheck on auth.users;
create trigger on_auth_user_email_updated_fitcheck
after update of email on auth.users
for each row execute procedure public.handle_auth_user_email_update();
