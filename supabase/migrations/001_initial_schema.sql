-- TripPilot AI - 001_initial_schema.sql
-- Run in Supabase Dashboard > SQL Editor. Safe to read top-to-bottom.

create extension if not exists pgcrypto;

-- ============ helper: updated_at ============
create or replace function public.set_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- ============ TABLES ============
create table public.profiles (
  id          uuid primary key references auth.users(id) on delete cascade,
  full_name   text,
  avatar_url  text,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

create table public.trips (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references public.profiles(id) on delete cascade,
  title        text not null check (char_length(title) between 1 and 200),
  origin       text not null check (char_length(origin) between 1 and 200),
  destination  text not null check (char_length(destination) between 1 and 200),
  start_date   date not null,
  end_date     date not null,
  budget       numeric(12,2) not null check (budget > 0),
  currency     char(3) not null default 'INR',
  travelers    integer not null default 1 check (travelers between 1 and 50),
  travel_style text not null default 'balanced'
               check (travel_style in ('relaxed','balanced','packed')),
  preferences  jsonb not null default '{}'::jsonb,
  status       text not null default 'draft'
               check (status in ('draft','planned','completed','archived')),
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  constraint trips_dates_valid check (end_date >= start_date)
);

create table public.itinerary_days (
  id          uuid primary key default gen_random_uuid(),
  trip_id     uuid not null references public.trips(id) on delete cascade,
  day_number  integer not null check (day_number >= 1),
  trip_date   date,
  summary     text,
  created_at  timestamptz not null default now(),
  unique (trip_id, day_number)
);

create table public.itinerary_items (
  id               uuid primary key default gen_random_uuid(),
  day_id           uuid not null references public.itinerary_days(id) on delete cascade,
  name             text not null check (char_length(name) between 1 and 200),
  category         text,
  description      text,
  address          text,
  latitude         double precision check (latitude  between -90  and 90),
  longitude        double precision check (longitude between -180 and 180),
  start_time       time,
  duration_minutes integer check (duration_minutes is null or duration_minutes >= 0),
  estimated_cost   numeric(12,2) check (estimated_cost is null or estimated_cost >= 0),
  currency         char(3) not null default 'INR',
  source_url       text,
  sort_order       integer not null default 0,
  created_at       timestamptz not null default now()
);

create table public.expenses (
  id                uuid primary key default gen_random_uuid(),
  trip_id           uuid not null references public.trips(id) on delete cascade,
  itinerary_item_id uuid references public.itinerary_items(id) on delete set null,
  category          text not null
                    check (category in ('transport','accommodation','food','tickets','local_travel','misc')),
  description       text,
  amount            numeric(12,2) not null check (amount >= 0),
  currency          char(3) not null default 'INR',
  expense_date      date,
  is_actual         boolean not null default false,
  created_at        timestamptz not null default now()
);

create table public.agent_runs (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references public.profiles(id) on delete cascade,
  trip_id       uuid references public.trips(id) on delete set null,
  input_data    jsonb not null default '{}'::jsonb,
  output_data   jsonb,
  status        text not null default 'pending'
                check (status in ('pending','success','error')),
  error_message text,
  created_at    timestamptz not null default now()
);

-- ============ INDEXES ============
create index trips_user_created_idx   on public.trips (user_id, created_at desc);
create index days_trip_idx            on public.itinerary_days (trip_id);
create index items_day_sort_idx       on public.itinerary_items (day_id, sort_order);
create index expenses_trip_idx        on public.expenses (trip_id);
create index expenses_item_idx        on public.expenses (itinerary_item_id);
create index agent_runs_user_idx      on public.agent_runs (user_id, created_at desc);
create index agent_runs_trip_idx      on public.agent_runs (trip_id);

-- ============ updated_at TRIGGERS ============
create trigger profiles_set_updated_at before update on public.profiles
  for each row execute function public.set_updated_at();
create trigger trips_set_updated_at before update on public.trips
  for each row execute function public.set_updated_at();

-- ============ PROFILE ON SIGNUP ============
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.profiles (id, full_name, avatar_url)
  values (
    new.id,
    new.raw_user_meta_data ->> 'full_name',
    new.raw_user_meta_data ->> 'avatar_url'
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ============ ROW LEVEL SECURITY ============
alter table public.profiles        enable row level security;
alter table public.trips           enable row level security;
alter table public.itinerary_days  enable row level security;
alter table public.itinerary_items enable row level security;
alter table public.expenses        enable row level security;
alter table public.agent_runs      enable row level security;

-- profiles: read/update own row (insert happens via trigger only)
create policy "profiles_select_own" on public.profiles
  for select to authenticated using (id = (select auth.uid()));
create policy "profiles_update_own" on public.profiles
  for update to authenticated
  using (id = (select auth.uid())) with check (id = (select auth.uid()));

-- trips: full CRUD on own trips
create policy "trips_all_own" on public.trips
  for all to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));

-- itinerary_days: via trip ownership
create policy "days_all_own" on public.itinerary_days
  for all to authenticated
  using (exists (select 1 from public.trips t
                 where t.id = itinerary_days.trip_id and t.user_id = (select auth.uid())))
  with check (exists (select 1 from public.trips t
                 where t.id = itinerary_days.trip_id and t.user_id = (select auth.uid())));

-- itinerary_items: via day -> trip ownership
create policy "items_all_own" on public.itinerary_items
  for all to authenticated
  using (exists (select 1 from public.itinerary_days d
                 join public.trips t on t.id = d.trip_id
                 where d.id = itinerary_items.day_id and t.user_id = (select auth.uid())))
  with check (exists (select 1 from public.itinerary_days d
                 join public.trips t on t.id = d.trip_id
                 where d.id = itinerary_items.day_id and t.user_id = (select auth.uid())));

-- expenses: own trip, and any linked item must belong to the SAME trip
create policy "expenses_all_own" on public.expenses
  for all to authenticated
  using (exists (select 1 from public.trips t
                 where t.id = expenses.trip_id and t.user_id = (select auth.uid())))
  with check (
    exists (select 1 from public.trips t
            where t.id = expenses.trip_id and t.user_id = (select auth.uid()))
    and (
      expenses.itinerary_item_id is null
      or exists (select 1 from public.itinerary_items i
                 join public.itinerary_days d on d.id = i.day_id
                 where i.id = expenses.itinerary_item_id and d.trip_id = expenses.trip_id)
    )
  );

-- agent_runs: read own; insert own, and trip_id (if given) must be own trip
create policy "agent_runs_select_own" on public.agent_runs
  for select to authenticated using (user_id = (select auth.uid()));
create policy "agent_runs_insert_own" on public.agent_runs
  for insert to authenticated
  with check (
    user_id = (select auth.uid())
    and (
      trip_id is null
      or exists (select 1 from public.trips t
                 where t.id = agent_runs.trip_id and t.user_id = (select auth.uid()))
    )
  );
create policy "agent_runs_update_own" on public.agent_runs
  for update to authenticated
  using (user_id = (select auth.uid()))
  with check (
    user_id = (select auth.uid())
    and (
      trip_id is null
      or exists (select 1 from public.trips t
                 where t.id = agent_runs.trip_id and t.user_id = (select auth.uid()))
    )
  );
