"""Replay WN5620-11/13/45 against the authenticated HTTP portal and isolated providers.

This records machine-run acceptance evidence. It is not a human browser demonstration,
live Supabase/model check, or another member's review.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests'))
from test_exception_portal import ExceptionPortalTests  # noqa: E402
from test_exception_project_ports import ExceptionProjectPortTests  # noqa: E402
from tripmate.planning.engine import PlanningEngine  # noqa: E402
from tripmate.planning.fixtures import fixture_request, fixture_quotes, FIXTURE_TIME  # noqa: E402


def source_digest():
    digest = hashlib.sha256()
    for directory in ('src', 'tests', 'scripts'):
        for path in sorted((ROOT / directory).rglob('*.py')):
            digest.update(str(path.relative_to(ROOT)).encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def portal_scenario(name, action):
    fixture = ExceptionPortalTests(methodName='test_recovery_uses_current_project_ports_review_delivery_selection_and_restart')
    fixture.setUp()
    try:
        result = action(fixture)
        return {'scenario': name, 'result': 'PASS', **result}
    finally:
        fixture.doCleanups()


def request_decision(fixture, decision, reason):
    pending = fixture.dispatch()
    assert pending['case']['status'] == 'AWAITING_HUMAN_APPROVAL'
    response = fixture.f.clients[fixture.f.operator].call('/api/operations/review', {
        'requestKey': str(uuid4()), 'caseId': fixture.cid, 'revision': pending['revision'],
        'decision': decision, 'reason': reason})
    assert response[0] == 200, response[1]
    return response[1]


def successful_recovery(fixture):
    fixture.record()
    pending = fixture.dispatch()
    assert pending['case']['status'] == 'UNDER_REVIEW'
    assert pending['response'] is None
    investigation = fixture.f.app.exception.investigation(fixture.f.operator, fixture.cid)
    traces = fixture.f.app.operations.traces(fixture.f.operator, fixture.cid)
    actors = {event['actor'] for event in traces}
    assert {'operations', 'exception', 'supplier', 'planning'} <= actors
    assert investigation['result']['review']['outcome'] == 'PASS'
    released = fixture.f.release(fixture.cid, pending['revision'])
    assert released['case']['status'] == 'AWAITING_REQUESTER'
    assert released['canSelectRecovery']
    option = released['recoveryOptions']['options'][0]
    assert option['totalCost'] and isinstance(option['arrivalChangeMinutes'], int)
    assert fixture.f.app.planning.get_version(fixture.baseline['version']['versionId']) == fixture.baseline
    return {'cards': ['WN5620-11', 'WN5620-13', 'WN5620-45'], 'caseId': fixture.cid,
            'runId': investigation['result']['runId'], 'traceCount': len(traces),
            'linkedActors': sorted(actors & {'operations', 'exception', 'supplier', 'planning'}),
            'reviewOutcome': investigation['result']['review']['outcome'],
            'arrivalChangeMinutes': option['arrivalChangeMinutes'],
            'totalCostAUD': option['totalCost'], 'afterDelivery': released['case']['status']}


def no_alternative(fixture):
    fixture.record()
    with fixture.f.app.operations.repository.transaction() as rows:
        for pointer in rows.all('supplier_current'):
            current = fixture.f.app.supplier.repository.current(pointer['offerId'])
            if current['product']['role'] == 'OUTBOUND':
                rows.put('supplier_current', pointer['offerId'], dict(pointer, invalidated=True))
    view = fixture.dispatch()
    investigation = fixture.f.app.exception.investigation(fixture.f.operator, fixture.cid)
    code = investigation['result']['errors'][0]['code']
    assert view['case']['status'] == 'HUMAN_ASSISTANCE' and view['response'] is None
    assert code == 'NO_FEASIBLE_ITINERARY'
    assert {'supplier', 'planning'} <= {event['actor'] for event in investigation['trace']}
    assert fixture.f.app.planning.get_version(fixture.baseline['version']['versionId']) == fixture.baseline
    return {'cards': ['WN5620-13', 'WN5620-45'], 'caseId': fixture.cid,
            'errorCode': code, 'caseStatus': view['case']['status'], 'baselinePreserved': True}


def dependency_failure(fixture):
    fixture.record()
    with patch.object(fixture.f.app.exception.runtime.planning, 'recover', side_effect=RuntimeError('controlled outage')):
        view = fixture.dispatch()
    investigation = fixture.f.app.exception.investigation(fixture.f.operator, fixture.cid)
    assert view['case']['status'] == 'HUMAN_ASSISTANCE' and view['response'] is None
    assert investigation['result']['errors'][0]['code'] == 'TOOL_UNAVAILABLE'
    return {'cards': ['WN5620-13'], 'caseId': fixture.cid,
            'errorCode': 'TOOL_UNAVAILABLE', 'caseStatus': view['case']['status']}


def restricted_approval(fixture):
    fixture.record(restricted=True)
    pending = fixture.dispatch()
    assert pending['case']['status'] == 'AWAITING_HUMAN_APPROVAL'
    assert pending['response'] is None
    unauthorised = fixture.f.clients[fixture.f.traveller].call('/api/operations/review', {
        'requestKey': str(uuid4()), 'caseId': fixture.cid, 'revision': pending['revision'],
        'decision': 'APPROVE', 'reason': 'Unauthorised attempt.'})
    assert unauthorised[0] == 403
    approved = fixture.f.post(fixture.f.operator, 'review', {
        'caseId': fixture.cid, 'revision': pending['revision'], 'decision': 'APPROVE',
        'reason': 'Approved this exact simulated proposal.'})
    assert approved['case']['status'] == 'UNDER_REVIEW'
    assert fixture.f.clients[fixture.f.traveller].call('/api/operations/case?caseId=' + fixture.cid)[1]['response'] is None
    delivered = fixture.f.release(fixture.cid, approved['revision'])
    assert delivered['case']['status'] == 'AWAITING_REQUESTER'
    return {'cards': ['WN5620-11', 'WN5620-13'], 'caseId': fixture.cid,
            'beforeDecision': pending['case']['status'], 'unauthorisedHTTP': unauthorised[0],
            'proposalApprovedThenResponseReviewed': True, 'afterDelivery': delivered['case']['status']}


def decision_path(fixture, decision, expected):
    fixture.record(restricted=True)
    view = request_decision(fixture, decision, 'Controlled acceptance ' + decision)
    assert view['case']['status'] == expected
    assert view['response'] is None
    return {'cards': ['WN5620-11'], 'caseId': fixture.cid,
            'decision': decision, 'caseStatus': view['case']['status'], 'noPrematureResponse': True}


def failed_approval_save(fixture):
    fixture.record(restricted=True)
    pending = fixture.dispatch()
    fixture.f.cloud.fail_commit = True
    try:
        response = fixture.f.clients[fixture.f.operator].call('/api/operations/review', {
            'requestKey': str(uuid4()), 'caseId': fixture.cid, 'revision': pending['revision'],
            'decision': 'APPROVE', 'reason': 'Controlled failed write.'})
    finally:
        fixture.f.cloud.fail_commit = False
    current = fixture.f.clients[fixture.f.operator].call('/api/operations/case?caseId=' + fixture.cid)[1]
    assert response[0] == 503 and current['case']['status'] == 'AWAITING_HUMAN_APPROVAL'
    return {'cards': ['WN5620-11'], 'caseId': fixture.cid,
            'saveFailureHTTP': response[0], 'caseStatus': current['case']['status']}


def confirmed_constraints():
    fixture = ExceptionProjectPortTests(methodName='test_recovery_checks_additional_confirmed_baggage_and_arrival_constraints')
    fixture.setUp()
    try:
        case, context, quotes = fixture.inputs()
        request = context['planningContext']['request']
        spec = context['planningContext']['spec']
        request['hardConstraints'].extend([
            dict(constraintId='baggage', kind='BAGGAGE', description='Carry 20 kg', confirmed=True),
            dict(constraintId='arrival', kind='ARRIVAL_TIME', description='Arrive by 18:00', confirmed=True)])
        spec['constraintBindings'].update(baggage=dict(description='Carry 20 kg', value=20),
                                          arrival=dict(description='Arrive by 18:00', value='2026-10-20T18:00:00+11:00'))
        context['planningContext']['baseline']['request'] = deepcopy(request)
        context['planningContext']['baseline']['spec'] = deepcopy(spec)
        result, snapshot = fixture.run_case(case, context, quotes)
        assert result['status'] == 'SUCCESS'
        options = snapshot['proposal']['options']
        assert options
        for option in options:
            checks = {c['ruleId']: c['outcome'] for c in option['planningRecord']['version']['validationResults']}
            assert checks['CONSTRAINT:baggage'] == checks['CONSTRAINT:arrival'] == 'PASS'
            assert option['planningRecord']['comparison']['baselineVersionId'] == context['itinerary']['versionId']
        return {'scenario': 'confirmed_baggage_arrival_and_downstream_impact', 'result': 'PASS',
                'cards': ['WN5620-45'], 'caseId': case['caseId'], 'candidateCount': len(options),
                'checkedRules': ['CONSTRAINT:baggage', 'CONSTRAINT:arrival'],
                'arrivalChangesMinutes': [o['arrivalChangeMinutes'] for o in options]}
    finally:
        fixture.doCleanups()


def conflicting_constraint():
    fixture = ExceptionProjectPortTests(methodName='test_recovery_checks_additional_confirmed_baggage_and_arrival_constraints')
    fixture.setUp()
    try:
        case, context, quotes = fixture.inputs()
        request = context['planningContext']['request']
        spec = context['planningContext']['spec']
        request['hardConstraints'].append(dict(constraintId='baggage', kind='BAGGAGE',
                                               description='Carry 21 kg', confirmed=True))
        spec['constraintBindings']['baggage'] = dict(description='Carry 21 kg', value=21)
        context['planningContext']['baseline']['request'] = deepcopy(request)
        context['planningContext']['baseline']['spec'] = deepcopy(spec)
        result, snapshot = fixture.run_case(case, context, quotes)
        assert result['status'] == 'HUMAN_ASSISTANCE'
        assert result['errors'][0]['code'] == 'NO_FEASIBLE_ITINERARY'
        assert snapshot['proposal'] is None
        return {'scenario': 'conflicting_confirmed_baggage_constraint', 'result': 'PASS',
                'cards': ['WN5620-45'], 'caseId': case['caseId'],
                'errorCode': result['errors'][0]['code'], 'proposalReleased': False}
    finally:
        fixture.doCleanups()


def unsupported_preference():
    _, request, spec = fixture_request(budget='900.00')
    request['preferences'] = ['Quiet accommodation preferred']
    records, rejected = PlanningEngine(lambda: FIXTURE_TIME).generate(request, fixture_quotes(), spec)
    assert records == []
    assert rejected and all(any(check['ruleId'] == 'PREFERENCE_SCOPE' and check['outcome'] == 'UNSUPPORTED'
                                for check in row['checks']) for row in rejected)
    return {'scenario': 'unsupported_free_text_preference', 'result': 'PASS',
            'cards': ['WN5620-45'], 'rejectedCandidateCount': len(rejected),
            'reasonRule': 'PREFERENCE_SCOPE', 'feasibleCount': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/stage2/acceptance-11-13-45-evidence.json')
    args = parser.parse_args()
    scenarios = [
        portal_scenario('reviewed_recovery_and_four_agent_trace', successful_recovery),
        portal_scenario('no_eligible_alternative', no_alternative),
        portal_scenario('planning_dependency_failure', dependency_failure),
        portal_scenario('restricted_proposal_then_separate_response_approval', restricted_approval),
        portal_scenario('request_revision', lambda f: decision_path(f, 'REQUEST_REVISION', 'AWAITING_REQUESTER')),
        portal_scenario('reject', lambda f: decision_path(f, 'REJECT', 'HUMAN_ASSISTANCE')),
        portal_scenario('approval_save_failure', failed_approval_save),
        confirmed_constraints(),
        conflicting_constraint(),
        unsupported_preference(),
    ]
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    output = {'scope': 'isolated provider doubles; authenticated local HTTP and deterministic project ports',
              'limitations': 'No live Supabase/model, human browser demonstration, or peer sign-off',
              'recordedAtUTC': datetime.now(timezone.utc).isoformat(), 'baseCommit': commit,
              'pythonSourceSha256': source_digest(), 'allPassed': True, 'scenarios': scenarios}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n')
    print(f"PASS: {len(scenarios)} acceptance scenarios; evidence: {args.output}")


if __name__ == '__main__':
    main()
