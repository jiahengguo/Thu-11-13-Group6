begin;
-- Business storage is private. Public account rows expose only the signed-in account.
create schema if not exists tripmate_private;
revoke all on schema tripmate_private from public, anon, authenticated;
create table public.tripmate_accounts (
  user_id uuid primary key references auth.users(id) on delete cascade,
  role text not null default 'TRAVELLER' check(role in ('TRAVELLER','SUPPLIER','OPERATOR')),
  active boolean not null default true,
  membership text not null default 'FREE' check(membership in ('FREE','PAID')),
  paid_until timestamptz,
  created_at timestamptz not null default now()
);
alter table public.tripmate_accounts enable row level security;
revoke all on public.tripmate_accounts from anon, authenticated;
grant select on public.tripmate_accounts to authenticated;
create policy read_own_account on public.tripmate_accounts for select to authenticated using(user_id=auth.uid());
create function tripmate_private.new_account() returns trigger language plpgsql security definer set search_path='' as $$
begin
 insert into public.tripmate_accounts(user_id) values(new.id);
 return new;
end; $$;
create trigger tripmate_new_account after insert on auth.users for each row execute function tripmate_private.new_account();
insert into public.tripmate_accounts(user_id) select id from auth.users on conflict do nothing;
create table tripmate_private.records(kind text not null,id text not null,payload jsonb not null,primary key(kind,id));
create table tripmate_private.traces(event_id text primary key,case_id text,payload jsonb not null);
create table tripmate_private.commands(key text primary key,fingerprint text not null,result jsonb not null);
create table tripmate_private.revision(id boolean primary key default true check(id),version bigint not null default 0);
insert into tripmate_private.revision values(true,0);
create table tripmate_private.audit(id bigint generated always as identity primary key,actor uuid references auth.users(id),action text not null,subject text,created_at timestamptz not null default now());
create table tripmate_private.partner_applications(user_id uuid primary key references auth.users(id) on delete cascade,company text not null,description text not null,status text not null default 'PENDING' check(status in ('PENDING','APPROVED','REJECTED')),reason text,reviewed_by uuid,created_at timestamptz not null default now());
alter table tripmate_private.records enable row level security;
alter table tripmate_private.traces enable row level security;
alter table tripmate_private.commands enable row level security;
alter table tripmate_private.revision enable row level security;
alter table tripmate_private.audit enable row level security;
alter table tripmate_private.partner_applications enable row level security;
-- All RPCs below are backend-only. No browser JWT can fetch raw draft/approval records.
create function public.tripmate_snapshot() returns jsonb language sql security definer set search_path='' as $$
 select jsonb_build_object('version',(select version from tripmate_private.revision where id),
 'records',coalesce((select jsonb_agg(jsonb_build_object('kind',kind,'id',id,'payload',payload)) from tripmate_private.records),'[]'::jsonb),
 'traces',coalesce((select jsonb_agg(payload order by payload->>'timestamp',event_id) from tripmate_private.traces),'[]'::jsonb),
 'commands',coalesce((select jsonb_agg(jsonb_build_object('key',key,'fingerprint',fingerprint,'result',result)) from tripmate_private.commands),'[]'::jsonb));
$$;
create function public.tripmate_commit(expected_version bigint,writes jsonb,events jsonb,command_entry jsonb default null) returns bigint language plpgsql security definer set search_path='' as $$
declare current_version bigint; item jsonb;
begin
 select version into current_version from tripmate_private.revision where id for update;
 if current_version<>expected_version then raise exception 'TRIPMATE_CONCURRENT_CHANGE' using errcode='40001'; end if;
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
create function public.tripmate_partner_apply(actor uuid,company_name text,description_text text) returns jsonb language plpgsql security definer set search_path='' as $$
declare result jsonb;
begin
 if not exists(select 1 from public.tripmate_accounts where user_id=actor and active and role='TRAVELLER') then raise exception 'ACCESS_DENIED'; end if;
 if length(trim(company_name)) not between 1 and 160 or length(trim(description_text)) not between 1 and 2000 then raise exception 'INVALID_INPUT'; end if;
 insert into tripmate_private.partner_applications(user_id,company,description) values(actor,company_name,description_text)
 on conflict(user_id) do update set company=excluded.company,description=excluded.description,status='PENDING',reason=null,reviewed_by=null where tripmate_private.partner_applications.status<>'APPROVED';
 insert into tripmate_private.audit(actor,action,subject) values(actor,'PARTNER_APPLICATION',actor::text);
 select to_jsonb(a) into result from tripmate_private.partner_applications a where user_id=actor;
 return result;
end; $$;
create function public.tripmate_partner_list(actor uuid) returns jsonb language sql security definer set search_path='' as $$
 select coalesce(jsonb_agg(to_jsonb(a) order by created_at),'[]'::jsonb) from tripmate_private.partner_applications a
 where a.user_id=actor or exists(select 1 from public.tripmate_accounts where user_id=actor and active and role='OPERATOR');
$$;
create function public.tripmate_partner_review(actor uuid,applicant uuid,decision text,review_reason text) returns jsonb language plpgsql security definer set search_path='' as $$
declare result jsonb;
begin
 if not exists(select 1 from public.tripmate_accounts where user_id=actor and active and role='OPERATOR') then raise exception 'ACCESS_DENIED'; end if;
 if decision not in ('APPROVED','REJECTED') or length(trim(review_reason)) not between 1 and 1000 then raise exception 'INVALID_INPUT'; end if;
 perform 1 from public.tripmate_accounts where user_id=applicant and active and role='TRAVELLER' for update;
 if not found then raise exception 'INVALID_APPLICANT'; end if;
 update tripmate_private.partner_applications set status=decision,reason=review_reason,reviewed_by=actor where user_id=applicant and status='PENDING';
 if not found then raise exception 'APPLICATION_CHANGED'; end if;
 if decision='APPROVED' then update public.tripmate_accounts set role='SUPPLIER' where user_id=applicant; end if;
 insert into tripmate_private.audit(actor,action,subject) values(actor,'PARTNER_'||decision,applicant::text);
 select to_jsonb(a) into result from tripmate_private.partner_applications a where user_id=applicant;
 return result;
end; $$;
revoke all on function public.tripmate_snapshot(),public.tripmate_commit(bigint,jsonb,jsonb,jsonb),public.tripmate_partner_apply(uuid,text,text),public.tripmate_partner_list(uuid),public.tripmate_partner_review(uuid,uuid,text,text) from public,anon,authenticated;
grant execute on function public.tripmate_snapshot(),public.tripmate_commit(bigint,jsonb,jsonb,jsonb),public.tripmate_partner_apply(uuid,text,text),public.tripmate_partner_list(uuid),public.tripmate_partner_review(uuid,uuid,text,text) to service_role;
grant all on public.tripmate_accounts to service_role;
notify pgrst,'reload schema';
commit;
