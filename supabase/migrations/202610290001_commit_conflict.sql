-- Ordinary optimistic-version conflicts must not use serialization_failure.
-- PostgREST 14 can repeatedly retry a custom 40001 with the same stale version.
-- PT409 returns HTTP 409 once; the caller must reload before deciding to retry.
-- Preserve the signature, ownership, grants and atomic version/data checks.
create or replace function public.tripmate_commit(expected_version bigint,writes jsonb,events jsonb,command_entry jsonb default null) returns bigint language plpgsql security definer set search_path='' as $$
declare current_version bigint; item jsonb;
begin
 select version into current_version from tripmate_private.revision where id for update;
 if current_version<>expected_version then raise exception 'TRIPMATE_CONCURRENT_CHANGE' using errcode='PT409'; end if;
 for item in select value from jsonb_array_elements(writes) loop
  insert into tripmate_private.records values(item->>'kind',item->>'id',item->'payload') on conflict(kind,id) do update set payload=excluded.payload;
 end loop;
 for item in select value from jsonb_array_elements(events) loop
  insert into tripmate_private.traces values(item->>'eventId',item->>'caseId',item);
 end loop;
 if command_entry is not null then
  insert into tripmate_private.commands values(command_entry->>'key',command_entry->>'fingerprint',command_entry->'result');
 end if;
 update tripmate_private.revision set version=version+1 where id;
 return current_version+1;
end; $$;
