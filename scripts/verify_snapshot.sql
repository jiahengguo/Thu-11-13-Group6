-- Read-only compatibility and access regression. Run on the deployed project.
-- Stop on any false result; no business payload is returned.
with actual as materialized (select public.tripmate_snapshot() as body),
expected as materialized (
select jsonb_build_object('version',(select version from tripmate_private.revision where id),
'records',coalesce((select jsonb_agg(jsonb_build_object('kind',kind,'id',id,'payload',payload)) from tripmate_private.records),'[]'::jsonb),
'traces',coalesce((select jsonb_agg(payload order by payload->>'timestamp',event_id) from tripmate_private.traces),'[]'::jsonb),
'commands',coalesce((select jsonb_agg(jsonb_build_object('key',key,'fingerprint',fingerprint,'result',result)) from tripmate_private.commands),'[]'::jsonb)) as body)
select actual.body=expected.body as identical_payload,
actual.body->>'version' as version,
jsonb_array_length(actual.body->'records') as records,
jsonb_array_length(actual.body->'traces') as traces,
jsonb_array_length(actual.body->'commands') as commands
from actual,expected;

select p.proowner::regrole::text as owner,
       l.lanname = 'plpgsql' as uses_scalar_return,
       p.provolatile = 's' as stable_statement_snapshot,
       p.prosecdef as existing_security_definer,
       p.proconfig = array['search_path=""']::text[] as empty_search_path,
       not has_function_privilege('anon',p.oid,'EXECUTE') as anon_blocked,
       not has_function_privilege('authenticated',p.oid,'EXECUTE') as user_blocked,
       has_function_privilege('service_role',p.oid,'EXECUTE') as backend_allowed
from pg_proc p join pg_language l on l.oid=p.prolang
where p.oid='public.tripmate_snapshot()'::regprocedure;

explain (analyze,buffers,timing off,format json)
WITH pgrst_source AS (
  SELECT public.tripmate_snapshot() AS pgrst_scalar
)
SELECT coalesce(json_agg(t.pgrst_scalar)->0,'null') AS body
FROM (SELECT * FROM pgrst_source LIMIT 1 OFFSET 0) t;
