import importlib.util
import unittest

AVAILABLE=all(importlib.util.find_spec(name) for name in ("fastapi","sqlalchemy","httpx"))

@unittest.skipUnless(AVAILABLE,"install API dependencies for endpoint integration tests")
class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from plant_monitor.api import app
        cls.client=TestClient(app)
    def test_process_and_history_endpoints(self):
        response=self.client.get("/process")
        self.assertEqual(response.status_code,200); self.assertEqual(response.json()["source"],"simulator")
        history=self.client.get("/history").json(); self.assertTrue(history)
    def test_event_limit_validation(self): self.assertEqual(self.client.get("/events?limit=0").status_code,422)
