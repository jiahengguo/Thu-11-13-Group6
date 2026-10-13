"""UC-06 control: injected B04/B05/B07/B10 ports; no fake production approval."""
import sqlite3
from copy import deepcopy

from tripmate.contracts import ContractError, validate
from .common import (PricingPolicy, SupplierError, SOURCE_FIELDS, check, envelope,
                     extraction_schema, now, subject, timestamp, uid,
                     validate_offer, validate_source, verify_price)


class SupplierRuntime:
    def __init__(self, load_input, repository, pricing, policy: PricingPolicy,
                 reviewer, traces, approvals, access, llm=None, clock=now,
                 execution_mode='FIXTURE', ordinary_terms=()):
        if execution_mode not in {'FIXTURE', 'REAL'}:
            raise ValueError('Supplier runtime must declare FIXTURE or REAL')
        self.load_input, self.repository = load_input, repository
        self.pricing, self.policy, self.reviewer = pricing, policy, reviewer
        self.traces, self.approvals, self.access = traces, approvals, access
        self.llm, self.clock, self.mode = llm, clock, execution_mode
        self.ordinary_terms = frozenset(ordinary_terms)

    def _result(self, source, run, status='SUCCESS', offer=None, error=None):
        result = envelope(source)
        result.update(runId=run, agent='supplier', status=status, executionMode=self.mode,
                      findings=[], proposedResponse=None, subjects=[subject(offer)] if offer else [],
                      review=deepcopy(offer['review']) if offer else None,
                      approvalIds=[offer['approvalId']] if offer and offer['approvalId'] else [],
                      nextAction='Return the internal assessment to Operations; no supplier commitment executed.')
        if offer:
            result['validationResults'] = deepcopy(offer['validationResults'])
            result['requiresApproval'] = offer['requiresApproval']
        if error:
            result['errors'] = [dict(code=error.code, message=str(error), step='supplier',
                                     retryable=error.code in {'TOOL_UNAVAILABLE', 'PERSISTENCE_FAILED', 'LLM_TIMEOUT'},
                                     sourceIds=[ref['sourceId'] for ref in source['sourceReferences']])]
            result['nextAction'] = 'Correct the source or resolve the recorded dependency; reassess through Operations.'
        validate('AgentResult', result)
        return result

    def _trace(self, source, run, ref, event_type, result, summary, approval_id=None):
        event = envelope(source)
        event.update(eventId=uid('event'), runId=run, timestamp=self.clock(), actor='supplier',
                     eventType=event_type, subject=ref, parentEventId=None,
                     executionMode=self.mode, summary=summary, result=result, approvalId=approval_id)
        event['requiresApproval'] = source.get('requiresApproval', False)
        validate('TraceEvent', event)
        try:
            self.traces.append(event)
        except Exception:
            raise SupplierError('PERSISTENCE_FAILED', 'Shared trace append failed') from None

    def _check_review(self, offer, at, calculated_at):
        validate('SupplierOffer', offer)  # Includes ReviewResult schema.
        review = offer['review']
        ids = {ref['sourceId'] for ref in offer['sourceReferences']}
        if (not review or review['subject'] != subject(offer) or review['outcome'] != 'PASS'
                or set(review['sourceIds']) != ids
                or not timestamp(calculated_at)
                <= timestamp(review['reviewedAt']) <= timestamp(at)):
            raise SupplierError('REVIEW_FAILED', 'Review must pass for this source and material version')

    def handle_case(self, case):
        validate('Case', case)
        run, offer, version, offer_id = uid('supplier-run'), None, None, None
        source = case
        try:
            if (case['caseKind'] != 'SUPPLIER' or case['requesterType'] != 'SUPPLIER'
                    or case['caseType'] not in {'INVENTORY', 'OFFER', 'PRICE_NEGOTIATION', 'SUPPLIER_COOPERATION'}
                    or case['status'] not in {'CONFIRMED', 'ASSIGNED', 'IN_PROGRESS'}
                    or case['unresolvedQuestions'] or case['errors']
                    or case['primaryHandler'] not in {None, 'supplier'}):
                raise SupplierError('UNCONFIRMED_REQUEST', 'A confirmed, assigned supplier source is required')
            if any(port is None for port in (self.pricing, self.reviewer, self.traces, self.approvals, self.access)):
                raise SupplierError('TOOL_UNAVAILABLE', 'Configure shared pricing, review, trace, approval and access ports')
            context = deepcopy(self.load_input(case['caseId']))
            offer_id = context.get('offerId')
            if not isinstance(offer_id, str) or not offer_id.strip():
                raise SupplierError('MISSING_REQUIRED_FIELDS', 'Operations must supply a stable offer ID')
            if not self.access.authorise(case['requesterId'], 'ASSESS_SUPPLIER_OFFER',
                                         {'caseId': case['caseId'], 'offerId': offer_id}):
                raise SupplierError('ACCESS_DENIED', 'Supplier source ownership is not verified')
            existing = self.repository.current(offer_id)
            if existing and existing['offer'] and existing['offer']['supplierId'] != case['requesterId']:
                raise SupplierError('ACCESS_DENIED', 'An offer cannot be reassigned to a different supplier')
            version = self.repository.reserve(offer_id, case['caseId'], self.mode, case['requesterId'])
            self._trace(case, run, dict(subjectType='SupplierOffer', subjectId=offer_id, materialVersion=version),
                        'VERSION_CREATED', 'PENDING',
                        'New source version reserved; earlier approval is no longer selectable.')
            refs = context.get('sourceReferences')
            if not isinstance(refs, list) or not refs:
                raise SupplierError('MISSING_REQUIRED_FIELDS', 'Supplier evidence references are required')
            source = envelope(case)
            source['sourceReferences'] = deepcopy(refs)
            if 'sourceText' in context:
                if self.llm is None:
                    raise SupplierError('TOOL_UNAVAILABLE', 'Configure the shared extraction adapter')
                locked = context.get('verifiedFacts', {})
                if any(field not in locked for field in ('supplierCost', 'quotedQuantity', 'unitBasis')):
                    raise SupplierError('VERIFICATION_FAILED', 'Confirm source cost and quantity basis before extraction')
                try:
                    candidate = self.llm.extract(context['sourceText'], extraction_schema())
                except Exception as exc:
                    code = getattr(exc, 'code', 'LLM_INVALID_OUTPUT')
                    if code not in {'LLM_TIMEOUT', 'LLM_INVALID_OUTPUT', 'TOOL_UNAVAILABLE'}:
                        code = 'LLM_INVALID_OUTPUT'
                    raise SupplierError(code, 'Supplier extraction failed; source remains unapproved') from None
                if not isinstance(candidate, dict) or any(candidate.get(key) != value for key, value in locked.items()):
                    raise SupplierError('VERIFICATION_FAILED', 'Extracted fields differ from independently verified source facts')
            else:
                candidate = context.get('candidate')
            validate_source(candidate)
            if candidate['supplierId'] != case['requesterId']:
                raise SupplierError('ACCESS_DENIED', 'Source supplier differs from confirmed requester')
            offer = envelope(source)
            offer.update(deepcopy(candidate), offerId=offer_id, materialVersion=version,
                         status='DRAFT', priceBreakdownId=None, review=None, approvalId=None)
            at = self.clock()
            validate_offer(offer, at)
            if self.mode == 'REAL' and any(ref['simulated'] for ref in offer['sourceReferences']):
                raise SupplierError('VERIFICATION_FAILED', 'Simulated source cannot establish a real approved offer')
            ids = [ref['sourceId'] for ref in refs]
            offer['validationResults'] = [check('SUPPLIER_SOURCE', at, ids)]
            # The service receives a copy: it cannot silently rewrite source cost.
            price = self.pricing.calculate(deepcopy(offer), None)
            verify_price(offer, price, self.policy)
            if not timestamp(at) <= timestamp(price['calculatedAt']) <= timestamp(self.clock()):
                raise SupplierError('MARGIN_FAILED', 'Pricing timestamp is outside this assessment')
            offer['priceBreakdownId'] = price['priceBreakdownId']
            offer['validationResults'].append(check('PRICE_MARGIN', at, ids))
            offer['requiresApproval'] = (case['requiresApproval']
                                        or any(term not in self.ordinary_terms for term in offer['commercialTerms']))
            offer['status'] = 'UNDER_REVIEW'
            offer['review'] = self.reviewer.review(deepcopy(offer), deepcopy(refs),
                                                   [{'policyVersion': self.policy.version,
                                                     'requiresApproval': offer['requiresApproval']}])
            at = self.clock()
            validate_offer(offer, at)
            self._check_review(offer, at, price['calculatedAt'])
            if offer['requiresApproval']:
                approval = envelope(offer)
                approval.update(requiresApproval=True, approvalId=uid('approval'), subject=subject(offer),
                                scope='restricted_supplier_terms', status='PENDING', decision=None,
                                requestedAt=at, decidedAt=None, operatorId=None, reason=None,
                                reviewId=offer['review']['reviewId'])
                validate('Approval', approval)
                try:
                    self.approvals.save(deepcopy(approval))
                except Exception:
                    raise SupplierError('PERSISTENCE_FAILED', 'Shared approval request save failed') from None
                offer.update(status='AWAITING_APPROVAL', approvalId=approval['approvalId'])
                status = 'APPROVAL_PENDING'
            else:
                offer['status'], status = 'APPROVED', 'SUCCESS'
            validate('SupplierOffer', offer)
            product = deepcopy(context.get('product'))
            if product is not None and (not isinstance(product, dict)
                    or product.get('productId') != offer['productId']
                    or not product.get('sourceIds') or not set(product['sourceIds']).issubset(ids)):
                raise SupplierError('VERIFICATION_FAILED', 'Product metadata must match this sourced offer')
            result = self._result(offer, run, status, offer)
            self._trace(offer, run, subject(offer), 'APPROVAL_REQUESTED' if offer['requiresApproval'] else 'VALIDATION',
                        'PENDING' if offer['requiresApproval'] else 'SUCCESS',
                        'Assessment passed; final Supplier snapshot persistence follows.', offer['approvalId'])
            self.repository.save(offer_id, version, dict(offer=offer, price=price, result=result,
                                                        product=product, supplierId=case['requesterId'],
                                                        caseId=case['caseId'], executionMode=self.mode))
            return result
        except Exception as exc:
            if isinstance(exc, SupplierError):
                error = exc
            elif isinstance(exc, (OSError, sqlite3.Error)):
                error = SupplierError('PERSISTENCE_FAILED', 'Supplier evidence or snapshot could not be saved')
            elif getattr(exc, 'code', None) in {'MARGIN_FAILED', 'OFFER_INVALID', 'TOOL_UNAVAILABLE', 'LLM_TIMEOUT'}:
                error = SupplierError(exc.code, 'Shared supplier dependency rejected this assessment')
            elif not isinstance(exc, (ContractError, ValueError, KeyError, TypeError)):
                error = SupplierError('TOOL_UNAVAILABLE', 'Shared supplier dependency failed')
            else:
                error = SupplierError('INVALID_CONTRACT', 'Supplier dependency returned invalid data')
            # Use the known-good Case envelope even if extracted sources were malformed.
            result = self._result(case, run, 'FAILURE', error=error)
            if version is not None:
                if offer:
                    offer['status'] = 'EXPIRED' if error.code == 'OFFER_EXPIRED' else 'REVISION_REQUIRED'
                    offer['approvalId'] = None
                try:
                    self._trace(case, run, dict(subjectType='SupplierOffer', subjectId=offer_id, materialVersion=version),
                                'FAILURE', 'FAILURE', str(error))
                    self.repository.save(offer_id, version, dict(offer=offer, price=None, result=result,
                                                                supplierId=case['requesterId'],
                                                                caseId=case['caseId'], executionMode=self.mode))
                except (OSError, sqlite3.Error, SupplierError):
                    result = self._result(case, run, 'FAILURE',
                                          error=SupplierError('PERSISTENCE_FAILED', 'Failed to persist the rejected assessment'))
            return result

    def apply_decision(self, approval):
        """Consume an already persisted B10 decision; the caller cannot invent one."""
        validate('Approval', approval)
        offer_id = approval['subject']['subjectId']
        record = self.repository.current(offer_id)
        if not record or not record['offer'] or record['executionMode'] != self.mode:
            raise SupplierError('APPROVAL_REJECTED', 'No current offer awaiting approval')
        offer, price = deepcopy(record['offer']), record['price']
        at = self.clock()
        stored = self.approvals.find_by_subject(subject(offer))
        decisions = [item for item in stored if item.get('approvalId') == offer['approvalId'] and item.get('status') == 'DECIDED']
        if (offer['status'] != 'AWAITING_APPROVAL' or approval['subject'] != subject(offer)
                or approval['approvalId'] != offer['approvalId'] or decisions != [approval]
                or approval['status'] != 'DECIDED' or approval['scope'] != 'restricted_supplier_terms'
                or approval['reviewId'] != offer['review']['reviewId']
                or approval['caseId'] != offer['caseId'] or approval['correlationId'] != offer['correlationId']
                or approval['sourceReferences'] != offer['sourceReferences']
                or not timestamp(offer['review']['reviewedAt']) <= timestamp(approval['requestedAt'])
                <= timestamp(approval['decidedAt']) <= timestamp(at)
                or not self.access.authorise(approval['operatorId'], 'APPROVE_SUPPLIER_TERMS', subject(offer))):
            raise SupplierError('APPROVAL_REJECTED', 'Decision must be persisted, authorised and scoped to the current reviewed version')
        validate_offer(offer, at)
        verify_price(offer, price, self.policy)
        self._check_review(offer, at, price['calculatedAt'])
        decision = approval['decision']
        offer['status'] = {'APPROVE': 'APPROVED', 'REQUEST_REVISION': 'REVISION_REQUIRED', 'REJECT': 'REJECTED'}[decision]
        status = 'SUCCESS' if decision == 'APPROVE' else 'REVISION_REQUIRED' if decision == 'REQUEST_REVISION' else 'FAILURE'
        error = SupplierError('APPROVAL_REJECTED', 'Human rejected these supplier terms') if decision == 'REJECT' else None
        result = self._result(offer, uid('supplier-run'), status, offer, error)
        validate('SupplierOffer', offer)
        self._trace(offer, result['runId'], subject(offer), 'APPROVAL_DECIDED',
                    'SUCCESS' if decision == 'APPROVE' else 'FAILURE',
                    'Version-scoped human decision checked; final Supplier persistence follows.', approval['approvalId'])
        self.repository.save(offer_id, offer['materialVersion'], dict(record, offer=offer, result=result))
        return result

    def find_selectable(self, criteria, at):
        """Shared ApprovedOfferLookup: latest versions only, with expiry rechecked."""
        allowed = {'offerId', 'supplierId', 'productId', 'productType'}
        planning_request = isinstance(criteria, dict) and 'requestId' in criteria
        if planning_request:
            validate('TravelRequest', criteria)
            filters = {}
        elif not isinstance(criteria, dict) or set(criteria) - allowed:
            raise SupplierError('UNSUPPORTED_CONSTRAINT', 'Offer lookup supports identity/product-type filters only')
        else:
            filters = criteria
        timestamp(at)
        selected = []
        for record in self.repository.records():
            offer, price = record['offer'], record['price']
            if not offer or offer['status'] != 'APPROVED' or not price or record['executionMode'] != self.mode:
                continue
            if any(offer[key] != value for key, value in filters.items()):
                continue
            if planning_request and not record.get('product'):
                continue
            try:
                validate_offer(offer, at)
                verify_price(offer, price, self.policy)
                self._check_review(offer, at, price['calculatedAt'])
                review = offer['review']
                if offer['requiresApproval']:
                    decisions = self.approvals.find_by_subject(subject(offer))
                    decisions = [item for item in decisions if item.get('approvalId') == offer['approvalId']
                                 and item.get('status') == 'DECIDED']
                    if len(decisions) != 1:
                        continue
                    approved = False
                    for decision in decisions:
                        validate('Approval', decision)
                        if (decision['approvalId'] == offer['approvalId'] and decision['subject'] == subject(offer)
                                and decision['status'] == 'DECIDED' and decision['decision'] == 'APPROVE'
                                and decision['scope'] == 'restricted_supplier_terms'
                                and decision['reviewId'] == review['reviewId']
                                and decision['caseId'] == offer['caseId']
                                and decision['correlationId'] == offer['correlationId']
                                and decision['sourceReferences'] == offer['sourceReferences']
                                and timestamp(review['reviewedAt']) <= timestamp(decision['requestedAt'])
                                <= timestamp(decision['decidedAt']) <= timestamp(at)
                                and self.access.authorise(decision['operatorId'], 'APPROVE_SUPPLIER_TERMS', subject(offer))):
                            approved = True
                    if not approved:
                        continue
                quote = {'offer': deepcopy(offer), 'price': deepcopy(price)}
                if record.get('product'):
                    quote['product'] = deepcopy(record['product'])
                selected.append(quote)
            except (SupplierError, ContractError, ValueError, KeyError, TypeError):
                continue
        return selected
