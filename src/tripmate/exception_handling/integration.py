"""Explicit Operations bridge. Business evidence and specialist ports are injected.

No fixture case is silently substituted for a customer's confirmed case. Imported
snapshots, traces and proposal decisions commit with the Operations case update.
"""
from copy import deepcopy
from uuid import uuid4

from tripmate.contracts import validate
from tripmate.operations.common import OperationsError, instant
from tripmate.agents.exception import CustomerExceptionAgent
from .runtime import ExceptionRuntime


class OperationsContexts:
    def __init__(self, operations, source):
        self.operations, self.source = operations, source

    def load(self, case_id):
        rec = self.operations.repository.read('case', case_id)
        if (not rec or rec['case']['status'] != 'IN_PROGRESS'
                or rec['case']['primaryHandler'] != 'exception'
                or not self.operations.access.authorise(rec['case']['requesterId'], 'READ_CASE', rec['case'])):
            raise OperationsError('ACCESS_DENIED', 'Use the current confirmed Operations case.')
        context = self.source.load(case_id)
        planning = context.get('planningContext')
        if planning and planning['baseline']['version']['planId'] != rec['fields']['planId']:
            raise OperationsError('ACCESS_DENIED', 'Planning baseline must belong to the affected confirmed trip.')
        return context


class ExceptionBridge:
    def __init__(self, operations, contexts, repository, supplier, planning, reviewer, complaint_findings=None):
        self.operations, self.repository = operations, repository
        if reviewer is None:
            from .review import exception_reviewer
            reviewer = exception_reviewer(operations.clock)
        self.runtime = ExceptionRuntime(OperationsContexts(operations, contexts), repository,
                                        supplier, planning, reviewer, clarification=True, complaint_findings=complaint_findings)

    def handle_case(self, case):
        current = self.operations.repository.read('case', case['caseId'])
        if not current or current['case'] != case:
            raise OperationsError('UNCONFIRMED_REQUEST', 'Exception requires the current persisted case.')
        return CustomerExceptionAgent(self.runtime).handle_case(case)

    def receive(self, rows, rec, result):
        snapshot = self.repository.get(result['runId'])
        if (not snapshot or snapshot['result'] != result or snapshot['inputCase'] != rec['case']
                or snapshot['handoffTo'] != 'operations'):
            raise OperationsError('INVALID_CONTRACT', 'Exception result is not a saved matching handoff.')
        if not rows.get('exception_run', result['runId']):
            for event in snapshot['trace']:
                rows.trace(event)
            rows.put('exception_run', result['runId'], snapshot)
        rec['exceptionRunId'] = result['runId']
        rec['exceptionApprovalId'] = None
        rec['exceptionDecisionId'] = None
        rec['exceptionSelection'] = None
        rec['exceptionStage'] = 'INVESTIGATED'
        rec['specialistResult'] = deepcopy(result)
        rec['sources'] += [deepcopy(s) for s in result['sourceReferences']
                           if s['sourceId'] not in {r['sourceId'] for r in rec['sources']}]
        rec['case']['sourceReferences'] = deepcopy(rec['sources'])
        rec['case']['validationResults'] = deepcopy(result['validationResults'])
        rec['case']['requiresApproval'] = result['requiresApproval']
        rec['response'], rec['review'], rec['approvalId'] = None, None, None
        if result['status'] == 'APPROVAL_PENDING':
            self._current(snapshot)
            approvals = snapshot['approvals']
            if (len(approvals) != 1 or result['approvalIds'] != [approvals[0]['approvalId']]
                    or approvals[0]['status'] != 'PENDING' or approvals[0]['decision'] is not None
                    or approvals[0]['subject'] != snapshot['proposal']['subject']
                    or approvals[0]['reviewId'] != result['review']['reviewId']):
                raise OperationsError('APPROVAL_REQUIRED', 'A scoped pending proposal approval is required.')
            approval = deepcopy(approvals[0])
            validate('Approval', approval)
            rows.put('exception_approval', approval['approvalId'], approval)
            rec['exceptionApprovalId'] = approval['approvalId']
            rec['case']['status'] = 'AWAITING_HUMAN_APPROVAL'
            rec['exceptionStage'] = 'AWAITING_HUMAN_DECISION'
        elif result['status'] == 'SUCCESS':
            self._current(snapshot)
            rec['response'] = result['proposedResponse']
            rec['responseVersion'] += 1
            rec['case']['status'] = 'UNDER_REVIEW'
            rec['exceptionStage'] = 'UNDER_REVIEW'
        else:
            rec['case']['status'] = 'AWAITING_REQUESTER' if result['status'] == 'REVISION_REQUIRED' else 'HUMAN_ASSISTANCE'
            rec['case']['unresolvedQuestions'] = [e['message'] for e in result['errors']] or [result['nextAction']]
            rec['exceptionStage'] = 'AWAITING_CLARIFICATION' if result['status'] == 'REVISION_REQUIRED' else 'HUMAN_TAKEOVER'

    def _current(self, snapshot):
        result, proposal = snapshot['result'], snapshot['proposal']
        at = instant(self.operations.clock())
        if (not proposal or not result['review'] or result['review']['outcome'] != 'PASS'
                or result['review']['subject'] != proposal['subject']
                or not result['validationResults']
                or any(c['outcome'] != 'PASS' for c in result['validationResults'])
                or not result['proposedResponse']):
            raise OperationsError('REVIEW_FAILED', 'A passed review and checks for this proposal are required.')
        if (instant(snapshot['assessedAt']) > at
                or instant(result['review']['reviewedAt']) > at
                or any(s['freshness'] != 'FRESH' or instant(s['capturedAt']) > at
                       for s in result['sourceReferences'])
                or any(instant(e['validUntil']) <= at for e in snapshot['context']['evidence'])):
            raise OperationsError('STALE_EVIDENCE', 'Refresh the Exception evidence before release or approval.')
        selected = {option['offerId'] for option in proposal.get('options', [])}
        if any(instant(o['validUntil']) <= at for o in snapshot['context']['supplierOffers']
               if o['offerId'] in selected):
            raise OperationsError('STALE_EVIDENCE', 'A proposed supplier alternative has expired.')
        for option in proposal.get('options', []):
            record = option.get('planningRecord')
            if record:
                from tripmate.planning.validation import PlanningValidator
                context = deepcopy(snapshot['context'])
                context['assessedAt'] = self.operations.clock()
                current = {q['offer']['offerId']: q for q in self.runtime.supplier.alternatives(context)}
                if any(current.get(q['offer']['offerId']) != q for q in record['quotes']):
                    raise OperationsError('STALE_EVIDENCE', 'Supplier resources or terms changed; investigate a new proposal before release.')
                checks = PlanningValidator(record['request'], record['quotes'], record['spec'],
                                            self.operations.clock).validate_plan(record['version'])
                if any(c['outcome'] != 'PASS' for c in checks):
                    raise OperationsError('STALE_EVIDENCE', 'The saved Planning candidate no longer passes validation.')

    def decide(self, rows, rec, actor, decision, reason, edited_text):
        """Called inside Operations' authorised/idempotent review transaction."""
        if not rec.get('exceptionApprovalId'):
            return False
        if edited_text is not None:
            raise OperationsError('UNCONFIRMED_REQUEST', 'Decide the saved proposal before editing an external response.')
        pending = rows.get('exception_approval', rec['exceptionApprovalId'])
        snapshot = rows.get('exception_run', rec['exceptionRunId'])
        if (not pending or pending['status'] != 'PENDING' or not snapshot
                or rec.get('exceptionDecisionId')
                or rec['case']['status'] != 'AWAITING_HUMAN_APPROVAL'
                or pending['subject'] != snapshot['proposal']['subject']
                or rec.get('specialistResult') != snapshot['result']):
            raise OperationsError('APPROVAL_REQUIRED', 'Reload the current pending Exception proposal.')
        if decision == 'APPROVE':
            self._current(snapshot)
        if decision == 'TAKE_OVER':
            rec['case']['status'] = 'HUMAN_ASSISTANCE'
        else:
            decided = deepcopy(pending)
            decided.update(approvalId=str(uuid4()), status='DECIDED', decision=decision,
                           decidedAt=self.operations.clock(), operatorId=actor, reason=reason)
            validate('Approval', decided)
            rows.put('exception_approval', decided['approvalId'], decided)
            rec['exceptionDecisionId'] = decided['approvalId']
            self.operations._event(rows, rec, 'APPROVAL_DECIDED',
                                   'Exception proposal decision: ' + decision + '; ' + reason,
                                   actor=actor, approval_id=decided['approvalId'])
            if decision == 'APPROVE':
                rec['response'] = snapshot['result']['proposedResponse']
                rec['responseVersion'] += 1
                rec['case']['status'] = 'UNDER_REVIEW'
            else:
                rec['case']['status'] = 'AWAITING_REQUESTER' if decision == 'REQUEST_REVISION' else 'HUMAN_ASSISTANCE'
        rec['case']['unresolvedQuestions'] = [] if decision == 'APPROVE' else [reason]
        rec['exceptionApprovalId'] = None
        rec['review'], rec['approvalId'] = None, None
        rec['exceptionStage'] = ('UNDER_REVIEW' if decision == 'APPROVE' else
                                 'AWAITING_CLARIFICATION' if decision == 'REQUEST_REVISION' else 'HUMAN_TAKEOVER')
        return True

    def invalidate_confirmation(self, rows, rec):
        rec['exceptionRunId'] = None
        rec['exceptionApprovalId'] = None
        rec['exceptionDecisionId'] = None
        rec['exceptionSelection'] = None
        rec['exceptionStage'] = 'AWAITING_INVESTIGATION'

    def after_delivery(self, rows, rec):
        snapshot = rows.get('exception_run', rec['exceptionRunId'])
        if snapshot['proposal']['kind'] != 'RECOVERY':
            return False
        rec['case']['status'] = 'AWAITING_REQUESTER'
        rec['exceptionStage'] = ('RECOMMENDATION_DELIVERED' if rec.get('exceptionSelection')
                                 else 'AWAITING_TRAVELLER_DECISION')
        rec['case']['unresolvedQuestions'] = ([] if rec.get('exceptionSelection') else
                                             ['Confirm an exact presented recovery option or decline the options.'])
        self.operations._event(rows, rec, 'HANDOFF',
                               'Recommendation delivered through Operations; the trip is not represented as recovered.', 'PENDING')
        return True

    def presented_options(self, rows, rec):
        snapshot = rows.get('exception_run', rec['exceptionRunId'])
        if snapshot['proposal']['kind'] != 'RECOVERY':
            return None
        return dict(runId=rec['exceptionRunId'], subject=snapshot['proposal']['subject'], options=[
            {k: deepcopy(option[k]) for k in ('offerId', 'totalCost', 'currency', 'arrivalChangeMinutes', 'terms', 'items')}
            for option in snapshot['proposal']['options']])

    def select(self, rows, rec, actor, run_id, option_id, confirmed):
        if (confirmed is not True or actor != rec['case']['requesterId']
                or rec.get('exceptionRunId') != run_id
                or rec.get('exceptionStage') != 'AWAITING_TRAVELLER_DECISION'
                or rec['case']['status'] != 'AWAITING_REQUESTER'):
            raise OperationsError('UNCONFIRMED_REQUEST', 'Confirm a current presented recovery option as its traveller.')
        self.ensure_release(rows, rec)
        snapshot = rows.get('exception_run', run_id)
        if option_id is None:
            rec['case']['status'] = 'HUMAN_ASSISTANCE'
            rec['exceptionStage'] = 'HUMAN_TAKEOVER'
            rec['case']['unresolvedQuestions'] = ['Traveller declined all presented recovery options.']
        else:
            option = next((o for o in snapshot['proposal']['options'] if o['offerId'] == option_id), None)
            if option is None:
                raise OperationsError('INVALID_CONTRACT', 'Select one of the exact presented options.')
            rec['exceptionSelection'] = dict(runId=run_id, subject=snapshot['proposal']['subject'],
                                             optionId=option_id, confirmedAt=self.operations.clock(), travellerId=actor)
            rec['case']['status'] = 'UNDER_REVIEW'
            rec['case']['unresolvedQuestions'] = []
            rec['exceptionStage'] = 'UNDER_REVIEW'
            rec['response'] = 'Confirmed recovery recommendation ' + option_id + '. ' + snapshot['result']['proposedResponse']
            rec['responseVersion'] += 1
            rec['review'], rec['approvalId'] = None, None
        self.operations._event(rows, rec, 'CONFIRMATION',
                               'Traveller confirmed an exact option.' if option_id else 'Traveller declined recovery options.', actor=actor)

    def ensure_release(self, rows, rec):
        snapshot = rows.get('exception_run', rec['exceptionRunId'])
        if not snapshot or snapshot['result'] != rec.get('specialistResult'):
            raise OperationsError('INVALID_CONTRACT', 'Saved Exception result is unavailable or superseded.')
        self._current(snapshot)
        if snapshot['result']['requiresApproval']:
            decision = rows.get('exception_approval', rec.get('exceptionDecisionId'))
            pending = snapshot['approvals'][0]
            if (not decision or decision['decision'] != 'APPROVE' or decision['status'] != 'DECIDED'
                    or decision['subject'] != snapshot['proposal']['subject']
                    or decision['reviewId'] != pending['reviewId'] or decision['scope'] != pending['scope']):
                raise OperationsError('APPROVAL_REQUIRED', 'This exact Exception proposal still needs human approval.')

    def investigation(self, actor, case_id):
        rec = self.operations.repository.read('case', case_id)
        if (not rec or not self.operations.access.authorise(actor, 'READ_CASE', rec['case'])
                or self.operations.profile(actor)['role'] != 'OPERATOR'):
            raise OperationsError('ACCESS_DENIED', 'Only an authorised operator can inspect investigation drafts.')
        run_id = rec.get('exceptionRunId')
        return deepcopy(self.operations.repository.read('exception_run', run_id)) if run_id else None


def connect_exception(operations, contexts, repository, supplier, planning, reviewer=None, complaint_findings=None):
    bridge = ExceptionBridge(operations, contexts, repository, supplier, planning, reviewer, complaint_findings)
    operations.specialists['exception'] = bridge
    return bridge
