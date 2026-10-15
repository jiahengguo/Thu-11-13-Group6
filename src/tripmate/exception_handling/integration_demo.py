"""Runnable, explicitly synthetic integration evidence; no real account or service.

Scripted operator decisions only run when explicitly requested by the CLI flag.
"""
import argparse
import json
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

from tripmate.fixtures import FixtureRepository
from tripmate.operations import OperationsRepository, OperationsService
from tripmate.planning.fixtures import fixture_request, FIXTURE_TIME
from tripmate.planning.integration import B03ApprovedOffers
from tripmate.planning.engine import PlanningEngine
from .fixtures import fixture
from .repository import ExceptionRepository
from .ports import SimulatedSupplier, SimulatedPlanning
from .project_ports import ProjectSupplier, ProjectPlanning
from .integration import connect_exception


class SavedContexts:
    """Trusted local fixture input. No public write endpoint is exposed."""
    def __init__(self, repository):
        self.repository = repository

    def load(self, case_id):
        context = self.repository.read('exception_context', case_id)
        if context is None:
            raise ValueError('No explicitly supplied Exception evidence for this case.')
        return context


def connect_saved_demo(operations, fixtures, database):
    config = operations.repository.read('exception_fixture', 'configuration')
    if not config:
        raise ValueError('Seed this database with exception_handling.integration_demo first.')
    operations.clock = lambda: config['assessedAt']
    operations.entitlement.clock = operations.clock
    supplier = B03ApprovedOffers(fixtures)
    return connect_exception(operations, SavedContexts(operations.repository), ExceptionRepository(database),
                             ProjectSupplier(supplier) if config['project'] else SimulatedSupplier(),
                             ProjectPlanning() if config['project'] else SimulatedPlanning())


def project_context(case, supplier):
    """A declared baseline fixture, generated from the actual resettable B03 data."""
    _, request, spec = fixture_request()
    request.update(caseId=case['caseId'], correlationId=case['correlationId'], travellerId=case['requesterId'])
    records, _ = PlanningEngine(lambda: FIXTURE_TIME).generate(
        request, supplier.find_selectable(request, FIXTURE_TIME), spec)
    baseline = records[0]
    baseline['version']['planId'] = 'itinerary:active-paid'
    _, ctx = fixture()
    ctx.update(caseId=case['caseId'], travellerId=case['requesterId'], assessedAt=FIXTURE_TIME,
               constraints=[], supplierOffers=[])
    items = [dict(itemId=i['itemId'], kind={'TRANSPORT':'TRANSPORT','ACCOMMODATION':'HOTEL','ACTIVITY':'ACTIVITY'}[i['productType']],
                  origin=i['origin'], destination=i['destination'], startAt=i['startAt'], endAt=i['endAt'],
                  remainingCost=i['quotedPrice']['amount'], sourceIds=i['sourceIds']) for i in baseline['version']['items']]
    ctx['itinerary'].update(versionId=baseline['version']['versionId'], travellerId=case['requesterId'], items=items)
    ctx['issue']['itemId'] = next(i['itemId'] for i in items if i['kind'] == 'TRANSPORT')
    ctx['evidence'] = [dict(source=deepcopy(s), validUntil='2026-10-20T00:00:00+11:00', assertions=[],
                            note='Explicit synthetic active baseline, assembled from the project B03 inventory.')
                       for s in baseline['version']['sourceReferences']]
    ctx['evidence'][0]['assertions'] = [dict(key=ctx['issue']['itemId']+':status', value='CANCELLED')]
    recovery = deepcopy(request)
    recovery['baselineVersionId'] = baseline['version']['versionId']
    ctx['planningContext'] = dict(request=recovery, spec=spec, baseline=baseline)
    return ctx


def demonstrate(database, kind='disruption', scenario='normal', scripted_decisions=False):
    path = Path(database)
    fixtures = FixtureRepository(path)
    fixtures.ensure_seeded()
    project = kind == 'disruption' and scenario == 'normal'
    at = FIXTURE_TIME if project else ('2026-10-20T16:00:00+11:00' if kind == 'complaint' else '2026-10-20T08:00:00+11:00')
    repository = OperationsRepository(path)
    config = dict(assessedAt=at, project=project)
    with repository.transaction() as rows:
        previous = rows.get('exception_fixture', 'configuration')
        if previous and previous != config:
            raise ValueError('Use a separate database for a different fixture clock or adapter configuration.')
        rows.put('exception_fixture', 'configuration', config)
    operations = OperationsService(repository, fixtures, clock=lambda: at)
    supplier = B03ApprovedOffers(fixtures)
    bridge = connect_saved_demo(operations, fixtures, path)
    intents = [dict(caseType=kind.upper(), fields=dict(planId='itinerary:active-paid',
                                                     details='Explicit synthetic ' + kind + ' demonstration.'))]
    key = lambda: str(uuid4())
    intake = operations.intake('traveller:paid', key(), 'Synthetic confirmed request', intents)
    case_id = operations.confirm('traveller:paid', key(), intake['id'], 1, intents, True)['caseIds'][0]
    case = operations.case_view('traveller:paid', case_id)['case']
    if project:
        context = project_context(case, supplier)
    else:
        _, context = fixture(kind.upper(), scenario)
        context.update(caseId=case_id, travellerId=case['requesterId'])
        context['itinerary']['travellerId'] = case['requesterId']
    with repository.transaction() as rows:
        rows.put('exception_context', case_id, context)
    view = operations.dispatch('traveller:paid', key(), case_id, 1)
    history = [view['case']['status']]
    if scripted_decisions:
        for _ in range(4):
            if view['case']['status'] not in {'UNDER_REVIEW', 'AWAITING_HUMAN_APPROVAL'}:
                break
            view = operations.review_case('operator:fixture', key(), case_id, view['revision'],
                                           'APPROVE', 'Explicitly scripted fixture decision; not a real human approval.')
            history.append(view['case']['status'])
            if view['case']['status'] == 'READY_TO_RESPOND':
                operations.deliver('operator:fixture', key(), case_id, view['revision'])
                view = operations.case_view('traveller:paid', case_id)
                history.append(view['case']['status'])
                if (view.get('recoveryOptions') and repository.read('case', case_id).get('exceptionStage')
                        == 'AWAITING_TRAVELLER_DECISION'):
                    presented = view['recoveryOptions']
                    view = operations.select_exception('traveller:paid', key(), case_id, view['revision'],
                                                         presented['runId'], presented['options'][0]['offerId'], True)
                    history.append(view['case']['status'])
        if repository.read('case', case_id).get('exceptionStage') == 'RECOMMENDATION_DELIVERED':
            view = operations.case_action('operator:fixture', key(), case_id, view['revision'], 'CLOSE_CASE',
                                           'Close unresolved after recommendation delivery; real travel action remains outside this demonstration.')
            history.append(view['case']['status'])
    return dict(simulationOnly=True, scriptedOperatorDecisions=scripted_decisions,
                projectSupplierAndPlanning=project, stages=history, case=operations.case_view('operator:fixture', case_id),
                investigation=bridge.investigation('operator:fixture', case_id), traces=operations.traces('operator:fixture', case_id))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=['disruption', 'complaint'], default='disruption')
    parser.add_argument('--scenario', choices=['normal', 'approval', 'conflict', 'missing-evidence'], default='normal')
    parser.add_argument('--database', default='data/exception-integration-demo.sqlite3')
    parser.add_argument('--scripted-decisions', action='store_true', help='Explicitly demonstrate simulated operator/traveller decisions.')
    args = parser.parse_args()
    print(json.dumps(demonstrate(args.database, args.case, args.scenario, args.scripted_decisions), indent=2))


if __name__ == '__main__':
    main()
