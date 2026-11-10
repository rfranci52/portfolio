-- Daily limits for the contact form. Safe to run repeatedly with the owner connection.
-- leads_writer can reach the counters only through leads.take_submission_slot.

create table if not exists leads.submission_limits (
  day date,
  key text,
  n   int not null default 0,
  primary key (day, key)
);

revoke all on leads.submission_limits from public, leads_writer, leads_reader;

-- One submission against the per-visitor and global daily limits. allowed says
-- whether to accept it at all, and notify whether it also fits under the separate
-- daily cap on notification emails. The visitor is checked first, so a visitor over
-- their limit never uses the global allowance.
create or replace function leads.take_submission_slot(
  visitor      text,
  per_visitor  int,
  global_limit int,
  email_limit  int
)
returns table (allowed boolean, notify boolean)
language plpgsql
security definer
set search_path = leads, pg_temp
as $$
declare
  today     date := (now() at time zone 'utc')::date;
  v_key     text := 'v:' || coalesce(visitor, '');
  visitor_n int;
  global_n  int;
  email_n   int;
begin
  allowed := false;
  notify := false;

  if per_visitor <= 0 or global_limit <= 0 then
    return next;
    return;
  end if;

  insert into leads.submission_limits as q (day, key, n)
  values (today, v_key, 1)
  on conflict (day, key) do update set n = q.n + 1
    where q.n < per_visitor
  returning q.n into visitor_n;

  if visitor_n is null then
    return next;
    return;
  end if;

  insert into leads.submission_limits as q (day, key, n)
  values (today, 'global', 1)
  on conflict (day, key) do update set n = q.n + 1
    where q.n < global_limit
  returning q.n into global_n;

  if global_n is null then
    -- The submission is refused, so it should not count against this visitor.
    update leads.submission_limits as q set n = q.n - 1
    where q.day = today and q.key = v_key;
    return next;
    return;
  end if;

  allowed := true;

  if email_limit > 0 then
    insert into leads.submission_limits as q (day, key, n)
    values (today, 'email', 1)
    on conflict (day, key) do update set n = q.n + 1
      where q.n < email_limit
    returning q.n into email_n;
    notify := email_n is not null;
  end if;

  return next;
end;
$$;

revoke execute on function leads.take_submission_slot(text, int, int, int) from public;
grant execute on function leads.take_submission_slot(text, int, int, int) to leads_writer;
