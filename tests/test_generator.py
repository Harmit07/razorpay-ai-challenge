import unittest
import tempfile
from pathlib import Path
from src.generators.batch_generator import BatchFailureGenerator
from src.models.schema import TransactionType


class TestBatchGenerator(unittest.TestCase):
    def setUp(self):
        self.generator = BatchFailureGenerator(seed=123)

    def test_single_event_generation(self):
        event = self.generator.generate_single_event()
        self.assertIsNotNone(event.txn_id)
        self.assertGreater(event.amount, 0)
        self.assertTrue(event.txn_id.startswith("pay_"))
        self.assertTrue("****" in event.customer_phone_masked)

    def test_bucket_override_all_13_buckets(self):
        for bucket_id in range(1, 14):
            event = self.generator.generate_single_event(bucket_override=bucket_id)
            self.assertIsNotNone(event)
            if bucket_id == 13:
                self.assertEqual(event.error_reason, "raw_unmapped_decline")
                self.assertIsNotNone(event.raw_error_description)

    def test_deliberate_edge_cases_injection(self):
        edge_cases = self.generator.generate_deliberate_edge_cases()
        self.assertEqual(len(edge_cases), 10)

        tags = {e.edge_case_tag for e in edge_cases}
        expected_tags = {
            "EDGE_01_ZOMBIE_RETRY_5X",
            "EDGE_02_AFA_15K_STRADDLE",
            "EDGE_03_AFA_1L_STRADDLE",
            "EDGE_04_MANDATE_EXPIRING_MID_RETRY",
            "EDGE_05_TRAI_QUIET_HOURS_SLEEP",
            "EDGE_06_PTP_RACE_CONDITION",
            "EDGE_07_MANDATE_REVOKED_POST_FAILURE",
            "EDGE_08_FRAUD_DISPUTE_STRADDLE",
            "EDGE_09_MSMED_45_DAY_CLASH",
            "EDGE_10_AMBIGUOUS_HIGH_RISK",
        }
        self.assertEqual(tags, expected_tags)

        # Test specific edge case properties
        e01 = next(e for e in edge_cases if e.edge_case_tag == "EDGE_01_ZOMBIE_RETRY_5X")
        self.assertEqual(e01.current_attempt_count, 3)

        e02 = next(e for e in edge_cases if e.edge_case_tag == "EDGE_02_AFA_15K_STRADDLE")
        self.assertEqual(e02.amount, 15001.00)
        self.assertTrue(e02.requires_afa_validation)

        e03 = next(e for e in edge_cases if e.edge_case_tag == "EDGE_03_AFA_1L_STRADDLE")
        self.assertEqual(e03.amount, 100001.00)
        self.assertTrue(e03.requires_afa_validation)

        e06 = next(e for e in edge_cases if e.edge_case_tag == "EDGE_06_PTP_RACE_CONDITION")
        self.assertIsNotNone(e06.ptp_record)
        self.assertEqual(e06.ptp_record.status, "ACTIVE")

    def test_batch_generation_coverage(self):
        batch = self.generator.generate_batch(count=50)
        self.assertEqual(len(batch), 50)

        # Verify key buckets are represented in the batch
        reasons = {e.error_reason for e in batch}
        self.assertIn("insufficient_funds", reasons)
        self.assertIn("bank_server_down", reasons)
        self.assertIn("gateway_timeout", reasons)
        self.assertIn("card_expired", reasons)
        self.assertIn("mandate_cancelled_by_user", reasons)
        self.assertIn("amount_exceeds_statutory_afa_limit", reasons)
        self.assertIn("checkout_abandonment_dropoff", reasons)
        self.assertIn("raw_unmapped_decline", reasons)

        # Verify the batch contains ambiguous / unstructured decline descriptions
        ambiguous_cases = [e for e in batch if e.raw_error_description is not None]
        self.assertGreaterEqual(len(ambiguous_cases), 3, "Batch must contain at least 3 ambiguous/unstructured cases")

        # Verify the batch contains risk-flagged cases
        risk_flagged_cases = [e for e in batch if e.risk_flag]
        self.assertGreaterEqual(len(risk_flagged_cases), 3, "Batch must contain at least 3 risk-flagged cases")

    def test_large_solo_scale_batch_750(self):
        batch = self.generator.generate_batch(count=750)
        self.assertEqual(len(batch), 750)

        summary = self.generator.print_batch_summary(batch)
        self.assertEqual(summary["total_transactions"], 750)
        self.assertGreater(summary["total_revenue_at_risk_inr"], 5000000.0)
        self.assertEqual(summary["injected_edge_cases_count"], 10)

        # Check transaction types mix
        types = summary["transaction_type_breakdown"]
        self.assertIn("RECURRING_SUBSCRIPTION", types)
        self.assertIn("CHECKOUT_DROP_OFF", types)
        self.assertIn("B2B_INVOICE", types)

    def test_export_and_load_json(self):
        batch = self.generator.generate_batch(count=20)
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test_batch.json"
            self.generator.export_to_json(batch, file_path)
            self.assertTrue(file_path.exists())

            loaded_batch = self.generator.load_from_json(file_path)
            self.assertEqual(len(loaded_batch), 20)
            self.assertEqual(loaded_batch[0].txn_id, batch[0].txn_id)
            self.assertEqual(loaded_batch[0].amount, batch[0].amount)

    def test_reproducibility_with_seed(self):
        gen1 = BatchFailureGenerator(seed=999)
        gen2 = BatchFailureGenerator(seed=999)
        b1 = gen1.generate_batch(count=15)
        b2 = gen2.generate_batch(count=15)

        for e1, e2 in zip(b1, b2):
            self.assertEqual(e1.txn_id, e2.txn_id)
            self.assertEqual(e1.amount, e2.amount)
            self.assertEqual(e1.error_reason, e2.error_reason)
            self.assertEqual(e1.risk_flag, e2.risk_flag)
            self.assertEqual(e1.raw_error_description, e2.raw_error_description)


if __name__ == "__main__":
    unittest.main()
