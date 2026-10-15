"""Backend-only, explicit daily-factor fixture: Sydney/Goulburn/Canberra/Melbourne."""
import argparse
from copy import deepcopy
import json
from pathlib import Path

from tripmate.agents.planning import TravelPlanningAgent
from .common import money
from .fixtures import fixture_runtime, fixture_quotes, source, FIXTURE_TIME
from .pricing import DeterministicPricingService
from .factors import FixtureTravelFactors


def daily_fixture():
    case, context, runtime = fixture_runtime('VALUE', '2000.00')
    rows = [
        ('sydney-goulburn','OUTBOUND','20T08:00','20T09:30','Sydney Central','Goulburn Station','70'),
        ('goulburn-canberra','OUTBOUND','20T10:00','20T11:00','Goulburn Station','Canberra Central','50'),
        ('canberra-melbourne','OUTBOUND','21T09:00','21T13:00','Canberra Central','Melbourne Centre','140'),
        ('canberra-stay','STAY','20T17:00','21T09:00','Canberra Hotel','Canberra Hotel','120'),
        ('melbourne-stay','STAY','21T17:00','22T10:00','Melbourne Hotel','Melbourne Hotel','150'),
        ('canberra-museum','ACTIVITY','20T14:00','20T15:00','Canberra Museum','Canberra Museum','30'),
        ('melbourne-gallery','ACTIVITY','21T15:00','21T16:00','Melbourne Gallery','Melbourne Gallery','30'),
        ('morning-museum','ACTIVITY','22T10:00','22T11:30','Melbourne Museum','Melbourne Museum','30'),
        ('outdoor-garden','ACTIVITY','22T14:00','22T15:30','Melbourne Garden','Melbourne Garden','20'),
        ('indoor-aquarium','ACTIVITY','22T14:00','22T15:30','Melbourne Aquarium','Melbourne Aquarium','45'),
    ]
    def time(t): return '2026-10-' + t + ':00+11:00'
    quote_template = {q['product']['role']:q for q in fixture_quotes()}
    quotes=[]
    for name,role,start,end,origin,destination,cost in rows:
        q=deepcopy(quote_template[role]);o,p=q['offer'],q['product']
        o.update(offerId=name,productId=name,supplierCost=money(cost),sourceReferences=[source(name)],review=None,status='DRAFT',priceBreakdownId=None)
        o['validationResults']=[]
        q['price']=DeterministicPricingService('0.10',money('0.00'),'daily-fixture-1',runtime.clock).calculate(o)
        o.update(status='APPROVED',priceBreakdownId=q['price']['priceBreakdownId'],
                 review={'reviewId':'fixture-'+name,'subject':{'subjectType':'SupplierOffer','subjectId':name,'materialVersion':1},'outcome':'PASS',
                         'reasons':['Simulated supplier approval'],'reviewedAt':FIXTURE_TIME,'policyVersion':'fixture-only','sourceIds':[name]})
        p.update(productId=name,role=role,startAt=time(start),endAt=time(end),origin=origin,destination=destination,
                 minConnectionMinutes=30 if role=='OUTBOUND' else 0,sourceIds=[name],
                 openingStart=time(start[:2]+'T08:00') if role=='ACTIVITY' else None,
                 openingEnd=time(start[:2]+'T20:00') if role=='ACTIVITY' else None)
        quotes.append(q)
    policy={'version':'daily-1','days':[
        {'date':'2026-10-20','startAt':time('20T07:00'),'endAt':time('20T20:00'),'startLocation':'Sydney Central','endLocation':'Canberra Hotel'},
        {'date':'2026-10-21','startAt':time('21T08:00'),'endAt':time('21T20:00'),'startLocation':'Canberra Hotel','endLocation':'Melbourne Hotel'},
        {'date':'2026-10-22','startAt':time('22T08:00'),'endAt':time('22T17:00'),'startLocation':'Melbourne Hotel','endLocation':'Melbourne Centre'}],
        'slots':[{'id':name,'role':role,'offerIds':[name]} for name,role,*_ in rows[:-2]]+
                [{'id':'afternoon-choice','role':'ACTIVITY','offerIds':['outdoor-garden','indoor-aquarium']}],
        'limits':{'maxWalkingMinutes':180,'maxActivityMinutes':240,'maxContinuousMinutes':300,'minRestMinutes':20,
                  'maxRainProbability':'0.60','minTemperatureC':'5','maxTemperatureC':'35','maxWindKph':'40'},
        'mealWindows':[{'start':'12:00','end':'14:00','minutes':30},{'start':'18:00','end':'20:00','minutes':30}],
        'mealBudgetPerDay':money('40.00')}
    context['request']['hardConstraints'].append({'constraintId':'daily','kind':'OTHER','description':'Confirmed daily travel policy','confirmed':True})
    context['spec']['constraintBindings']['daily']={'description':'Confirmed daily travel policy','value':policy}
    def fact(**data):
        return {'capturedAt':FIXTURE_TIME,'validUntil':'2026-10-13T10:00:00+11:00','sourceIds':['daily-factors'],**data}
    facts={'sources':[source('daily-factors')],'weather':[],'delays':[],'routes':[],'venues':[]}
    for q in quotes:
        p,o=q['product'],q['offer']
        if p['role']=='OUTBOUND':
            facts['delays'].append(fact(offerId=o['offerId'],offerVersion=1,status='ON_TIME',departureDelayMinutes=0,arrivalDelayMinutes=0))
        elif p['role']=='ACTIVITY':
            facts['venues'].append(fact(offerId=o['offerId'],offerVersion=1,openIntervals=[{'startAt':p['openingStart'],'endAt':p['openingEnd']}],closedIntervals=[],
                                       reservationRequired=True,reservationStatus='AVAILABLE',remainingCapacity=5,outdoor=o['offerId']=='outdoor-garden',walkingMinutes=30))
            facts['weather'].append(fact(location=p['origin'],startAt=p['openingStart'],endAt=p['openingEnd'],rainProbability='0.85',temperatureC='18',windKph='12',severe=False))
    for origin,dest in [('Canberra Central','Canberra Museum'),('Canberra Museum','Canberra Hotel'),('Canberra Hotel','Canberra Central'),
                        ('Melbourne Centre','Melbourne Gallery'),('Melbourne Gallery','Melbourne Hotel'),('Melbourne Hotel','Melbourne Museum'),
                        ('Melbourne Museum','Melbourne Garden'),('Melbourne Museum','Melbourne Aquarium'),('Melbourne Garden','Melbourne Centre'),('Melbourne Aquarium','Melbourne Centre')]:
        facts['routes'].append(fact(origin=origin,destination=dest,startAt=time('20T00:00'),endAt=time('23T00:00'),minutes=15,walkingMinutes=15,partySize=1,cost=money('0.00')))
    runtime.offers.quotes=quotes
    runtime.factors=FixtureTravelFactors(facts)
    return case,context,runtime


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('output/daily-planning'))
    parser.add_argument('--live-model',action='store_true')
    args=parser.parse_args()
    case,context,runtime=daily_fixture()
    try:
        if args.live_model:
            from tripmate.adapters.campus import load_local_config,CampusLLMService
            from .campus import ModelPlanningEngine
            load_local_config();runtime.planner=ModelPlanningEngine(CampusLLMService(),runtime.clock)
        result=TravelPlanningAgent(runtime).handle_case(case)
        records=[runtime.repository.get_version(s['subjectId']) for s in result['subjects']]
        data={'notice':'SIMULATED supplier/weather/traffic/routes/venues/reviewer. No real reservations. Fixed clock '+FIXTURE_TIME,
              'result':result,'options':records}
        args.output.mkdir(parents=True,exist_ok=True)
        (args.output/'report.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
        lines=['# Daily planning backend report','',data['notice'],'',result['status']]
        for r in records:
            lines += ['', '## '+r['version']['totalPrice']['amount']+' AUD', '', 'Includes meal allowance and route estimates.', '', '| Kind | Start | End | Location / offer |','| --- | --- | --- | --- |']
            for e in r['dailySchedule']['timeline']:
                lines.append('| '+ ' | '.join(str(e.get(k,'')) for k in ['kind','startAt','endAt'])+' | '+str(e.get('offerId',e.get('destination','Reserved break')))+' |')
        (args.output/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
        print(json.dumps({'status':result['status'],'options':len(records),'totals':[r['version']['totalPrice'] for r in records],'errors':result['errors']}))
        return 0 if result['status']=='SUCCESS' else 1
    finally:runtime.repository.close()


if __name__=='__main__':raise SystemExit(main())
