begin;
-- Trusted deployment command only; never expose this RPC to a browser/session JWT.
create function public.tripmate_assign_operator(approved_email text) returns boolean language plpgsql security definer set search_path='' as $$
declare target uuid;
begin
 select id into target from auth.users where lower(email)=lower(approved_email) and email_confirmed_at is not null;
 if target is null then raise exception 'VERIFIED_ACCOUNT_REQUIRED'; end if;
 update public.tripmate_accounts set role='OPERATOR' where user_id=target and active;
 if not found then raise exception 'ACTIVE_ACCOUNT_REQUIRED'; end if;
 insert into tripmate_private.audit(actor,action,subject) values(target,'TRUSTED_OPERATOR_ASSIGNMENT',target::text);
 return true;
end; $$;
revoke all on function public.tripmate_assign_operator(text) from public,anon,authenticated;
grant execute on function public.tripmate_assign_operator(text) to service_role;
notify pgrst,'reload schema';
commit;
