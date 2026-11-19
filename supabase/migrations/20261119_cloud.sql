-- Private per-user storage and atomic shared quotas. Apply to a dedicated project.
create table if not exists public.web_dictionaries (
  user_id uuid not null references auth.users(id) on delete cascade,
  dialect text not null check (dialect ~ '^[a-z][a-z0-9_-]{0,39}$'),
  version bigint not null default 1,
  payload jsonb not null,
  updated_at timestamptz not null default now(),
  primary key (user_id, dialect)
);
create table if not exists public.web_runs (
  user_id uuid not null references auth.users(id) on delete cascade,
  id text not null check (id ~ '^[a-f0-9]{32}$'),
  payload jsonb not null,
  created_at timestamptz not null default now(),
  primary key (user_id, id)
);
create table if not exists public.web_quota (
  bucket text not null,
  window_start bigint not null,
  seconds integer not null,
  attempts integer not null,
  primary key (bucket, window_start, seconds)
);
create table if not exists public.web_leases (
  id uuid primary key default gen_random_uuid(),
  subject text not null,
  expires_at timestamptz not null
);
alter table public.web_dictionaries enable row level security;
alter table public.web_runs enable row level security;
alter table public.web_quota enable row level security;
alter table public.web_leases enable row level security;
drop policy if exists dictionary_owner on public.web_dictionaries;
drop policy if exists run_owner on public.web_runs;
create policy dictionary_owner on public.web_dictionaries for select to authenticated using (user_id = (select auth.uid()));
create policy run_owner on public.web_runs for select to authenticated using (user_id = (select auth.uid()));
revoke all on public.web_dictionaries, public.web_runs, public.web_quota, public.web_leases from anon, authenticated;
grant select on public.web_dictionaries, public.web_runs to authenticated;
grant all on public.web_dictionaries, public.web_runs, public.web_quota, public.web_leases to service_role;

-- Limits are supplied only by the server using a service-role credential.
-- One short transaction covers all windows and both concurrency checks.
create or replace function public.web_reserve(p_buckets jsonb, p_subject text, p_inference boolean default false)
returns jsonb language plpgsql security definer set search_path = public, pg_temp as $$
declare b jsonb; n integer; epoch bigint := floor(extract(epoch from clock_timestamp()));
  quota_window bigint; retry integer := 0; lease uuid;
begin
  perform pg_advisory_xact_lock(71919001);
  delete from web_quota where window_start + seconds < epoch - 86400;
  delete from web_leases where expires_at < now();
  for b in select value from jsonb_array_elements(p_buckets) loop
    if (b->>'seconds')::integer not in (60, 86400) or (b->>'limit')::integer < 1 then
      raise exception 'Invalid quota configuration';
    end if;
    quota_window := (epoch / (b->>'seconds')::integer) * (b->>'seconds')::integer;
    insert into web_quota(bucket, window_start, seconds, attempts)
      values (b->>'key', quota_window, (b->>'seconds')::integer, 1)
      on conflict (bucket, window_start, seconds) do update set attempts = web_quota.attempts + 1
      returning attempts into n;
    if n > (b->>'limit')::integer then
      retry := greatest(retry, (quota_window + (b->>'seconds')::integer - epoch)::integer);
    end if;
  end loop;
  if retry > 0 then return jsonb_build_object('allowed', false, 'retry_after', retry); end if;
  if p_inference then
    if (select count(*) from web_leases) >= 4 or exists(select 1 from web_leases where subject = p_subject) then
      return jsonb_build_object('allowed', false, 'retry_after', 5);
    end if;
    insert into web_leases(subject, expires_at) values (p_subject, now() + interval '90 seconds') returning id into lease;
  end if;
  return jsonb_build_object('allowed', true, 'lease', lease);
end $$;
revoke all on function public.web_reserve(jsonb, text, boolean) from public, anon, authenticated;
grant execute on function public.web_reserve(jsonb, text, boolean) to service_role;
create or replace function public.web_release(p_id uuid)
returns void language sql security definer set search_path = public, pg_temp as $$ delete from web_leases where id = p_id; $$;
revoke all on function public.web_release(uuid) from public, anon, authenticated;
grant execute on function public.web_release(uuid) to service_role;

-- Owner comes from the validated Supabase session, never from request JSON.
-- Version comparison prevents losing corrections when two tabs write at once.
create or replace function public.web_commit_dictionary(p_dialect text, p_version bigint, p_payload jsonb, p_run jsonb default null)
returns jsonb language plpgsql security definer set search_path = public, pg_temp as $$
declare owner uuid := auth.uid(); current_version bigint; old_size bigint := 0; total_size bigint;
begin
  if owner is null then raise exception 'Authentication required'; end if;
  if p_dialect !~ '^[a-z][a-z0-9_-]{0,39}$' or coalesce(jsonb_typeof(p_payload->'corrections'), '') <> 'array'
    or coalesce(jsonb_typeof(p_payload->'links'), '') <> 'array' or jsonb_array_length(p_payload->'corrections') > 1000
    or jsonb_array_length(p_payload->'links') > 10000 or octet_length(p_payload::text) > 1048576 then
    raise exception 'Dictionary exceeds limits';
  end if;
  perform pg_advisory_xact_lock(71919002);
  select version, octet_length(payload::text) into current_version, old_size from web_dictionaries
    where user_id = owner and dialect = p_dialect for update;
  if coalesce(current_version, 0) <> p_version then return jsonb_build_object('conflict', true); end if;
  if current_version is null and (select count(*) from web_dictionaries where user_id = owner) >= 10 then
    raise exception 'Dictionary count limit reached';
  end if;
  select coalesce(sum(octet_length(payload::text)), 0) into total_size from web_dictionaries;
  if total_size - coalesce(old_size, 0) + octet_length(p_payload::text) > 134217728 then
    raise exception 'Storage budget exhausted';
  end if;
  if p_run is not null and not exists(select 1 from web_runs where user_id = owner and id = p_run->>'id') then
    raise exception 'Result not found';
  end if;
  insert into web_dictionaries(user_id, dialect, version, payload) values (owner, p_dialect, p_version + 1, p_payload)
    on conflict (user_id, dialect) do update set payload = excluded.payload, version = excluded.version, updated_at = now();
  if p_run is not null then
    update web_runs set payload = p_run where user_id = owner and id = p_run->>'id';
  end if;
  return jsonb_build_object('conflict', false, 'version', p_version + 1);
end $$;
revoke all on function public.web_commit_dictionary(text, bigint, jsonb, jsonb) from public, anon;
grant execute on function public.web_commit_dictionary(text, bigint, jsonb, jsonb) to authenticated;

create or replace function public.web_put_run(p_payload jsonb)
returns void language plpgsql security definer set search_path = public, pg_temp as $$
declare owner uuid := auth.uid(); total_size bigint;
begin
  if owner is null or p_payload->>'id' !~ '^[a-f0-9]{32}$' or octet_length(p_payload::text) > 20000 then
    raise exception 'Invalid translation result';
  end if;
  perform pg_advisory_xact_lock(71919003);
  delete from web_runs where created_at < now() - interval '7 days';
  delete from web_runs where user_id = owner and id in
    (select id from web_runs where user_id = owner order by created_at desc offset 99);
  select coalesce(sum(octet_length(payload::text)), 0) into total_size from web_runs;
  if total_size + octet_length(p_payload::text) > 67108864 then raise exception 'History budget exhausted'; end if;
  insert into web_runs(user_id, id, payload) values (owner, p_payload->>'id', p_payload)
    on conflict (user_id, id) do update set payload = excluded.payload;
end $$;
revoke all on function public.web_put_run(jsonb) from public, anon;
grant execute on function public.web_put_run(jsonb) to authenticated;
