"""Explicit cloud demo provisioning; dry-run by default, no embedded passwords."""
import argparse
import hashlib
from datetime import date, datetime, timedelta
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
from uuid import UUID
from zoneinfo import ZoneInfo

from tripmate.api.settings import Settings
from tripmate.operations import OperationsService
from tripmate.operations.common import OperationsError, instant
from tripmate.supplier.gateway import SupplierGateway
from tripmate.supplier.common import PricingPolicy
from .repository import SupabaseOperationsRepository, NoUserFixtures
from .supabase import Supabase

KINDS = ('free', 'paid', 'supplier', 'operator')


def namespace_value(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-z][a-z0-9-]{2,39}', value):
        raise ValueError('Use a 3..40 character lowercase demo namespace.')
    return value


def protect_manifest(path):
    """Restrict credentials to the current owner using the host's permission model."""
    if os.name != 'nt':
        path.chmod(0o600)
        return
    script = """
$ErrorActionPreference = 'Stop'
$sid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
$acl = New-Object System.Security.AccessControl.FileSecurity
$acl.SetOwner($sid)
$acl.SetAccessRuleProtection($true, $false)
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule($sid, 'FullControl', 'Allow')
$acl.AddAccessRule($rule)
[System.IO.File]::SetAccessControl($env:TRIPMATE_MANIFEST_ACL_PATH, $acl)
"""
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script],
        env=dict(os.environ, TRIPMATE_MANIFEST_ACL_PATH=str(path.resolve())),
        capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise OSError('Could not restrict demo credential file permissions.')


def save_manifest(path, data):
    if path.is_symlink():
        raise ValueError('Credential manifest cannot be a symlink.')
    temporary = path.with_name(path.name + '.tmp')
    # Exclusive creation prevents following pre-existing paths when writing secrets.
    with temporary.open('x') as stream:
        protect_manifest(temporary)
        json.dump(data, stream, indent=2)
        stream.write('\n')
    temporary.replace(path)
    protect_manifest(path)


def prepare_accounts(cloud, namespace, manifest_path):
    namespace_value(namespace)
    manifest_path = Path(manifest_path)
    if manifest_path.is_symlink():
        raise ValueError('Credential manifest cannot be a symlink.')
    data = json.loads(manifest_path.read_text()) if manifest_path.exists() else dict(
        namespace=namespace, project=cloud.url, accounts={})
    if data['namespace'] != namespace or data['project'] != cloud.url:
        raise ValueError('Manifest belongs to another project or namespace; do not reuse it.')
    # Fail before creating users when the explicit demo migration is absent.
    ready = cloud.rpc('tripmate_prepare_demo_profile', dict(actor=None, demo_namespace=namespace, member_kind=None))
    if ready.get('demoProvisioning') != 1:
        raise ValueError('Apply the demo-profile migration before provisioning.')
    for kind in KINDS:
        email = namespace + '.' + kind + '@example.invalid'
        account = data['accounts'].get(kind)
        if account:
            user = cloud.request('/auth/v1/admin/users/' + str(UUID(account['id'])), admin=True)
            user = user.get('user', user)
            if user.get('email') != email or user.get('app_metadata', {}).get('tripmate_demo') != namespace:
                raise ValueError('Existing demo identity cannot be verified; no role was changed.')
        else:
            password = secrets.token_urlsafe(24)
            user = cloud.request('/auth/v1/admin/users', 'POST', dict(email=email, password=password,
                email_confirm=True, app_metadata={'tripmate_demo': namespace}), admin=True)
            user = user.get('user', user)
            account = dict(id=str(UUID(user['id'])), email=email, password=password)
            data['accounts'][kind] = account
            # Save each new identity immediately so a later failure can resume safely.
            save_manifest(manifest_path, data)
        cloud.rpc('tripmate_prepare_demo_profile', dict(actor=account['id'], demo_namespace=namespace, member_kind=kind))
    return data


def supplier_inputs(namespace, scenario, start, at):
    zone = ZoneInfo('Australia/Sydney')
    def when(day, hour):
        return datetime.combine(start + timedelta(days=day), datetime.min.time(), zone).replace(hour=hour).isoformat()
    specs = [('express', 'OUTBOUND', 0, 8, 0, 11), ('coach', 'OUTBOUND', 0, 6, 0, 16),
             ('stay', 'STAY', 0, 17, 2, 10), ('activity', 'ACTIVITY', 1, 10, 1, 12)]
    result = []
    for name, role, first, begins, last, ends in specs:
        product_type = {'OUTBOUND': 'TRANSPORT', 'STAY': 'ACCOMMODATION', 'ACTIVITY': 'ACTIVITY'}[role]
        payload = dict(offerReference=namespace + '-' + scenario + '-' + name,
            productId=namespace + '-' + scenario + '-' + name, productType=product_type,
            availableQuantity=1, quotedQuantity=1, unitBasis='One complete simulated party package',
            supplierCost=dict(amount='180.00', currency='AUD'), mandatoryChargesIncluded=True,
            validFrom=(instant(at) - timedelta(days=1)).isoformat(), validUntil=when(3, 23),
            cancellationTerms='Simulation: refundable until 24 hours before service; no real reservation.',
            commercialTerms=[], sourceReference='synthetic://demo/' + namespace + '/' + scenario + '/' + name,
            product=dict(role=role, startAt=when(first, begins), endAt=when(last, ends),
                origin='Sydney Central' if role == 'OUTBOUND' else 'Melbourne Centre', destination='Melbourne Centre',
                partySize=1, accessible=True, baggageKg=20, comfort='0.80' if name == 'express' else '0.60',
                reliability='0.95', minConnectionMinutes=30, openingStart=when(1, 9) if role == 'ACTIVITY' else None,
                openingEnd=when(1, 17) if role == 'ACTIVITY' else None))
        result.append((name, payload))
    for name in ('zero-stock', 'expired', 'restricted'):
        payload = json.loads(json.dumps(result[0][1]))
        payload.update(offerReference=namespace + '-' + scenario + '-' + name,
                       productId=namespace + '-' + scenario + '-' + name,
                       sourceReference='synthetic://demo/' + namespace + '/' + scenario + '/' + name)
        if name == 'zero-stock':
            payload['availableQuantity'] = 0
        elif name == 'expired':
            payload.update(validFrom=(instant(at) - timedelta(days=2)).isoformat(),
                           validUntil=(instant(at) - timedelta(days=1)).isoformat())
        else:
            payload['commercialTerms'] = ['Simulated binding commitment; explicit scoped human decision required.']
        result.append((name, payload))
    return result


def seed_data(cloud, accounts, namespace, scenario='demo', start_date=None, clock=None):
    namespace_value(namespace)
    namespace_value(scenario)
    repository = SupabaseOperationsRepository(cloud)
    operations = OperationsService(repository, NoUserFixtures(), seed_profiles=False)
    if clock is not None:
        operations.clock = clock
        operations.entitlement.clock = clock
    for kind in KINDS:
        profile = operations.profile(accounts[kind]['id'])
        expected = 'OPERATOR' if kind == 'operator' else 'SUPPLIER' if kind == 'supplier' else 'TRAVELLER'
        if not profile or not profile['verified'] or profile['role'] != expected or (kind == 'paid' and profile['membership'] != 'PAID'):
            raise ValueError('Prepare verified demo identities and membership before seeding data.')
    gateway = SupplierGateway(operations, policy=PricingPolicy('0.10', '15.00', 'demo-2026-10-24'))
    key = namespace + '/' + scenario
    previous = repository.read('demo_setup', key)
    owners = {kind: accounts[kind]['id'] for kind in KINDS}
    if previous and previous['owners'] != owners:
        raise ValueError('This scenario belongs to another set of accounts.')
    today = instant(operations.clock()).astimezone(ZoneInfo('Australia/Sydney')).date()
    start = date.fromisoformat(start_date) if start_date else date.fromisoformat(previous['startDate']) if previous else today + timedelta(days=2)
    if start < today or (previous and previous['startDate'] != start.isoformat()):
        raise ValueError('Scenario dates have passed or changed; choose a new scenario name, not a silent rewrite.')
    existing = repository.read('demo_seed_result', key)
    if existing:
        return existing
    if previous is None:
        previous = dict(owners=owners, startDate=start.isoformat(), createdAt=operations.clock(), simulationOnly=True)
        with repository.transaction() as rows:
            rows.put('demo_setup', key, previous)
    cases = {}
    for name, quotation in supplier_inputs(namespace, scenario, start, previous['createdAt']):
        intents = [dict(caseType='OFFER', fields=dict(details='Seeded synthetic quotation; not a live supplier submission.', supplierOffer=quotation))]
        prefix = 'seed-' + hashlib.sha256((key + '/' + name).encode()).hexdigest()[:32]
        intake = operations.intake(owners['supplier'], prefix + '/intake', 'Explicit simulated supplier seed data.', intents)
        confirmed = operations.confirm(owners['supplier'], prefix + '/confirm', intake['id'], 1, intents, True)
        case_id = confirmed['caseIds'][0]
        operations.dispatch(owners['supplier'], prefix + '/dispatch', case_id, 1)
        expected = 'EXPIRED' if name == 'expired' else 'REVISION_REQUIRED' if name == 'zero-stock' else 'UNDER_REVIEW'
        if gateway.view(owners['supplier'], case_id)['status'] != expected:
            raise OperationsError('TOOL_UNAVAILABLE', 'A seed assessment is incomplete; inspect the saved case before retrying.')
        cases[name] = case_id
    drafts = {}
    for kind in ('free', 'paid'):
        fields = dict(origin='Sydney Central', destination='Melbourne Centre', partySize=1,
            budgetCeiling=dict(amount='900.00', currency='AUD'), travelDates=dict(startDate=start.isoformat(),
            endDate=(start + timedelta(days=2)).isoformat()), rankingMode='VALUE', preferences=[], constraints=[])
        intake = operations.intake(owners[kind], key + '/draft/' + kind, 'Seeded simulated itinerary request; traveller confirmation still required.',
                                  [dict(caseType='TRAVEL_PLANNING', fields=fields)])
        drafts[kind] = intake['id']
    result = dict(namespace=namespace, scenario=scenario, startDate=start.isoformat(), supplierCases=cases,
                  travellerDrafts=drafts, simulationOnly=True, operatorReviewRequired=True)
    with repository.transaction() as rows:
        rows.put('demo_seed_result', key, result)
    return result


def main():
    parser = argparse.ArgumentParser(description='Prepare dedicated simulated cloud accounts/data; dry-run by default')
    parser.add_argument('--env-file', type=Path, default=Path('.env'))
    parser.add_argument('--namespace', default='stage2-demo')
    parser.add_argument('--scenario', default='demo')
    parser.add_argument('--start-date')
    parser.add_argument('--manifest', type=Path, default=Path('.demo-accounts.local.json'))
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--confirm-project', help='Must exactly match the configured Supabase URL for a real cloud write')
    args = parser.parse_args()
    try:
        namespace_value(args.namespace)
        namespace_value(args.scenario)
        if not args.apply:
            print(json.dumps(dict(dryRun=True, accounts=[args.namespace + '.' + k + '@example.invalid' for k in KINDS],
                cloudWrites=False, operatorReviewRequired=True), indent=2))
            return 0
        Settings.load(args.env_file)
        cloud = Supabase.from_env()
        if args.confirm_project != cloud.url:
            raise ValueError('Explicitly confirm the exact project URL before creating dedicated test identities.')
        manifest = prepare_accounts(cloud, args.namespace, args.manifest)
        result = seed_data(cloud, manifest['accounts'], args.namespace, args.scenario, args.start_date)
        print(json.dumps(result, indent=2))
        print('Credentials are in the owner-only local manifest; no passwords were printed. No offers were approved.')
        return 0
    except (ValueError, OperationsError, OSError):
        parser.exit(1, 'Demo setup incomplete. Check project confirmation, migration, manifest and network. '
                       'Existing data was not reset; retain the local manifest to resume.\n')


if __name__ == '__main__':
    raise SystemExit(main())
