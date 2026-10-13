"""Tests for FastAPI endpoints in api.py."""

import sys
import os
import unittest
from fastapi.testclient import TestClient

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api import app


class TestAPI(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_root_endpoint(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "online")

    def test_optimize_endpoint(self):
        payload = {
            "query": "SELECT * FROM orders WHERE YEAR(order_date) = 2024;",
            "dialect": "mysql",
            "use_ai": False
        }
        res = self.client.post("/api/optimize", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["is_valid"])
        self.assertIn("2024-01-01", data["optimized_query"])
        self.assertGreater(len(data["inefficiencies"]), 0)

    def test_natural_language_endpoint(self):
        payload = {
            "prompt": "Find customers who placed orders over $500 in the last 30 days"
        }
        res = self.client.post("/api/natural-language", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("SELECT", data["sql_query"].upper())
        self.assertTrue(len(data["optimization_highlights"]) > 0)


if __name__ == "__main__":
    unittest.main()
