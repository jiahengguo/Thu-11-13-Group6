"""Dated synthetic inventory for the customer daily planner; no auto-approval."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from tripmate.operations.common import instant


SERVICES = [
    ('sydney-goulburn', 'OUTBOUND', 0, '08:00', 0, '09:30', 'Sydney Central', 'Goulburn Station'),
    ('goulburn-canberra', 'OUTBOUND', 0, '10:00', 0, '11:00', 'Goulburn Station', 'Canberra Central'),
    ('canberra-melbourne', 'OUTBOUND', 1, '09:00', 1, '13:00', 'Canberra Central', 'Melbourne Centre'),
    ('canberra-stay', 'STAY', 0, '17:00', 1, '09:00', 'Canberra Hotel', 'Canberra Hotel'),
    ('melbourne-stay', 'STAY', 1, '17:00', 2, '10:00', 'Melbourne Hotel', 'Melbourne Hotel'),
    ('canberra-museum', 'ACTIVITY', 0, '14:00', 0, '15:00', 'Canberra Museum', 'Canberra Museum'),
    ('melbourne-gallery', 'ACTIVITY', 1, '15:00', 1, '16:00', 'Melbourne Gallery', 'Melbourne Gallery'),
    ('morning-museum', 'ACTIVITY', 2, '10:00', 2, '11:30', 'Melbourne Museum', 'Melbourne Museum'),
    ('outdoor-garden', 'ACTIVITY', 2, '14:00', 2, '15:30', 'Melbourne Garden', 'Melbourne Garden'),
    ('indoor-aquarium', 'ACTIVITY', 2, '14:00', 2, '15:30', 'Melbourne Aquarium', 'Melbourne Aquarium'),
]

ASSUMPTIONS = ('Explicit simulated inventory; no reservations or payments. '
               'On-time transport, available venues, 20 C/no rain, and 30-minute walking transfers '
               'at zero extra cost. Factors expire 24 hours after request confirmation.')


def when(start, day, local_time):
    hour, minute = map(int, local_time.split(':'))
    return datetime.combine(start + timedelta(days=day), datetime.min.time(),
                            ZoneInfo('Australia/Sydney')).replace(hour=hour, minute=minute).isoformat()


def supplier_inputs(namespace, scenario, start, at):
    result = []
    for name, role, first, begins, last, ends, origin, destination in SERVICES:
        reference = namespace + '-' + scenario + '-' + name
        result.append((name, dict(offerReference=reference, productId=reference,
            productType={'OUTBOUND': 'TRANSPORT', 'STAY': 'ACCOMMODATION', 'ACTIVITY': 'ACTIVITY'}[role],
            availableQuantity=1, quotedQuantity=1, unitBasis='One complete simulated party package',
            supplierCost=dict(amount='180.00', currency='AUD'), mandatoryChargesIncluded=True,
            validFrom=(instant(at) - timedelta(days=1)).isoformat(), validUntil=when(start, 3, '23:00'),
            cancellationTerms='Simulation: refundable until 24 hours before service; no real reservation.',
            commercialTerms=[], sourceReference='synthetic://multi-city/' + namespace + '/' + scenario + '/' + name,
            product=dict(role=role, startAt=when(start, first, begins), endAt=when(start, last, ends),
                origin=origin, destination=destination, partySize=1, accessible=True, baggageKg=20,
                comfort='0.80', reliability='0.95', minConnectionMinutes=30,
                openingStart=when(start, first, '08:00') if role == 'ACTIVITY' else None,
                openingEnd=when(start, first, '20:00') if role == 'ACTIVITY' else None))))
    return result


def daily_policy(start, offer_ids):
    stops = [('Sydney Central', 'Canberra Hotel'), ('Canberra Hotel', 'Melbourne Hotel'),
             ('Melbourne Hotel', 'Melbourne Centre')]
    slots = [dict(id=name, role=role, offerIds=[offer_ids[name]]) for name, role, *_ in SERVICES[:-2]]
    slots.append(dict(id='afternoon-choice', role='ACTIVITY',
                      offerIds=[offer_ids['outdoor-garden'], offer_ids['indoor-aquarium']]))
    return dict(version='daily-1', days=[dict(date=(start + timedelta(days=i)).isoformat(),
        startAt=when(start, i, '07:00'), endAt=when(start, i, '22:00'),
        startLocation=a, endLocation=b) for i, (a, b) in enumerate(stops)], slots=slots,
        limits=dict(maxWalkingMinutes=180, maxActivityMinutes=240, maxContinuousMinutes=300,
                    minRestMinutes=20, maxRainProbability='0.60', minTemperatureC='5',
                    maxTemperatureC='35', maxWindKph='40'),
        mealWindows=[dict(start='12:00', end='14:00', minutes=30),
                     dict(start='18:00', end='20:00', minutes=30)],
        mealBudgetPerDay=dict(amount='40.00', currency='AUD'))
