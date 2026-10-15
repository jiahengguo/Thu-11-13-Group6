"""Shared ReviewService: deterministic gates and explicitly registered domain checks.

There is no default passing reviewer. Owners register their proposal validator;
unknown subjects/policies fail for revision instead of acquiring invented rules.
"""
from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

from tripmate.contracts import schema_bundle
from jsonschema import Draft202012Validator, FormatChecker


def timestamp(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Timezone required')
    return result


class DeterministicReviewService:
    def __init__(self, clock, validators):
        self.clock, self.validators = clock, dict(validators)

    def review(self, proposal, evidence, policies):
        reasons = []
        ref = deepcopy(proposal.get('subject'))
        if ref is None:
            for key, kind, version in [('versionId', 'ItineraryVersion', 'versionNo'),
                                       ('offerId', 'SupplierOffer', 'materialVersion'),
                                       ('campaignId', 'CampaignProposal', 'materialVersion')]:
                if key in proposal:
                    ref = dict(subjectType=kind, subjectId=proposal[key], materialVersion=proposal[version])
                    break
        schema = schema_bundle()
        schema['$ref'] = '#/$defs/SubjectRef'
        if not Draft202012Validator(schema).is_valid(ref):
            raise ValueError('A valid exact proposal/version reference is required')
        try:
            at = timestamp(self.clock())
            ids = [s['sourceId'] for s in evidence]
            source_schema = schema_bundle()
            source_schema['$ref'] = '#/$defs/SourceReference'
            validator = Draft202012Validator(source_schema, format_checker=FormatChecker())
            if (not ids or len(ids) != len(set(ids))
                    or any(not validator.is_valid(s) or s['freshness'] != 'FRESH'
                           or timestamp(s['capturedAt']) > at for s in evidence)):
                reasons.append('Evidence must have unique, current, valid source references.')
            checks = proposal.get('checks', proposal.get('validationResults', []))
            if not checks or any(c['outcome'] != 'PASS' or not set(c['sourceIds']) <= set(ids)
                                 for c in checks):
                reasons.append('All applicable deterministic checks must pass with resolved sources.')
            claimed = proposal.get('sourceIds', [s['sourceId'] for s in proposal.get('sourceReferences', [])])
            if not claimed or not set(claimed) <= set(ids):
                reasons.append('Proposal source references are unresolved.')
            domain = self.validators.get(ref['subjectType'])
            if domain is None:
                reasons.append('No domain review validator is configured for this subject type.')
            else:
                reasons.extend(domain(deepcopy(proposal), deepcopy(evidence), deepcopy(policies)))
        except (ValueError, KeyError, TypeError, ArithmeticError):
            reasons.append('Domain review input is incomplete or invalid.')
        return dict(reviewId=str(uuid4()), subject=ref,
                    outcome='REVISION_REQUIRED' if reasons else 'PASS', reasons=reasons,
                    reviewedAt=self.clock(), policyVersion='shared-deterministic-review-1',
                    sourceIds=[s['sourceId'] for s in evidence])
