begin;
-- Trusted setup only; never grants a browser the ability to select its own role.
create function public.tripmate_prepare_demo_profile(actor uuid, demo_namespace text, member_kind text default null)
returns jsonb language plpgsql security definer set search_path='' as $$
declare u auth.users; wanted_role text; wanted_tier text;
begin
 if demo_namespace is null or demo_namespace !~ '^[a-z][a-z0-9-]{2,39}$' then raise exception 'INVALID_DEMO_NAMESPACE'; end if;
 if actor is null then return jsonb_build_object('demoProvisioning',1); end if;
 if member_kind is null or member_kind not in ('free','paid','supplier','operator') then raise exception 'INVALID_DEMO_KIND'; end if;
 select * into u from auth.users where id=actor;
 if not found or u.email<>(demo_namespace||'.'||member_kind||'@example.invalid')
    or coalesce(u.raw_app_meta_data->>'tripmate_demo','')<>demo_namespace or u.email_confirmed_at is null
 then raise exception 'DEMO_IDENTITY_MISMATCH'; end if;
 wanted_role=case member_kind when 'supplier' then 'SUPPLIER' when 'operator' then 'OPERATOR' else 'TRAVELLER' end;
 wanted_tier=case member_kind when 'paid' then 'PAID' else 'FREE' end;
 update public.tripmate_accounts set role=wanted_role, membership=wanted_tier, active=true,
 paid_until=case when wanted_tier='PAID' then now()+interval '30 days' else null end where user_id=actor;
 if not found then raise exception 'DEMO_PROFILE_MISSING'; end if;
 insert into tripmate_private.audit(actor,action,subject)
 values(actor,'DEMO_PROFILE_PREPARED',demo_namespace||':'||member_kind);
 return jsonb_build_object('demoProvisioning',1,'role',wanted_role,'membership',wanted_tier);
end; $$;
revoke all on function public.tripmate_prepare_demo_profile(uuid,text,text) from public,anon,authenticated;
grant execute on function public.tripmate_prepare_demo_profile(uuid,text,text) to service_role;
commit;
