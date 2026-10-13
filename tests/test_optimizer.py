"""Automated tests for SQL Query Optimizer core modules."""

import sys
import os
import unittest

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.analyzer import SQLAnalyzer
from core.optimizer import SQLOptimizer
from core.metrics import PerformanceMetricsEngine
from core.database import DatabaseManager
from core.ai_engine import AIEngine


class TestSQLAnalyzer(unittest.TestCase):

    def setUp(self):
        self.analyzer = SQLAnalyzer(dialect="mysql")

    def test_select_star_detection(self):
        query = "SELECT * FROM users WHERE status = 'active';"
        result = self.analyzer.analyze(query)
        self.assertTrue(result.is_valid)
        codes = [i.code for i in result.inefficiencies]
        self.assertIn("SELECT_STAR", codes)

    def test_non_sargable_function_detection(self):
        query = "SELECT id, name FROM orders WHERE YEAR(order_date) = 2024;"
        result = self.analyzer.analyze(query)
        self.assertTrue(result.is_valid)
        codes = [i.code for i in result.inefficiencies]
        self.assertIn("NON_SARGABLE_FUNCTION", codes)

    def test_leading_wildcard_detection(self):
        query = "SELECT id FROM products WHERE name LIKE '%phone%';"
        result = self.analyzer.analyze(query)
        self.assertTrue(result.is_valid)
        codes = [i.code for i in result.inefficiencies]
        self.assertIn("LEADING_WILDCARD_LIKE", codes)

    def test_missing_where_update_detection(self):
        query = "UPDATE users SET is_active = 0;"
        result = self.analyzer.analyze(query)
        self.assertTrue(result.is_valid)
        codes = [i.code for i in result.inefficiencies]
        self.assertIn("MISSING_WHERE_MODIFY", codes)

    def test_cartesian_join_detection(self):
        query = "SELECT * FROM customers, orders;"
        result = self.analyzer.analyze(query)
        self.assertTrue(result.is_valid)
        codes = [i.code for i in result.inefficiencies]
        self.assertTrue(any("JOIN" in c or "CARTESIAN" in c or "CROSS" in c for c in codes))


class TestSQLOptimizer(unittest.TestCase):

    def setUp(self):
        self.analyzer = SQLAnalyzer(dialect="mysql")
        self.optimizer = SQLOptimizer(dialect="mysql")

    def test_sargable_date_rewrite(self):
        query = "SELECT id, order_date FROM orders WHERE YEAR(order_date) = 2024;"
        analysis = self.analyzer.analyze(query)
        opt_res = self.optimizer.optimize(query, analysis)
        self.assertIn("2024-01-01", opt_res.optimized_query)
        self.assertIn("2025-01-01", opt_res.optimized_query)
        self.assertTrue(opt_res.is_modified)

    def test_in_subquery_rewrite(self):
        query = "SELECT id, name FROM users WHERE id IN (SELECT user_id FROM orders);"
        analysis = self.analyzer.analyze(query)
        opt_res = self.optimizer.optimize(query, analysis)
        self.assertIn("EXISTS", opt_res.optimized_query)
        self.assertTrue(opt_res.is_modified)

    def test_index_recommendation(self):
        query = "SELECT id FROM orders WHERE customer_id = 42 AND status = 'PENDING';"
        analysis = self.analyzer.analyze(query)
        opt_res = self.optimizer.optimize(query, analysis)
        self.assertTrue(len(opt_res.index_recommendations) > 0)
        self.assertTrue(any("CREATE INDEX" in idx for idx in opt_res.index_recommendations))


class TestMetricsAndDatabase(unittest.TestCase):

    def setUp(self):
        self.analyzer = SQLAnalyzer(dialect="mysql")
        self.metrics_engine = PerformanceMetricsEngine()
        self.db = DatabaseManager(use_sqlite_fallback=True)

    def test_metrics_calculation(self):
        query = "SELECT * FROM orders WHERE YEAR(order_date) = 2024;"
        analysis = self.analyzer.analyze(query)
        metrics = self.metrics_engine.calculate_estimated_metrics(analysis, is_optimized=False)
        self.assertGreater(metrics.estimated_cost, 0)
        self.assertGreater(metrics.potential_improvement_pct, 0)

    def test_history_logging(self):
        # Insert a test record
        record_id = self.db.save_history(
            original_query="SELECT * FROM test;",
            optimized_query="SELECT id FROM test LIMIT 10;",
            statement_type="SELECT",
            inefficiency_score=35,
            complexity_score=20,
            inefficiencies=[{"code": "SELECT_STAR", "title": "SELECT *"}],
            metrics={"cost": 45.0},
            optimizations=["Replaced SELECT *"],
            explanations=["Reduced memory"],
            index_recommendations=["CREATE INDEX idx_test ON test(id);"],
            mode="Rule-Based Test"
        )
        self.assertIsNotNone(record_id)
        df = self.db.get_history(limit=5)
        self.assertFalse(df.empty)
        self.assertIn("original_query", df.columns)


class TestAIEngine(unittest.TestCase):

    def setUp(self):
        # Test built-in smart engine without external API key
        self.ai = AIEngine(provider="built-in")

    def test_smart_heuristic_optimization(self):
        query = "SELECT * FROM customers WHERE YEAR(created_at) = 2023;"
        resp = self.ai.optimize_with_ai(query)
        self.assertIsNotNone(resp.optimized_sql)
        self.assertTrue(len(resp.optimizations_applied) > 0)
        self.assertTrue(len(resp.explanation) > 0)

    def test_nl_to_sql_translation(self):
        prompt = "Find customers who placed orders over $500 in the last 30 days"
        resp = self.ai.natural_language_to_sql(prompt)
        self.assertIn("SELECT", resp.sql_query.upper())
        self.assertIn("FROM", resp.sql_query.upper())
        self.assertTrue(len(resp.optimization_highlights) > 0)


if __name__ == "__main__":
    unittest.main()
