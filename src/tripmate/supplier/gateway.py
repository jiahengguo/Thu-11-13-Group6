"""Authenticated portal integration; shared private storage, explicit human gates."""
import hashlib
import json
import os
from copy import deepcopy

from tripmate.contracts import validate
from tripmate.operations.common import OperationsError, safe_text
from .application import SupplierRuntime
from .common import PricingPolicy, SOURCE_FIELDS, SupplierError, subject, uid
from .shared_repository import SharedSupplierRepository, SharedApprovals


class UnavailablePricing:
    def calculate(self, offer, discount):
        raise SupplierError('TOOL_UNAVAILABLE', 'Configure Supplier pricing policy and merge the shared B04 pricing module')


class SupplierAccess:
    def __init__(self, operations, repository):
        self.operations, self.repository = operations, repository

    def authorise(self, identity, action, target):
        profile = self.operations.profile(identity)
        if not profile or not profile.get('verified'):
            return False
        if action == 'ASSESS_SUPPLIER_OFFER':
            rec = self.operations.repository.read('case', target['caseId'])
            return bool(rec and profile['role'] == 'SUPPLIER' and rec['case']['requesterId'] == identity
                        and rec['case']['status'] == 'IN_PROGRESS')
        if action not in {'REVIEW_SUPPLIER_OFFER', 'APPROVE_SUPPLIER_TERMS'} or profile['role'] != 'OPERATOR':
            return False
        current = self.repository.current(target['subjectId'])
        rec = self.operations.repository.read('case', current['caseId']) if current else None
        return bool(rec and current['offer'] and subject(current['offer']) == target
                    and rec['case']['status'] != 'WITHDRAWN'
                    and (rec['case']['status'] != 'CLOSED' or current['offer']['status'] == 'APPROVED'))


class SupplierGateway:
    def __init__(self, operations, pricing=None, policy=None):
        self.operations = operations
        self.repository = SharedSupplierRepository(operations.repository)
        self.approvals = SharedApprovals(operations.repository)
        self.access = SupplierAccess(operations, self.repository)
        if policy is None:
            values = [os.environ.get(key) for key in ('TRIPMATE_MARKUP_RATE', 'TRIPMATE_MINIMUM_MARGIN',
                                                    'TRIPMATE_PRICING_CONFIG_VERSION')]
            policy = PricingPolicy(*values) if all(values) else PricingPolicy('0', '0.00', 'unconfigured')
        self.policy = policy
        if pricing is None and policy.version != 'unconfigured':
            try:
                from tripmate.planning.pricing import DeterministicPricingService
                pricing = DeterministicPricingService(policy.markup_rate, {'amount': policy.minimum_margin, 'currency': 'AUD'},
                                                       policy.version, operations.clock)
            except ImportError:
                pass
        self.pricing = pricing or UnavailablePricing()
        self.runtime = SupplierRuntime(self.load_input, self.repository, self.pricing, policy,
                                      None, operations.repository, self.approvals, self.access,
                                      llm=operations.llm, clock=operations.clock, execution_mode='FIXTURE')
        operations.specialists['supplier'] = self

    def load_input(self, case_id):
        rec = self.operations.repository.read('case', case_id)
        if not rec or rec['case']['status'] != 'IN_PROGRESS' or rec['case']['caseKind'] != 'SUPPLIER':
            raise SupplierError('UNCONFIRMED_REQUEST', 'Use the current confirmed Operations supplier case')
        submission = rec['fields'].get('supplierOffer')
        if not submission:
            raise SupplierError('MISSING_REQUIRED_FIELDS', 'Submit structured quotation fields; general cooperation requests require human handling')
        owner = rec['case']['requesterId']
        offer_id = 'offer-' + hashlib.sha256((owner + '\0' + submission['offerReference']).encode()).hexdigest()[:32]
        candidate = {key: deepcopy(submission[key]) for key in SOURCE_FIELDS if key in submission}
        candidate['supplierId'] = owner
        signature = hashlib.sha256(json.dumps(submission, sort_keys=True).encode()).hexdigest()[:16]
        evidence = dict(sourceId='supplier-source-' + case_id + '-' + signature, sourceType='SUPPLIER',
                        sourceReference=submission['sourceReference'], capturedAt=rec['case']['confirmedAt'],
                        freshness='FRESH', simulated=True)
        context = dict(offerId=offer_id, candidate=candidate,
                       sourceReferences=[deepcopy(ref) for ref in rec['sources']
                                         if not ref['sourceId'].startswith('supplier-source-')] + [evidence])
        if submission.get('product'):
            context['product'] = dict(deepcopy(submission['product']), productId=submission['productId'],
                                      sourceIds=[evidence['sourceId']])
        # Model extraction is optional. Structured source facts remain authoritative.
        if (not isinstance(self.pricing, UnavailablePricing) and self.operations.llm is not None
                and all(key in candidate for key in SOURCE_FIELDS)):
            context.pop('candidate')
            context.update(sourceText=json.dumps(candidate), verifiedFacts=deepcopy(candidate))
        return context

    def handle_case(self, case):
        result = self.runtime.handle_case(case)
        correction_codes = {'MISSING_REQUIRED_FIELDS', 'OFFER_INVALID', 'OFFER_EXPIRED',
                            'MARGIN_FAILED', 'VERIFICATION_FAILED', 'STALE_EVIDENCE'}
        if result['status'] == 'FAILURE' and result['errors'][0]['code'] in correction_codes:
            result['status'] = 'REVISION_REQUIRED'
            result['nextAction'] = 'Correct and explicitly confirm the complete supplier quotation before reassessment.'
        return result

    def invalidate_confirmation(self, rows, case_record):
        # Runs in the coordinator's existing transaction: confirmed changes and
        # withdrawal of old offer authority either both save or both roll back.
        for pointer in rows.all('supplier_current'):
            if pointer['caseId'] == case_record['id']:
                rows.put('supplier_current', pointer['offerId'], dict(pointer, invalidated=True))

    def find_selectable(self, criteria, at):
        quotes = self.runtime.find_selectable(criteria, at)
        return [quote for quote in quotes
                if (self.operations.repository.read('case', quote['offer']['caseId']) or {}).get('case', {}).get('status') != 'WITHDRAWN']

    def _case(self, actor, case_id):
        profile = self.operations.profile(actor)
        rec = self.operations.repository.read('case', case_id)
        if (not profile or not profile.get('verified') or not rec or rec['case']['caseKind'] != 'SUPPLIER'
                or profile['role'] not in {'SUPPLIER', 'OPERATOR'}
                or (profile['role'] != 'OPERATOR' and rec['case']['requesterId'] != actor)):
            raise OperationsError('ACCESS_DENIED', 'This supplier assessment is not available to this account')
        return profile, rec

    def _record_for_case(self, rec):
        refs = (rec.get('specialistResult') or {}).get('subjects', [])
        for ref in refs:
            if ref['subjectType'] == 'SupplierOffer':
                record = self.repository.current(ref['subjectId'])
                if record and record['caseId'] == rec['id']:
                    return record
        # Failed assessments may have no valid SupplierOffer subject.
        return next((row for row in self.repository.records() if row['caseId'] == rec['id']), None)

    def view(self, actor, case_id):
        profile, rec = self._case(actor, case_id)
        record = self._record_for_case(rec)
        data = dict(pricingReady=not isinstance(self.pricing, UnavailablePricing),
                    status='NOT_ASSESSED', offer=None, price=None, issues=[])
        if not record:
            return data
        if record.get('invalidated'):
            return data
        offer = record['offer']
        data['issues'] = (record.get('result') or {}).get('errors', [])
        if offer:
            fields = ('offerId', 'materialVersion', 'productId', 'productType', 'availableQuantity',
                      'quotedQuantity', 'unitBasis', 'validFrom', 'validUntil', 'cancellationTerms', 'status', 'requiresApproval')
            data.update(status=offer['status'], offer={key: offer[key] for key in fields})
            if profile['role'] == 'OPERATOR':
                data['offer'] = deepcopy(offer)
                data['price'] = deepcopy(record['price'])
                data['pendingApprovals'] = self.approvals.find_by_subject(subject(offer))
        else:
            data['status'] = 'REVISION_REQUIRED'
        return data

    def mutate(self, actor, action, body):
        required = {'caseId', 'materialVersion', 'revision', 'requestKey', 'reason', 'decision'}
        if action not in {'review', 'decision'} or set(body) != required:
            raise OperationsError('INVALID_CONTRACT', 'Use a version-scoped supplier review or decision')
        reason = safe_text(body['reason'], 1000)
        choices = {'PASS', 'REVISION_REQUIRED'} if action == 'review' else {'APPROVE', 'REQUEST_REVISION', 'REJECT'}
        if body['decision'] not in choices or type(body['revision']) is not int:
            raise OperationsError('INVALID_CONTRACT', 'Supply a valid decision and case revision')
        if not isinstance(body['requestKey'], str) or not 1 <= len(body['requestKey']) <= 100:
            raise OperationsError('INVALID_CONTRACT', 'Provide a stable action key')
        profile, rec = self._case(actor, body['caseId'])
        if profile['role'] != 'OPERATOR':
            raise OperationsError('ACCESS_DENIED', 'Only an authorised operator can review supplier offers')
        record = self._record_for_case(rec)
        if not record or not record['offer'] or type(body['materialVersion']) is not int:
            raise OperationsError('UNCONFIRMED_REQUEST', 'Reload the assessed offer')
        offer = record['offer']
        key = actor + '/' + body['requestKey']
        fingerprint = hashlib.sha256(json.dumps([action, body], sort_keys=True).encode()).hexdigest()
        journal = self.operations.repository.read('supplier_action', key)
        if journal:
            if journal['fingerprint'] != fingerprint:
                raise OperationsError('UNCONFIRMED_REQUEST', 'This action key was used for another decision')
            if journal['status'] == 'DONE':
                return self.view(actor, rec['id'])
        else:
            if (body['revision'] != rec['revision'] or body['materialVersion'] != offer['materialVersion']
                    or rec['case']['status'] in {'CLOSED', 'WITHDRAWN'}):
                raise OperationsError('UNCONFIRMED_REQUEST', 'Reload the current case and offer version')
            journal = dict(fingerprint=fingerprint, status='STARTED', reviewedAt=self.operations.clock(),
                           reviewId='review-' + hashlib.sha256(key.encode()).hexdigest(), offerId=offer['offerId'],
                           materialVersion=offer['materialVersion'])
            with self.operations.repository.transaction() as rows:
                if rows.get('supplier_action', key):
                    raise OperationsError('UNCONFIRMED_REQUEST', 'This action is already running; retry with its original key')
                rows.put('supplier_action', key, journal)
        if offer['materialVersion'] != journal['materialVersion'] or offer['offerId'] != journal['offerId']:
            raise OperationsError('UNCONFIRMED_REQUEST', 'A source revision invalidated this decision')
        try:
            if action == 'review':
                if body['decision'] not in {'PASS', 'REVISION_REQUIRED'}:
                    raise SupplierError('REVIEW_FAILED', 'Choose Pass or Request revision')
                if not offer['review'] or offer['review']['reviewId'] != journal['reviewId']:
                    review = dict(reviewId=journal['reviewId'], subject=subject(offer), outcome=body['decision'],
                                  reasons=[reason], reviewedAt=journal['reviewedAt'], policyVersion='portal-operator-review-1',
                                  sourceIds=[ref['sourceId'] for ref in offer['sourceReferences']])
                    self.runtime.apply_review(offer['offerId'], offer['materialVersion'], review, actor)
            else:
                if body['decision'] not in {'APPROVE', 'REQUEST_REVISION', 'REJECT'}:
                    raise SupplierError('APPROVAL_REJECTED', 'Choose an explicit human decision')
                if offer['status'] == 'AWAITING_APPROVAL':
                    pending = next(item for item in self.approvals.find_by_subject(subject(offer))
                                   if item['approvalId'] == offer['approvalId'] and item['status'] == 'PENDING')
                    approval = dict(pending, status='DECIDED', decision=body['decision'], operatorId=actor,
                                    reason=reason, decidedAt=journal['reviewedAt'])
                    self.approvals.save(approval)
                    self.runtime.apply_decision(approval)
                else:
                    saved = self.approvals.find_by_subject(subject(offer))
                    if not any(a['approvalId'] == offer['approvalId'] and a['status'] == 'DECIDED'
                               and a['operatorId'] == actor and a['decision'] == body['decision']
                               and a['decidedAt'] == journal['reviewedAt'] for a in saved):
                        raise SupplierError('APPROVAL_REJECTED', 'Offer is not awaiting this scoped decision')
            current = self.repository.current(offer['offerId'])
            result = current['result']
            validate('AgentResult', result)
            with self.operations.repository.transaction() as rows:
                stored = rows.get('supplier_action', key)
                if stored['status'] != 'DONE':
                    case_rec = rows.get('case', rec['id'])
                    if case_rec['case']['status'] in {'CLOSED', 'WITHDRAWN'} or current['caseId'] != rec['id']:
                        raise OperationsError('UNCONFIRMED_REQUEST', 'The case is no longer active')
                    self.operations._receive(rows, case_rec, result)
                    case_rec['revision'] += 1
                    self.operations._event(rows, case_rec, 'TOOL_RESULT', 'Scoped Supplier offer decision recorded; external response remains controlled.')
                    self.operations._save(rows, case_rec)
                    rows.put('supplier_action', key, dict(stored, status='DONE'))
        except (SupplierError, ValueError, KeyError, StopIteration) as exc:
            raise OperationsError(getattr(exc, 'code', 'INVALID_CONTRACT'), str(exc)) from None
        return self.view(actor, rec['id'])
