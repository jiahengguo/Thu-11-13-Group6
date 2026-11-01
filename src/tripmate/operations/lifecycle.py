"""Explicit recovery waiting policy and evidenced simulated completion."""
from datetime import timedelta
from copy import deepcopy
from uuid import uuid4
from .common import OperationsError, instant, safe_text


def recovery_command(service, actor, key, case_id, revision, action, data):
    if not isinstance(data, dict):
        raise OperationsError('INVALID_CONTRACT', 'Lifecycle input must be an object.')
    def apply(rows):
        rec = service._owned(rows, actor, case_id, 'REVIEW_CASE', revision)
        if rec['case']['caseType'] != 'DISRUPTION' or rec['case']['status'] in {'CLOSED', 'WITHDRAWN'}:
            raise OperationsError('UNCONFIRMED_REQUEST', 'An open recovery case is required.')
        stage = rec.get('exceptionStage')
        now = instant(service.clock())
        if action == 'CONFIGURE_WAIT':
            if (set(data) != {'deadline', 'reminderMinutes', 'maxReminders'}
                    or type(data['reminderMinutes']) is not int or not 1 <= data['reminderMinutes'] <= 10080
                    or type(data['maxReminders']) is not int or not 0 <= data['maxReminders'] <= 10):
                raise OperationsError('INVALID_CONTRACT', 'Supply a deadline, reminder interval and limit.')
            try:
                if not isinstance(data['deadline'], str):
                    raise ValueError('Deadline must be an ISO timestamp')
                deadline = instant(data['deadline'])
            except (ValueError, TypeError, AttributeError) as exc:
                raise OperationsError('INVALID_CONTRACT', 'Use a timezone-aware ISO response deadline.') from exc
            if deadline <= now or stage != 'AWAITING_TRAVELLER_DECISION':
                raise OperationsError('UNCONFIRMED_REQUEST', 'Configure a future deadline while waiting for the traveller.')
            rec['recoveryWait'] = dict(data, policyId=str(uuid4()), runId=rec['exceptionRunId'], reminders=0,
                                      nextReminderAt=(now + timedelta(minutes=data['reminderMinutes'])).isoformat())
        elif action == 'CHECK_WAIT':
            wait = rec.get('recoveryWait')
            if data or stage != 'AWAITING_TRAVELLER_DECISION' or not wait or wait['runId'] != rec.get('exceptionRunId'):
                raise OperationsError('UNCONFIRMED_REQUEST', 'A current configured waiting period is required.')
            if now >= instant(wait['deadline']):
                rec['exceptionStage'] = 'NO_RESPONSE'
                rec['case']['status'] = 'HUMAN_ASSISTANCE'
                rec['case']['unresolvedQuestions'] = ['Configured response deadline elapsed; human follow-up required.']
            elif now >= instant(wait['nextReminderAt']) and wait['reminders'] < wait['maxReminders']:
                wait['reminders'] += 1
                wait['nextReminderAt'] = (now + timedelta(minutes=wait['reminderMinutes'])).isoformat()
                reminder = dict(caseId=case_id, requesterId=rec['case']['requesterId'],
                    runId=wait['runId'], at=service.clock(), message='Please review your recovery options.', simulationOnly=True)
                rows.put('recovery_reminder', wait['policyId'] + ':' + str(wait['reminders']), reminder)
                rec.setdefault('recoveryReminders', []).append(reminder)
            else:
                return {'caseId': case_id, 'changed': False}
        elif action == 'COMPLETE':
            if set(data) != {'runId', 'optionId', 'evidenceReference', 'reason', 'confirmed'} or data['confirmed'] is not True:
                raise OperationsError('INVALID_CONTRACT', 'Confirm completion with evidence for the selected recovery.')
            selection = rec.get('exceptionSelection') or {}
            if (stage != 'RECOMMENDATION_DELIVERED' or data['runId'] != rec.get('exceptionRunId')
                    or selection.get('runId') != data['runId'] or selection.get('optionId') != data['optionId']):
                raise OperationsError('STALE_EVIDENCE', 'Completion must match the current selected and delivered recovery.')
            # Completion records a manual simulated outcome, not a new booking or quote.
            service.specialists['exception'].ensure_release(rows, rec)
            inbox = rows.get('inbox', case_id + ':' + str(rec['responseVersion']))
            if not inbox or not rec.get('review') or rec['review']['outcome'] != 'PASS' or rec['review']['subject'] != service._response_subject(rec):
                raise OperationsError('REVIEW_FAILED', 'Complete only the currently reviewed and delivered recommendation.')
            if rec['case']['requiresApproval']:
                approval = rows.get('approval', rec.get('approvalId'))
                if (not approval or approval['status'] != 'DECIDED' or approval['decision'] != 'APPROVE'
                        or approval['subject'] != service._response_subject(rec) or approval['reviewId'] != rec['review']['reviewId']
                        or approval['scope'] != 'SIMULATED_EXTERNAL_RESPONSE'
                        or not service.access.authorise(approval['operatorId'], 'REVIEW_CASE', rec['case'])):
                    raise OperationsError('APPROVAL_REQUIRED', 'Current scoped response approval is required for completion.')
            evidence = safe_text(data['evidenceReference'], 1000)
            reason = safe_text(data['reason'], 1000)
            rec['recoveryCompletion'] = dict(runId=data['runId'], optionId=data['optionId'],
                subject=deepcopy(selection['subject']), responseVersion=rec['responseVersion'], reviewId=rec['review']['reviewId'],
                evidenceReference=evidence, reason=reason, actor=actor, at=service.clock(), simulationOnly=True)
            rec['exceptionStage'] = 'RESOLVED_SIMULATED'
            rec['case']['status'] = 'CLOSED'
            rec['case']['unresolvedQuestions'] = []
        else:
            raise OperationsError('INVALID_CONTRACT', 'Unknown recovery lifecycle action.')
        rec['revision'] += 1
        service._event(rows, rec, 'CASE_CLOSED' if action == 'COMPLETE' else 'CONFIRMATION',
                       'Recovery lifecycle: ' + action + '; simulated local processing.', actor=actor)
        service._save(rows, rec)
        return {'caseId': case_id, 'changed': True}
    service._command(actor, 'recovery-lifecycle', key, [case_id, revision, action, data], apply)
    return service.case_view(actor, case_id)


def record_planning_state(service, rows, rec):
    """Durable assessment aggregate; immutable itinerary versions stay unchanged."""
    if rec['case']['caseType'] not in {'TRAVEL_PLANNING', 'PLAN_REVISION'}:
        return
    mapping = {'CONFIRMED': 'DRAFT', 'ASSIGNED': 'DRAFT', 'IN_PROGRESS': 'VALIDATING',
               'UNDER_REVIEW': 'UNDER_REVIEW', 'READY_TO_RESPOND': 'REVIEWED',
               'AWAITING_HUMAN_APPROVAL': 'AWAITING_HUMAN_REVIEW',
               'AWAITING_REQUESTER': 'REVISION_REQUIRED', 'HUMAN_ASSISTANCE': 'AWAITING_HUMAN_REVIEW',
               'AWAITING_VERIFICATION': 'AWAITING_HUMAN_REVIEW', 'AWAITING_PLAN_ACCESS_DECISION': 'AWAITING_HUMAN_REVIEW',
               'CLOSED': 'HANDED_OFF', 'WITHDRAWN': 'REJECTED'}
    state = rec.get('planningDecisionState') or mapping.get(rec['case']['status'])
    if rec['case']['status'] == 'WITHDRAWN':
        state = 'REJECTED'
    result = rec.get('specialistResult') or {}
    if rec['case']['status'] == 'CLOSED' and (not rows.get('inbox', rec['id'] + ':' + str(rec['responseVersion']))
            or result.get('status') != 'SUCCESS' or not result.get('subjects')):
        state = 'REJECTED'
    errors = rec['case'].get('errors', [])
    if errors and not rec.get('planningDecisionState') and rec['case']['status'] not in {'CLOSED', 'WITHDRAWN'}:
        state = 'INFEASIBLE' if any(e['code'] == 'NO_FEASIBLE_ITINERARY' for e in errors) else 'REVISION_REQUIRED'
    if state is None:
        return
    refs = [r for r in (rec.get('specialistResult') or {}).get('subjects', []) if r['subjectType'] == 'ItineraryVersion']
    previous = rows.get('planning_assessment', rec['id'])
    value = dict(caseId=rec['id'], state=state, subjects=refs, responseVersion=rec['responseVersion'],
                 caseRevision=rec['revision'], updatedAt=service.clock(),
                 priorRunIds=deepcopy(rec.get('planningPriorRuns', [])))
    if not previous or any(previous.get(k) != value[k] for k in ('state', 'subjects', 'responseVersion')):
        rows.put('planning_assessment_event', str(uuid4()),
                 dict(value, previousState=previous['state'] if previous else None))
    rows.put('planning_assessment', rec['id'], value)


def planning_command(service, actor, key, case_id, revision, action, reason):
    """Operator recovery never grants proposal approval or changes confirmed inputs."""
    reason = safe_text(reason, 1000)
    if action not in {'RETRY', 'REOPEN'}:
        raise OperationsError('INVALID_CONTRACT', 'Choose retry or request reconfirmation.')
    def apply(rows):
        rec = service._owned(rows, actor, case_id, 'REVIEW_CASE', revision)
        if rec['case']['caseType'] not in {'TRAVEL_PLANNING', 'PLAN_REVISION'} or rec['case']['status'] not in {'HUMAN_ASSISTANCE', 'AWAITING_REQUESTER'}:
            raise OperationsError('UNCONFIRMED_REQUEST', 'Only an incomplete Planning assessment can be resumed.')
        errors = rec['case']['errors'] or (rec.get('specialistResult') or {}).get('errors', [])
        if action == 'RETRY' and (rec.get('planningDecisionState') in {'REJECTED', 'REVISION_REQUIRED'} or not errors
                or any(e['code'] not in {'TOOL_UNAVAILABLE', 'PERSISTENCE_FAILED', 'LLM_TIMEOUT'} for e in errors)):
            raise OperationsError('UNCONFIRMED_REQUEST', 'Only a technical failure may retry unchanged input; request reconfirmation otherwise.')
        old = rec.get('specialistResult') or {}
        if old.get('runId'):
            rec.setdefault('planningPriorRuns', []).append(old['runId'])
        rec.pop('specialistResult', None)
        rec.pop('planningDecisionState', None)
        rec.update(response=None, responseVersion=rec['responseVersion']+1, review=None, approvalId=None,
                   dispatchStarted=False, completedRun=None, invokedRun=None)
        rec['case'].update(status='CONFIRMED' if action == 'RETRY' else 'AWAITING_REQUESTER',
                           errors=[], validationResults=[], unresolvedQuestions=[] if action == 'RETRY' else [reason])
        rec['revision'] += 1
        service._event(rows, rec, 'CONFIRMATION', 'Planning ' + action + ': ' + reason, actor=actor)
        service._save(rows, rec)
        return {'caseId': case_id}
    service._command(actor, 'planning-lifecycle', key, [case_id, revision, action, reason], apply)
    return service.case_view(actor, case_id)
