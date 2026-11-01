"""UC-07 access boundaries against replaceable simulated inputs."""
import unittest
from unittest.mock import Mock
import test_operations as fixtures
PAID, FREE = fixtures.PAID, fixtures.FREE
from tripmate.operations.rules import Entitlements

class BenefitsTests(unittest.TestCase):
    setUp = fixtures.OperationsTests.setUp
    key = fixtures.OperationsTests.key
    def test_map_and_ads_are_gated(self):
        paid = self.service.premium(PAID, self.key(), "ROUTE_MAP")
        free = self.service.premium(FREE, self.key(), "ROUTE_MAP")
        self.assertTrue(paid["routePoints"])
        self.assertEqual(paid["ads"], [])
        self.assertNotIn("routePoints", free)
        self.assertTrue(free["ads"])
        self.assertFalse(free["rankingAffected"])

    def test_member_offer_eligibility_and_missing_rule(self):
        rule = "demo-paid-benefit-v1"
        self.assertEqual(self.service.premium(PAID, self.key(), "MEMBER_OFFER", rule)["decision"]["outcome"], "ALLOWED")
        self.assertEqual(self.service.premium(FREE, self.key(), "MEMBER_OFFER", rule)["decision"]["outcome"], "DENIED")
        self.assertEqual(self.service.premium(PAID, self.key(), "MEMBER_OFFER", "missing")["decision"]["outcome"], "DENIED")

    def test_replayed_key_cannot_reuse_expired_access(self):
        key = self.key()
        self.assertIn("routePoints", self.service.premium(PAID, key, "ROUTE_MAP"))
        self.service.entitlement.clock = lambda: "2040-01-01T00:00:00Z"
        result = self.service.premium(PAID, key, "ROUTE_MAP")
        self.assertEqual(result["decision"]["outcome"], "DENIED")
        self.assertNotIn("routePoints", result)

class EvidenceTests(unittest.TestCase):
    def test_unavailable_evidence_fails_closed(self):
        decision = Entitlements(Mock(side_effect=RuntimeError("offline")), lambda _: [], lambda: "2026-10-13T00:00:00Z").evaluate("a", "ROUTE_MAP", {})
        self.assertEqual(decision["outcome"], "VERIFICATION_FAILED")

class PortalBenefitsTests(unittest.TestCase):
    def test_verified_portal_identity_and_provider(self):
        from test_portals import FakeCloud
        from tripmate.portal.server import Portal
        cloud = FakeCloud()
        actor, _ = cloud.add()
        app = Portal(cloud)
        body = {"requestKey": "portal-map", "action": "ROUTE_MAP"}
        self.assertNotIn("routePoints", app.operation("premium", body, cloud.profile(actor)))
        cloud.accounts[actor].update(membership="PAID", paidUntil="2099-01-01T00:00:00Z")
        self.assertIn("routePoints", app.operation("premium", body, cloud.profile(actor)))
        cloud.accounts[actor].update(membership="FREE", paidUntil=None)
        self.assertNotIn("routePoints", app.operation("premium", body, cloud.profile(actor)))
