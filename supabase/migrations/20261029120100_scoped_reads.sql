-- Backend-only point/kind reads avoid constructing unrelated history and runs.
create or replace function public.tripmate_read_records(record_kind text, record_id text default null)
returns jsonb language sql stable security definer set search_path='' as $$
 select coalesce(jsonb_agg(payload),'[]'::jsonb)
 from tripmate_private.records
 where kind=record_kind and (record_id is null or id=record_id);
$$;
create or replace function public.tripmate_read_traces(requested_case text)
returns jsonb language sql stable security definer set search_path='' as $$
 select coalesce(jsonb_agg(payload order by payload->>'timestamp',event_id),'[]'::jsonb)
 from tripmate_private.traces where case_id=requested_case;
$$;
create index if not exists tripmate_traces_case_id_idx on tripmate_private.traces(case_id);
revoke all on function public.tripmate_read_records(text,text) from public,anon,authenticated;
revoke all on function public.tripmate_read_traces(text) from public,anon,authenticated;
grant execute on function public.tripmate_read_records(text,text) to service_role;
grant execute on function public.tripmate_read_traces(text) to service_role;
-- Writes need a consistent version, business records and deduplication results,
-- but do not consume the trace archive or append-only case-history snapshots.
-- Both remain available through the scoped readers above; nothing is deleted.
create or replace function public.tripmate_state()
returns jsonb language plpgsql stable security definer set search_path='' as $$
declare state_body jsonb;
begin
 select jsonb_build_object(
 'version',(select version from tripmate_private.revision where id),
 'records',coalesce((select jsonb_agg(jsonb_build_object('kind',kind,'id',id,'payload',payload)) from tripmate_private.records where kind<>'history'),'[]'::jsonb),
 'commands',coalesce((select jsonb_agg(jsonb_build_object('key',key,'fingerprint',fingerprint,'result',result)) from tripmate_private.commands),'[]'::jsonb)) into state_body;
 return state_body;
end;
$$;
revoke all on function public.tripmate_state() from public,anon,authenticated;
grant execute on function public.tripmate_state() to service_role;
