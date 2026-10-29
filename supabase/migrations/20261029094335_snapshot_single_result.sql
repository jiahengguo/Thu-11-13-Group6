-- Keep the backend-only snapshot contract while avoiding the SQL function's
-- large-result tuplestore spill. No rows, history or revision checks are removed.
create or replace function public.tripmate_snapshot()
returns jsonb
language plpgsql
stable
security definer
set search_path = ''
as $function$
declare
  snapshot jsonb;
begin
  -- All four components share one statement snapshot.
  select jsonb_build_object(
    'version', (select version from tripmate_private.revision where id),
    'records', coalesce((
      select jsonb_agg(jsonb_build_object('kind', kind, 'id', id, 'payload', payload))
      from tripmate_private.records
    ), '[]'::jsonb),
    'traces', coalesce((
      select jsonb_agg(payload order by payload->>'timestamp', event_id)
      from tripmate_private.traces
    ), '[]'::jsonb),
    'commands', coalesce((
      select jsonb_agg(jsonb_build_object('key', key, 'fingerprint', fingerprint, 'result', result))
      from tripmate_private.commands
    ), '[]'::jsonb)
  ) into snapshot;
  return snapshot;
end;
$function$;

-- CREATE OR REPLACE preserves ownership; restate the existing narrow grants.
revoke all on function public.tripmate_snapshot() from public, anon, authenticated;
grant execute on function public.tripmate_snapshot() to service_role;
