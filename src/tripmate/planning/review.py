"""Shared domain review rechecks current confirmed facts, not claimed PASS flags."""
from tripmate.services.review import DeterministicReviewService
from .validation import PlanningValidator


def planning_reviewer(operations, offers):
    def validate_plan(version, evidence, policies):
        if 'planning-1.0' not in policies:
            return ['The supported Planning review policy is required.']
        context = operations.load_context(version['caseId'])
        request, spec = context['request'], context['spec']
        quotes = offers.find_selectable(request, operations.clock())
        # The default portal does not yet accept daily policies/factors. Unsupported
        # constraints fail the same deterministic validator instead of being waived.
        checks = PlanningValidator(request, quotes, spec, operations.clock).validate_plan(version)
        return [check['ruleId'] + ': ' + check['reason'] for check in checks if check['outcome'] != 'PASS']
    return DeterministicReviewService(lambda: operations.clock(), {'ItineraryVersion': validate_plan})
