import unittest
from copy import deepcopy
from unittest.mock import Mock
from tripmate.planning.daily_demo import daily_fixture
from tripmate.planning.factors import load_factors
from tripmate.portal.customer_daily import CustomerDailyFactors, MARKER

class CustomerDailyTests(unittest.TestCase):
    def test_explicit_simulation_and_fixed_expiry(self):
        _,context,runtime=daily_fixture()
        self.addCleanup(runtime.repository.close)
        request=context['request']
        request['hardConstraints'][-1]['description']=MARKER
        context['spec']['constraintBindings']['daily']['description']=MARKER
        ops=Mock();ops.load_context.return_value=context
        provider=CustomerDailyFactors(ops,Mock())
        data=load_factors(provider,request,runtime.offers.quotes,runtime.clock(),'FIXTURE')
        self.assertTrue(data['sources'][0]['simulated'])
        from tripmate.planning.daily import DailyPlanningEngine
        records, excluded = DailyPlanningEngine(data, runtime.clock).generate(request,runtime.offers.quotes,context['spec'])
        self.assertTrue(records, excluded)
        self.assertTrue(all(r['dailySchedule']['additionalCost']['amount']=='120.00' for r in records))
        self.assertEqual(len(data['delays']),3)
        self.assertTrue(all(f['minutes']==30 for f in data['routes']))
        self.assertEqual(data,provider.snapshot(request,runtime.offers.quotes,runtime.clock()))
        with self.assertRaises(ValueError):
            load_factors(provider,request,runtime.offers.quotes,'2030-01-01T00:00:00+11:00','FIXTURE')

    def test_manual_input_does_not_silently_get_simulation(self):
        provider=CustomerDailyFactors(Mock(),Mock())
        request={'hardConstraints':[]}
        provider.snapshot(request,[],'now')
        provider.stored.snapshot.assert_called_once_with(request,[],'now')
