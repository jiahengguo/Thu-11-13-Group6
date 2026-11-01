"""UC-04 trusted complaint input through the authenticated portal."""
import unittest
from datetime import timedelta
from uuid import uuid4
from unittest.mock import patch
import test_exception_portal as recovery
from tripmate.operations.common import instant

class ComplaintPortalTests(unittest.TestCase):
    setUp = recovery.ExceptionPortalTests.setUp
    evidence = recovery.ExceptionPortalTests.evidence
    dispatch = recovery.ExceptionPortalTests.dispatch

    def prepare(self, action='EXPLAIN_AND_APOLOGISE'):
        self.cid = self.f.confirm(self.f.traveller, 'COMPLAINT', dict(planId=self.baseline['version']['planId'], details='Investigate the documented service delay.'))
        item = next(i for i in self.baseline['version']['items'] if i['productType']=='TRANSPORT')
        actual = instant(item['endAt']) + timedelta(minutes=60)
        at = (actual + timedelta(minutes=5)).isoformat()
        self.f.app.operations.clock = lambda: at
        self.clock.stop()
        clock = patch('tripmate.exception_handling.runtime.now', return_value=at)
        clock.start(); self.addCleanup(clock.stop)
        return self.evidence(complaintCategory='DELAY', actualArrival=actual.isoformat(), policyAction=action,
                             policyReference='synthetic://policy/delay-v1', validUntil=(actual+timedelta(days=10)).isoformat())

    def test_delay_review_and_delivery(self):
        body=self.prepare()
        status,result,*_=self.f.clients[self.f.operator].call('/api/exception/evidence',body)
        self.assertEqual(status,200,result)
        view=self.dispatch()
        self.assertEqual(view['case']['status'],'UNDER_REVIEW',view)
        self.assertIsNone(view['response'])
        released=self.f.release(self.cid,view['revision'])
        self.assertIn('delay',released['response'].lower())

    def test_refund_requires_human_approval(self):
        body=self.prepare('HUMAN_REVIEW_REFUND')
        self.assertEqual(self.f.clients[self.f.operator].call('/api/exception/evidence',body)[0],200)
        view=self.dispatch()
        self.assertEqual(view['case']['status'],'AWAITING_HUMAN_APPROVAL',view)
        self.assertIsNone(view['response'])

    def test_traveller_cannot_assert_policy_and_future_observation_rejected(self):
        body=self.prepare()
        self.assertEqual(self.f.clients[self.f.traveller].call('/api/exception/evidence',body)[0],403)
        body['actualArrival']='2099-01-01T00:00:00Z'
        self.assertNotEqual(self.f.clients[self.f.operator].call('/api/exception/evidence',body)[0],200)

    def test_missing_evidence_requests_clarification(self):
        self.prepare()
        view=self.dispatch()
        self.assertEqual(view['case']['status'],'AWAITING_REQUESTER',view)
        self.assertIsNone(view['response'])

    def test_low_confidence_requires_human_handling(self):
        body=self.prepare();body['confidence']='LOW'
        self.assertEqual(self.f.clients[self.f.operator].call('/api/exception/evidence',body)[0],200)
        view=self.dispatch()
        self.assertEqual(view['case']['status'],'HUMAN_ASSISTANCE',view)
        self.assertIsNone(view['response'])

    def test_itinerary_complaint_collects_findings_and_refers(self):
        body=self.prepare();body['complaintCategory']='ITINERARY';body.pop('actualArrival')
        self.assertEqual(self.f.clients[self.f.operator].call('/api/exception/evidence',body)[0],200)
        view=self.dispatch()
        self.assertEqual(view['case']['status'],'HUMAN_ASSISTANCE',view)
        investigation=self.f.app.exception.investigation(self.f.operator,self.cid)
        self.assertTrue(investigation['result']['findings'])
