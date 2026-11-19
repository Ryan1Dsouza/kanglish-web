-- Versions remain distinct when a deleted dictionary name is recreated.
create sequence if not exists public.web_dictionary_versions start with 1000000000000;
revoke all on sequence public.web_dictionary_versions from public, anon, authenticated;

create or replace function public.web_commit_dictionary(p_dialect text, p_version bigint, p_payload jsonb, p_run jsonb default null)
returns jsonb language plpgsql security definer set search_path = public, pg_temp as $$
declare owner uuid := auth.uid(); current_version bigint; new_version bigint; old_size bigint := 0; total_size bigint;
begin
  if owner is null then raise exception 'Authentication required'; end if;
  if p_dialect is null or p_dialect !~ '^[a-z][a-z0-9_-]{0,39}$' or p_version is null or p_version < 0
    or coalesce(jsonb_typeof(p_payload->'corrections'), '') <> 'array'
    or coalesce(jsonb_typeof(p_payload->'links'), '') <> 'array' or jsonb_array_length(p_payload->'corrections') > 5000
    or jsonb_array_length(p_payload->'links') > 10000 or octet_length(p_payload::text) > 2097152 then
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
  new_version := nextval('public.web_dictionary_versions');
  insert into web_dictionaries(user_id, dialect, version, payload) values (owner, p_dialect, new_version, p_payload)
    on conflict (user_id, dialect) do update set payload = excluded.payload, version = excluded.version, updated_at = now();
  if p_run is not null then
    update web_runs set payload = p_run where user_id = owner and id = p_run->>'id';
  end if;
  return jsonb_build_object('conflict', false, 'version', new_version);
end $$;
revoke all on function public.web_commit_dictionary(text, bigint, jsonb, jsonb) from public, anon;
grant execute on function public.web_commit_dictionary(text, bigint, jsonb, jsonb) to authenticated;

create or replace function public.web_delete_dictionary(p_dialect text, p_version bigint)
returns jsonb language plpgsql security definer set search_path = public, pg_temp as $$
declare owner uuid := auth.uid(); current_version bigint;
begin
  if owner is null then raise exception 'Authentication required'; end if;
  if p_dialect is null or p_dialect !~ '^[a-z][a-z0-9_-]{0,39}$' or p_version is null or p_version < 0 then
    raise exception 'Invalid dictionary confirmation';
  end if;
  perform pg_advisory_xact_lock(71919002);
  select version into current_version from web_dictionaries where user_id = owner and dialect = p_dialect for update;
  if coalesce(current_version, 0) <> p_version then return jsonb_build_object('conflict', true); end if;
  delete from web_dictionaries where user_id = owner and dialect = p_dialect;
  return jsonb_build_object('conflict', false);
end $$;
revoke all on function public.web_delete_dictionary(text, bigint) from public, anon;
grant execute on function public.web_delete_dictionary(text, bigint) to authenticated;

-- The switcher needs counts, not every user's entire dictionary payload.
create or replace function public.web_dictionary_counts()
returns jsonb language plpgsql security definer set search_path = public, pg_temp as $$
declare owner uuid := auth.uid(); result jsonb;
begin
  if owner is null then raise exception 'Authentication required'; end if;
  select coalesce(jsonb_object_agg(dialect, jsonb_array_length(payload->'corrections')), '{}'::jsonb)
    into result from web_dictionaries where user_id = owner;
  return result;
end $$;
revoke all on function public.web_dictionary_counts() from public, anon;
grant execute on function public.web_dictionary_counts() to authenticated;
