import unittest
from pathlib import Path
from src.generators.batch_generator import BatchFailureGenerator
from src.benchmarks.naive_baseline import NaiveBaselineRunner
from src.benchmarks.comparative_evaluator import BenchmarkEvaluator


class TestBenchmarks(unittest.TestCase):
    def setUp(self):
        self.generator = BatchFailureGenerator(seed=42)

    def test_naive_baseline_violations_tallied(self):
        events = self.generator.generate_batch(50)
        runner = NaiveBaselineRunner(seed=42)
        results = runner.run_simulation(events)

        self.assertEqual(results.total_transactions, 50)
        self.assertGreater(results.wasted_api_calls, 0)
        self.assertGreater(results.total_compliance_violations, 20, "Naive baseline should trigger numerous statutory violations")
        self.assertGreater(results.violation_rbi_no_24h_pre_debit_notice, 0)

    def test_comparative_evaluator_lift(self):
        events = self.generator.generate_batch(50)
        evaluator = BenchmarkEvaluator(seed=42)
        report = evaluator.evaluate(events, dataset_name="Test_50_Batch")

        self.assertGreater(report.ai_recovered_revenue_inr, report.naive_recovered_revenue_inr)
        self.assertEqual(report.ai_compliance_violations, 0)
        self.assertGreater(report.naive_compliance_violations, 0)
        self.assertEqual(report.compliance_risk_reduction_pct, 100.0)


if __name__ == "__main__":
    unittest.main()
