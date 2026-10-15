"""Explicit B08 fixture adapters. Do not use these as B05/B07/B10 services."""
import json
import sqlite3
from contextlib import closing
from copy import deepcopy

from tripmate.contracts import validate
from tripmate.fixtures.b03 import FIXTURE_TIME, fixture_quotes
from .application import SupplierRuntime
from .common import PricingPolicy, SOURCE_FIELDS, SupplierError, envelope, subject, uid
from .repository import SupplierRepository


class FixtureServices:
    def __init__(self, database):
        self.database = str(database)
        with closing(sqlite3.connect(self.database)) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS supplier_fixture_events (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS supplier_fixture_approvals (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')

    def append(self, event):
        validate('TraceEvent', event)
        if event['executionMode'] != 'FIXTURE':
            raise ValueError('Fixture trace adapter cannot record real execution')
        with closing(sqlite3.connect(self.database)) as db, db:
            db.execute('INSERT INTO supplier_fixture_events VALUES (?, ?)', (event['eventId'], json.dumps(event)))

    def save(self, approval):
        validate('Approval', approval)
        if not all(source['simulated'] for source in approval['sourceReferences']):
            raise ValueError('Fixture approval adapter requires simulated evidence')
        with closing(sqlite3.connect(self.database)) as db, db:
            db.execute('INSERT INTO supplier_fixture_approvals VALUES (?, ?)', (uid('fixture-decision'), json.dumps(approval)))

    def find_by_subject(self, ref):
        with closing(sqlite3.connect(self.database)) as db:
            values = [json.loads(row[0]) for row in db.execute('SELECT payload FROM supplier_fixture_approvals ORDER BY rowid')]
        return [value for value in values if value['subject'] == ref]

    def authorise(self, requester_id, action, target):
        return requester_id == ('fixture-human' if action == 'APPROVE_SUPPLIER_TERMS' else 'fixture-supplier')

    def review(self, offer, evidence, policies):
        passed = bool(offer['validationResults']) and all(row['outcome'] == 'PASS' for row in offer['validationResults'])
        return dict(reviewId=uid('fixture-review'), subject=subject(offer),
                    outcome='PASS' if passed else 'REVISION_REQUIRED',
                    reasons=['B08 synthetic review only; B10 integration pending'],
                    reviewedAt=FIXTURE_TIME, policyVersion='fixture-only-1',
                    sourceIds=[ref['sourceId'] for ref in evidence])


class FixtureExtractor:
    def extract(self, content, schema):
        """Replay known JSON input; this is not a call to an AI provider."""
        return json.loads(content)


def fixture_runtime(database, scenario='coach'):
    try:
        from tripmate.planning.pricing import DeterministicPricingService
    except ImportError:
        raise SupplierError('TOOL_UNAVAILABLE', 'Merge the B04 pricing implementation from the Planning branch first') from None
    from tripmate.fixtures import baseline
    quotes = {quote['offer']['offerId']: quote for quote in fixture_quotes()}
    invalid = {entity['id'].split(':', 1)[1]: entity for entity in baseline()['entities'] if entity['kind'] == 'OFFER_INPUT'}
    if scenario in quotes:
        quote = quotes[scenario]
        source = quote['offer']
        candidate = {key: deepcopy(source[key]) for key in SOURCE_FIELDS}
        context = dict(offerId=source['offerId'], sourceReferences=deepcopy(source['sourceReferences']),
                       sourceText=json.dumps(candidate), verifiedFacts=deepcopy(candidate),
                       product=deepcopy(quote['product']))
    elif scenario in invalid:
        raw = invalid[scenario]['data']['rawCandidate']
        context = dict(offerId=raw['offerId'], sourceReferences=deepcopy(raw['sourceReferences']),
                       candidate={key: deepcopy(raw[key]) for key in SOURCE_FIELDS if key in raw})
    else:
        raise SupplierError('INVALID_CONTRACT', 'Choose a documented B03 supplier scenario')
    case = envelope(dict(caseId='supplier-demo-' + scenario, correlationId='supplier-demo-' + scenario,
                         sourceReferences=context['sourceReferences']))
    case.update(caseKind='SUPPLIER', caseType='OFFER', externalRequestId='fixture-intake-' + scenario,
                requesterId='fixture-supplier', requesterType='SUPPLIER', confirmedAt=FIXTURE_TIME,
                createdAt=FIXTURE_TIME, status='CONFIRMED', coordinator='operations',
                primaryHandler='supplier', relatedCaseIds=[], humanRequestCount=0,
                confirmedRequest='Synthetic supplier scenario: ' + scenario,
                unresolvedQuestions=[], entitlementDecision=None)
    repository = SupplierRepository(database)
    services = FixtureServices(database)
    policy = PricingPolicy('0.10', '0.00', 'b08-fixture-1')
    pricing = DeterministicPricingService(policy.markup_rate, {'amount': policy.minimum_margin, 'currency': 'AUD'},
                                         policy.version, lambda: FIXTURE_TIME)
    runtime = SupplierRuntime(lambda _: deepcopy(context), repository, pricing, policy,
                              services, services, services, services, FixtureExtractor(),
                              clock=lambda: FIXTURE_TIME,
                              ordinary_terms=('Simulation only; no real supplier commitment.',))
    validate('Case', case)
    return case, runtime
