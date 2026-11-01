"""Operator-supplied, case-bound simulated travel factors."""
from copy import deepcopy
from uuid import uuid4
from tripmate.operations.common import OperationsError
from tripmate.planning.factors import load_factors, FixtureTravelFactors
from tripmate.operations.application import validate_fragment

class StoredTravelFactors:
    def __init__(self, operations):
        self.ops = operations

    def view(self, actor, case_id):
        rec = self.ops.repository.read('case', case_id)
        if not rec or not self.ops.access.authorise(actor, 'REVIEW_CASE', rec['case']):
            raise OperationsError('ACCESS_DENIED', 'Only an authorised operator can inspect travel factors.')
        return {'snapshot': self.ops.repository.read('travel_factors', case_id), 'revision': rec['revision'], 'simulationOnly': True}

    def record(self, actor, body):
        if set(body) != {'requestKey', 'caseId', 'revision', 'data', 'confirmed'} or body['confirmed'] is not True:
            raise OperationsError('INVALID_CONTRACT', 'Confirm the case-bound simulated factor snapshot.')
        self.view(actor, body['caseId'])
        if type(body['revision']) is not int or body['revision'] < 1:
            raise OperationsError('INVALID_CONTRACT', 'Supply the current case revision.')
        try:
            data = load_factors(FixtureTravelFactors(body['data']), {}, [], self.ops.clock(), 'FIXTURE')
            for source in data['sources']:
                validate_fragment('SourceReference', source)
                if source['simulated'] is not True:
                    raise ValueError('Manual inputs must be labelled simulated')
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise OperationsError('INVALID_CONTRACT', 'Supply valid, fresh simulated factor evidence.') from exc
        def save(rows):
            rec = self.ops._owned(rows, actor, body['caseId'], 'REVIEW_CASE', body['revision'])
            if rec['case']['caseType'] not in {'TRAVEL_PLANNING', 'PLAN_REVISION', 'DISRUPTION'} or rec['case']['status'] != 'CONFIRMED':
                raise OperationsError('UNCONFIRMED_REQUEST', 'Reconfirm the request before changing its factors.')
            value = dict(caseId=body['caseId'], confirmedRequest=rec['case']['confirmedRequest'],
                         recordedBy=actor, at=self.ops.clock(), data=data, snapshotId=str(uuid4()))
            rows.put('travel_factor_history', value['snapshotId'], value)
            rows.put('travel_factors', body['caseId'], value)
            rec['revision'] += 1
            self.ops._event(rows, rec, 'TOOL_RESULT', 'Recorded explicit simulated travel factors.', actor=actor)
            self.ops._save(rows, rec)
            return {'caseId': body['caseId'], 'revision': rec['revision'], 'snapshotId': value['snapshotId'], 'simulationOnly': True}
        return self.ops._command(actor, 'travel-factors', body['requestKey'], body, save)

    def snapshot(self, request, quotes, at):
        rec = self.ops.repository.read('case', request['caseId'])
        value = self.ops.repository.read('travel_factors', request['caseId'])
        if (not rec or not value or value['confirmedRequest'] != rec['case']['confirmedRequest']
                or not self.ops.access.authorise(value['recordedBy'], 'REVIEW_CASE', rec['case'])):
            raise OperationsError('STALE_EVIDENCE', 'Record current travel factors for this confirmed request.')
        return deepcopy(value['data'])
