import unittest
from pathlib import Path
from src.generators.batch_generator import BatchFailureGenerator
from src.orchestrator.batch_pipeline import BatchRecoveryPipeline, BatchSimulationResults


class TestBatchRecoveryPipeline(unittest.TestCase):
    def setUp(self):
        self.generator = BatchFailureGenerator(seed=42)
        self.pipeline = BatchRecoveryPipeline(seed=42)

    def test_run_small_batch_simulation(self):
        events = self.generator.generate_batch(50)
        summary, fsms = self.pipeline.run_batch_simulation(events, simulation_days=14)

        self.assertEqual(summary.total_transactions, 50)
        self.assertGreater(summary.total_recovered_revenue_inr, 0.0)
        self.assertGreater(summary.overall_recovery_rate_pct, 15.0)
        self.assertEqual(len(fsms), 50)
        self.assertGreater(summary.total_audit_events_recorded, 50)

    def test_run_full_750_batch_simulation(self):
        dataset_path = Path(__file__).resolve().parent.parent / "data" / "synthetic_transactions_750.json"
        events = self.generator.load_from_json(dataset_path)
        summary, fsms = self.pipeline.run_batch_simulation(events, simulation_days=14)

        self.assertEqual(summary.total_transactions, 750)
        self.assertGreater(summary.overall_recovery_rate_pct, 20.0, "Recovery rate should exceed 20% across full portfolio")
        self.assertGreater(summary.total_recovered_revenue_inr, 5000000.0, "Recovered volume should exceed ₹50 Lakhs")
        self.assertGreater(summary.recovered_count, 150)
        self.assertGreater(summary.total_audit_events_recorded, 1000)


if __name__ == "__main__":
    unittest.main()
