"""Exception-specific checks registered with the project's shared ReviewService."""
from decimal import Decimal
from tripmate.services.review import DeterministicReviewService, timestamp


def review_exception(proposal, evidence, policies):
    reasons = []
    facts = {}
    for item in proposal['evidenceAssertions']:
        if item['sourceId'] not in {s['sourceId'] for s in evidence}:
            reasons.append('A structured assertion has no evidence source.')
        for assertion in item['assertions']:
            facts.setdefault(assertion['key'], set()).add(assertion['value'])
    if any(len(values) != 1 for values in facts.values()):
        reasons.append('Evidence assertions conflict.')
    if proposal['kind'] == 'RECOVERY':
        if not proposal['options']:
            reasons.append('No validated recovery option is available.')
        for option in proposal['options']:
            total = Decimal(proposal['sunkCost']) + sum((Decimal(i['remainingCost']) for i in option['items']), Decimal('0'))
            if total != Decimal(option['totalCost']) or not option['terms'].strip():
                reasons.append('Recovery cost or supplied supplier terms do not reconcile.')
            if 'planningRecord' in option:
                from tripmate.planning.validation import PlanningValidator
                record = option['planningRecord']
                checks = PlanningValidator(record['request'], record['quotes'], record['spec'],
                                            lambda: proposal['assessedAt']).validate_plan(record['version'])
                if any(c['outcome'] != 'PASS' for c in checks):
                    reasons.append('Project Planning validation did not pass on recheck.')
    elif proposal['kind'] == 'COMPLAINT':
        item = proposal['affectedItemIds'][0]
        scheduled = timestamp(next(iter(facts[item + ':scheduledArrival'])))
        actual = timestamp(next(iter(facts[item + ':actualArrival'])))
        if actual <= scheduled or int((actual - scheduled).total_seconds() / 60) != proposal['delayMinutes']:
            reasons.append('Delay does not reconcile to service evidence.')
        if len(policies) != 1 or proposal['policyIds'] != [policies[0]['policyId']]:
            reasons.append('An unambiguous supplied complaint policy is required.')
        else:
            policy = policies[0]
            for field in ('version', 'action'):
                if facts.get('policy:' + policy['policyId'] + ':' + field) != {policy[field]}:
                    reasons.append('The policy version/action is not supported by evidence.')
            if policy['action'] == 'HUMAN_REVIEW_REFUND' and not proposal['requiresApproval']:
                reasons.append('A restricted proposal must require human approval.')
            if policy['action'] not in {'EXPLAIN_AND_APOLOGISE', 'HUMAN_REVIEW_REFUND'}:
                reasons.append('No complaint policy evaluator is configured for this action.')
    else:
        reasons.append('Unsupported Exception proposal kind.')
    return reasons


def exception_reviewer(clock):
    return DeterministicReviewService(clock, {
        'RecoveryProposal': review_exception, 'ResolutionRecommendation': review_exception})
