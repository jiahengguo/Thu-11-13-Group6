"""Shared domain review rechecks current confirmed facts, not claimed PASS flags."""
from tripmate.services.review import DeterministicReviewService
from .validation import PlanningValidator


def planning_reviewer(operations, offers, factors=None):
    def validate_plan(version, evidence, policies):
        if 'planning-1.0' not in policies:
            return ['The supported Planning review policy is required.']
        context = operations.load_context(version['caseId'])
        request, spec = context['request'], context['spec']
        quotes = offers.find_selectable(request, operations.clock())
        from .daily import policy_from, evaluate_daily
        from .factors import load_factors
        daily = None
        policy = policy_from(request, spec)
        if policy:
            facts = load_factors(factors, request, quotes, operations.clock(), 'FIXTURE')
            selected = {item['offerId'] for item in version['items']}
            daily = evaluate_daily(request, [q for q in quotes if q['offer']['offerId'] in selected], policy, facts, operations.clock)
        checks = PlanningValidator(request, quotes, spec, operations.clock, daily=daily).validate_plan(version)
        return [check['ruleId'] + ': ' + check['reason'] for check in checks if check['outcome'] != 'PASS']
    return DeterministicReviewService(lambda: operations.clock(), {'ItineraryVersion': validate_plan})
