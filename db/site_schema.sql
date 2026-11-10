-- Schema for the site chatbot. Safe to run repeatedly with the owner connection.
-- scripts/site_setup.py runs this file, then gives the roles their login passwords.

create extension if not exists vector;
create schema if not exists site;
revoke all on schema site from public;

-- Retrieval passages. No vector index: at a few hundred rows exact search is
-- both faster and exact.
create table if not exists site.chunks (
  id          text primary key,
  doc         text,
  title       text,
  section     text,
  url         text,
  content     text,
  embedding   vector(1024) not null,
  tsv         tsvector generated always as
                (to_tsvector('english', title || ' ' || section || ' ' || content)) stored,
  content_sha text,
  indexed_at  timestamptz default now()
);
create index if not exists chunks_tsv_idx on site.chunks using gin (tsv);

-- Organization context. Readable only through site.lookup_org.
create table if not exists site.org_context (
  org_id       bigserial primary key,
  display_name text not null,
  what_they_do text,
  team_focus   text,
  closest_work text[] not null default '{}',
  updated_at   timestamptz default now()
);

create table if not exists site.org_keys (
  key_hash text primary key,
  org_id   bigint references site.org_context on delete cascade,
  guarded  boolean not null default false
);

-- Privacy screen: salted hashes only.
create table if not exists site.screen_terms (
  hash    text primary key,
  kind    text check (kind in ('name', 'self', 'deflect', 'say')),
  guarded boolean not null default false
);

create table if not exists site.config (
  key   text primary key,
  value text not null
);

create table if not exists site.web_cache (
  key_hash     text primary key,
  display_name text,
  kind         text,
  summary      text,
  sources      jsonb not null default '[]',
  fetched_at   timestamptz default now()
);

create table if not exists site.quota (
  day date,
  key text,
  n   int not null default 0,
  primary key (day, key)
);

create table if not exists site.chat_log (
  id                 bigserial primary key,
  turn_id            uuid unique,
  created_at         timestamptz default now(),
  session_id         text,
  visitor_id         text,
  question           text,
  answer             text,
  passages           jsonb,
  cited              jsonb,
  org_matched        text,
  lookups            jsonb,
  model              text,
  effort             text,
  input_tokens       int,
  output_tokens      int,
  cache_read_tokens  int,
  cache_write_tokens int,
  web_searches       int,
  cost_usd           numeric(10,5),
  ms_first_token     int,
  ms_total           int,
  outcome            text,
  flags              text[],
  ip                 text,
  city               text,
  region             text,
  country            text,
  network            text,
  user_agent         text,
  referrer           text,
  page               text
);

create table if not exists site.events (
  id         bigserial primary key,
  created_at timestamptz default now(),
  kind       text,
  visitor_id text,
  session_id text,
  turn_id    uuid,
  path       text,
  referrer   text,
  data       jsonb,
  ip         text,
  city       text,
  region     text,
  country    text,
  network    text,
  user_agent text,
  device     text
);

-- The only read path to organization context. Unguarded keys sort first so a
-- run of everyday-word hits cannot push a real match past the three-row cap.
create or replace function site.lookup_org(hashes text[])
returns table (
  display_name text,
  what_they_do text,
  team_focus   text,
  closest_work text[],
  key_hash     text,
  guarded      boolean
)
language sql
stable
security definer
set search_path = site, public, pg_temp
as $$
  select c.display_name, c.what_they_do, c.team_focus, c.closest_work, k.key_hash, k.guarded
  from site.org_keys k
  join site.org_context c on c.org_id = k.org_id
  where k.key_hash = any(lookup_org.hashes)
  order by k.guarded, k.key_hash
  limit 3
$$;

-- Counts one request against the per-visitor and global daily limits. The
-- visitor is checked first, so a visitor over their limit never spends the
-- global budget. Callers must treat a database error as a refusal.
create or replace function site.take_quota(visitor text, per_visitor int, global_limit int)
returns boolean
language plpgsql
security definer
set search_path = site, public, pg_temp
as $$
declare
  today     date := (now() at time zone 'utc')::date;
  v_key     text := 'v:' || coalesce(visitor, '');
  visitor_n int;
  global_n  int;
begin
  if per_visitor <= 0 or global_limit <= 0 then
    return false;
  end if;

  insert into site.quota as q (day, key, n)
  values (today, v_key, 1)
  on conflict (day, key) do update set n = q.n + 1
    where q.n < per_visitor
  returning q.n into visitor_n;

  if visitor_n is null then
    return false;
  end if;

  insert into site.quota as q (day, key, n)
  values (today, 'global', 1)
  on conflict (day, key) do update set n = q.n + 1
    where q.n < global_limit
  returning q.n into global_n;

  if global_n is null then
    -- The request is refused, so it should not count against this visitor.
    update site.quota as q set n = q.n - 1
    where q.day = today and q.key = v_key;
    return false;
  end if;

  return true;
end;
$$;

-- Today's recorded model spend, in hundredths of a cent, against a ceiling.
create or replace function site.spend_open(limit_units int)
returns boolean
language sql
stable
security definer
set search_path = site, public, pg_temp
as $$
  select coalesce(
    (select q.n from site.quota q
      where q.day = (now() at time zone 'utc')::date and q.key = 'spend'),
    0
  ) < spend_open.limit_units
$$;

-- The same check across the current calendar month.
create or replace function site.month_spend_open(limit_units int)
returns boolean
language sql
stable
security definer
set search_path = site, public, pg_temp
as $$
  select coalesce(
    (select sum(q.n) from site.quota q
      where q.key = 'spend'
        and q.day >= date_trunc('month', now() at time zone 'utc')::date),
    0
  ) < month_spend_open.limit_units
$$;

create or replace function site.record_spend(units int)
returns void
language sql
security definer
set search_path = site, public, pg_temp
as $$
  insert into site.quota as q (day, key, n)
  values ((now() at time zone 'utc')::date, 'spend', greatest(record_spend.units, 0))
  on conflict (day, key) do update set n = q.n + greatest(record_spend.units, 0)
$$;

-- Holds a turn's worst-case cost before any model call, against both the daily
-- and the monthly ceiling, in hundredths of a cent. Returns the day the hold was
-- counted on, or null when either ceiling would be passed. Callers must treat a
-- database error as a refusal.
create or replace function site.reserve_spend(units int, day_limit int, month_limit int)
returns date
language plpgsql
security definer
set search_path = site, public, pg_temp
as $$
declare
  today   date := (now() at time zone 'utc')::date;
  day_n   int;
  month_n bigint;
begin
  if units <= 0 or day_limit <= 0 or month_limit <= 0 then
    return null;
  end if;

  -- Writing today's row locks it, so holds run one at a time and each one
  -- reads what the one before it added.
  insert into site.quota as q (day, key, n)
  values (today, 'spend', 0)
  on conflict (day, key) do update set n = q.n
  returning q.n into day_n;

  select coalesce(sum(q.n), 0) into month_n
  from site.quota q
  where q.key = 'spend'
    and q.day >= date_trunc('month', today)::date;

  if day_n + units > day_limit or month_n + units > month_limit then
    return null;
  end if;

  update site.quota as q set n = q.n + units
  where q.day = today and q.key = 'spend';

  return today;
end;
$$;

-- Swaps a hold for what the turn really cost, on the day the hold was counted.
-- A turn that spent nothing passes zero and gives the whole hold back. A request
-- ends well inside a minute, so a hold is never older than yesterday's.
create or replace function site.settle_spend(reserved_on date, reserved int, actual int)
returns void
language sql
security definer
set search_path = site, public, pg_temp
as $$
  update site.quota as q
  set n = greatest(q.n + greatest(settle_spend.actual, 0) - greatest(settle_spend.reserved, 0), 0)
  where q.key = 'spend'
    and q.day = settle_spend.reserved_on
    and q.day >= (now() at time zone 'utc')::date - 1
$$;

-- A turn that never reaches the model spends no budget, but its log rows are
-- limited per visitor all the same, on a counter of their own.
create or replace function site.take_log_slot(visitor text, per_visitor int)
returns boolean
language plpgsql
security definer
set search_path = site, public, pg_temp
as $$
declare
  today date := (now() at time zone 'utc')::date;
  taken int;
begin
  if per_visitor <= 0 then
    return false;
  end if;

  insert into site.quota as q (day, key, n)
  values (today, 'l:' || coalesce(visitor, ''), 1)
  on conflict (day, key) do update set n = q.n + 1
    where q.n < per_visitor
  returning q.n into taken;

  return taken is not null;
end;
$$;

-- One visit event against the per-visitor and global daily limits. The logging
-- role can reach the counters only through this function.
create or replace function site.take_event_slot(visitor text, per_visitor int, global_limit int)
returns boolean
language plpgsql
security definer
set search_path = site, public, pg_temp
as $$
declare
  today     date := (now() at time zone 'utc')::date;
  v_key     text := 'e:' || coalesce(visitor, '');
  visitor_n int;
  global_n  int;
begin
  if per_visitor <= 0 or global_limit <= 0 then
    return false;
  end if;

  insert into site.quota as q (day, key, n)
  values (today, v_key, 1)
  on conflict (day, key) do update set n = q.n + 1
    where q.n < per_visitor
  returning q.n into visitor_n;

  if visitor_n is null then
    return false;
  end if;

  insert into site.quota as q (day, key, n)
  values (today, 'events', 1)
  on conflict (day, key) do update set n = q.n + 1
    where q.n < global_limit
  returning q.n into global_n;

  if global_n is null then
    update site.quota as q set n = q.n - 1
    where q.day = today and q.key = v_key;
    return false;
  end if;

  return true;
end;
$$;

-- Entries older than 30 days are treated as missing.
create or replace function site.web_cache_get(key_hash text)
returns table (
  display_name text,
  kind         text,
  summary      text,
  sources      jsonb,
  fetched_at   timestamptz
)
language sql
stable
security definer
set search_path = site, public, pg_temp
as $$
  select c.display_name, c.kind, c.summary, c.sources, c.fetched_at
  from site.web_cache c
  where c.key_hash = web_cache_get.key_hash
    and c.fetched_at > now() - interval '30 days'
$$;

create or replace function site.web_cache_put(
  key_hash     text,
  display_name text,
  kind         text,
  summary      text,
  sources      jsonb
)
returns void
language sql
security definer
set search_path = site, public, pg_temp
as $$
  insert into site.web_cache as c (key_hash, display_name, kind, summary, sources, fetched_at)
  values (
    web_cache_put.key_hash,
    web_cache_put.display_name,
    web_cache_put.kind,
    web_cache_put.summary,
    coalesce(web_cache_put.sources, '[]'::jsonb),
    now()
  )
  on conflict (key_hash) do update set
    display_name = excluded.display_name,
    kind         = excluded.kind,
    summary      = excluded.summary,
    sources      = excluded.sources,
    fetched_at   = excluded.fetched_at
$$;

revoke execute on function site.lookup_org(text[]) from public;
revoke execute on function site.take_quota(text, int, int) from public;
revoke execute on function site.web_cache_get(text) from public;
revoke execute on function site.web_cache_put(text, text, text, text, jsonb) from public;
revoke execute on function site.spend_open(int) from public;
revoke execute on function site.month_spend_open(int) from public;
revoke execute on function site.record_spend(int) from public;
revoke execute on function site.reserve_spend(int, int, int) from public;
revoke execute on function site.settle_spend(date, int, int) from public;
revoke execute on function site.take_log_slot(text, int) from public;
revoke execute on function site.take_event_slot(text, int, int) from public;

-- Created without a login here; site_setup.py sets the login and password.
do $$
declare
  role_name text;
begin
  foreach role_name in array array['site_search', 'site_logger', 'site_reader'] loop
    if not exists (select 1 from pg_roles where rolname = role_name) then
      execute format('create role %I nologin', role_name);
    end if;
  end loop;
end;
$$;

-- Start every run from nothing so a past grant cannot linger.
revoke all on all tables in schema site from site_search, site_logger, site_reader;
revoke all on all sequences in schema site from site_search, site_logger, site_reader;
revoke all on all functions in schema site from site_search, site_logger, site_reader;

grant usage on schema site to site_search, site_logger, site_reader;

grant select on site.chunks, site.screen_terms, site.config to site_search;
grant execute on function site.lookup_org(text[]) to site_search;
grant execute on function site.take_quota(text, int, int) to site_search;
grant execute on function site.web_cache_get(text) to site_search;
grant execute on function site.web_cache_put(text, text, text, text, jsonb) to site_search;
grant execute on function site.spend_open(int) to site_search;
grant execute on function site.month_spend_open(int) to site_search;
grant execute on function site.record_spend(int) to site_search;
grant execute on function site.reserve_spend(int, int, int) to site_search;
grant execute on function site.settle_spend(date, int, int) to site_search;
grant execute on function site.take_log_slot(text, int) to site_search;

grant insert on site.chat_log, site.events to site_logger;
grant usage on sequence site.chat_log_id_seq, site.events_id_seq to site_logger;
grant execute on function site.take_event_slot(text, int, int) to site_logger;

grant select on site.chat_log, site.events to site_reader;
