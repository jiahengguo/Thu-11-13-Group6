"""Explicit customer-selected simulation inputs, never supplier approval."""
from datetime import timedelta
from itertools import permutations
from tripmate.planning.common import timestamp
from tripmate.planning.daily import policy_from

MARKER = 'Customer-built simulated daily itinerary'

class CustomerDailyFactors:
    def __init__(self, operations, stored):
        self.ops, self.stored = operations, stored

    def snapshot(self, request, quotes, at):
        if not any(c['description'] == MARKER and c['confirmed'] for c in request['hardConstraints']):
            return self.stored.snapshot(request, quotes, at)
        # The confirmed request fixes the snapshot lifetime; repeated reads cannot renew it.
        context = self.ops.load_context(request['caseId'])
        policy = policy_from(request, context['spec'])
        if not policy:
            raise ValueError('A confirmed daily policy is required')
        ids = {i for slot in policy['slots'] for i in slot['offerIds']}
        selected = [q for q in quotes if q['offer']['offerId'] in ids]
        if len(selected) > 48:
            raise ValueError('Too many selected services')
        captured = request['confirmedAt']
        until = (timestamp(captured) + timedelta(hours=24)).isoformat()
        source = dict(sourceId='customer-simulation',sourceType='FIXTURE',sourceReference='synthetic://customer-daily/v1',capturedAt=captured,freshness='FRESH',simulated=True)
        def fact(**values):
            return dict(capturedAt=captured,validUntil=until,sourceIds=[source['sourceId']],**values)
        data = dict(sources=[source],weather=[],delays=[],routes=[],venues=[])
        locations = {d[k] for d in policy['days'] for k in ('startLocation','endLocation')}
        weather = set()
        for q in selected:
            o,p = q['offer'],q['product']
            locations.update([p['origin'],p['destination']])
            if p['role'] in ('OUTBOUND','RETURN'):
                data['delays'].append(fact(offerId=o['offerId'],offerVersion=o['materialVersion'],status='ON_TIME',departureDelayMinutes=0,arrivalDelayMinutes=0))
            elif p['role'] == 'ACTIVITY':
                data['venues'].append(fact(offerId=o['offerId'],offerVersion=o['materialVersion'],openIntervals=[dict(startAt=p['startAt'],endAt=p['endAt'])],closedIntervals=[],reservationRequired=True,reservationStatus='AVAILABLE',remainingCapacity=request['partySize'],outdoor=True,walkingMinutes=0))
                if p['origin'] not in weather:
                    weather.add(p['origin'])
                    data['weather'].append(fact(location=p['origin'],startAt=policy['days'][0]['startAt'],endAt=policy['days'][-1]['endAt'],rainProbability='0.00',temperatureC='20',windKph='0',severe=False))
        for origin,destination in permutations(sorted(locations),2):
            data['routes'].append(fact(origin=origin,destination=destination,startAt=policy['days'][0]['startAt'],endAt=policy['days'][-1]['endAt'],minutes=30,walkingMinutes=30,partySize=request['partySize'],cost=dict(amount='0.00',currency='AUD')))
        return data
