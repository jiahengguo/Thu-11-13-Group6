"""Explicit readiness checks; never expose keys or call providers by default."""
import argparse
import json
import os
from pathlib import Path

from tripmate.api.settings import Settings, has_model_key
from tripmate.planning.common import PlanningError
from tripmate.operations.common import OperationsError
from tripmate.supplier.common import PricingPolicy
from .supabase import Supabase


def readiness(*, demo_pricing=False, check_cloud=False, check_model=False):
    checks = []
    def add(name, status, message):
        checks.append(dict(component=name, status=status, message=message))
    try:
        keys = [os.environ.get(k, '').strip() for k in
                ('SUPABASE_URL', 'SUPABASE_PUBLISHABLE_KEY', 'SUPABASE_SECRET_KEY')]
        if any(not value or value.startswith('REPLACE_') for value in keys):
            raise ValueError()
        cloud = Supabase(*keys)
        if check_cloud:
            snapshot = cloud.rpc('tripmate_snapshot')
            if not isinstance(snapshot, dict) or not {'version', 'records', 'traces', 'commands'} <= snapshot.keys():
                raise ValueError()
        add('cloud', 'VERIFIED' if check_cloud else 'CONFIGURED',
            'Private storage RPC is reachable.' if check_cloud else 'Credentials configured; connectivity not tested.')
    except (ValueError, OperationsError):
        add('cloud', 'BLOCKED', 'Check Supabase URL, separate keys, network and applied migrations; provider details omitted.')
    try:
        values = [os.environ.get(k, '').strip() for k in
                  ('TRIPMATE_MARKUP_RATE', 'TRIPMATE_MINIMUM_MARGIN', 'TRIPMATE_PRICING_CONFIG_VERSION')]
        if demo_pricing:
            policy = PricingPolicy('0.10', '15.00', 'demo-2026-10-24')
        else:
            if not all(values) or any(v.startswith('REPLACE_') for v in values) or values[2] == 'unconfigured':
                raise ValueError()
            policy = PricingPolicy(*values)
        add('pricing', 'CONFIGURED', 'Explicit demo pricing selected.' if demo_pricing else 'Versioned pricing configured.')
    except (ValueError, ArithmeticError):
        add('pricing', 'BLOCKED', 'Set all three pricing values or explicitly select --demo-pricing.')
    try:
        if not has_model_key():
            raise ValueError()
        from tripmate.adapters.campus import CampusLLMService
        client = CampusLLMService(timeout=20, max_completion_tokens=1024)
        if check_model:
            # A genuine shared Agent extraction call, not a canned reply or private case.
            schema = dict(type='object', properties={'partySize': {'type': 'integer', 'minimum': 1}},
                          required=['partySize'], additionalProperties=False)
            if client.extract('Two travellers are requesting a simulated trip.', schema) != {'partySize': 2}:
                raise ValueError()
        add('model', 'VERIFIED' if check_model else 'CONFIGURED',
            'Course model returned schema-valid extraction.' if check_model else 'Model configured; no live request made.')
    except PlanningError as exc:
        add('model', 'BLOCKED', 'Check course key, provider/model configuration and campus network/VPN; no simulated success substituted.')
        checks[-1]['code'] = exc.code if exc.code in {'TOOL_UNAVAILABLE', 'LLM_INVALID_OUTPUT', 'INVALID_CONTRACT',
                                                     'VERIFICATION_FAILED'} else 'MODEL_CHECK_FAILED'
    except ValueError:
        add('model', 'BLOCKED', 'Check course key, provider/model configuration and campus network/VPN; no simulated success substituted.')
        checks[-1]['code'] = 'MODEL_CONFIGURATION_OR_RESULT_INVALID'
    return dict(ready=all(c['status'] != 'BLOCKED' for c in checks), checks=checks,
                liveChecks=dict(cloud=check_cloud, model=check_model))


def main():
    parser = argparse.ArgumentParser(description='Check portal configuration without revealing credentials')
    parser.add_argument('--env-file', type=Path, default=Path('.env'))
    parser.add_argument('--demo-pricing', action='store_true')
    parser.add_argument('--check-cloud', action='store_true', help='Read the private storage RPC; never writes')
    parser.add_argument('--check-model', action='store_true', help='Make one small real course-model extraction request')
    args = parser.parse_args()
    try:
        Settings.load(args.env_file)
        report = readiness(demo_pricing=args.demo_pricing, check_cloud=args.check_cloud, check_model=args.check_model)
    except ValueError:
        parser.exit(1, 'Invalid execution configuration; check the configuration template.\n')
    print(json.dumps(report, indent=2))
    return 0 if report['ready'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
