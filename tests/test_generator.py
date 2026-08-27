import unittest
from src.generators.batch_generator import BatchFailureGenerator


class TestBatchGenerator(unittest.TestCase):
    def setUp(self):
        self.generator = BatchFailureGenerator(seed=123)

    def test_single_event_generation(self):
        event = self.generator.generate_single_event()
        self.assertIsNotNone(event.txn_id)
        self.assertGreater(event.amount, 0)
        self.assertTrue(event.txn_id.startswith("pay_"))
        self.assertTrue("****" in event.customer_phone_masked)

    def test_bucket_override(self):
        for bucket_id in range(1, 13):
            event = self.generator.generate_single_event(bucket_override=bucket_id)
            self.assertIsNotNone(event)

    def test_batch_generation_coverage(self):
        batch = self.generator.generate_batch(count=50)
        self.assertEqual(len(batch), 50)

        # Verify all 12 buckets are represented in the batch
        reasons = {e.error_reason for e in batch}
        self.assertIn("insufficient_funds", reasons)
        self.assertIn("bank_server_down", reasons)
        self.assertIn("gateway_timeout", reasons)
        self.assertIn("card_expired", reasons)
        self.assertIn("mandate_cancelled_by_user", reasons)
        self.assertIn("amount_exceeds_statutory_afa_limit", reasons)
        self.assertIn("checkout_abandonment_dropoff", reasons)

    def test_reproducibility_with_seed(self):
        gen1 = BatchFailureGenerator(seed=999)
        gen2 = BatchFailureGenerator(seed=999)
        b1 = gen1.generate_batch(count=15)
        b2 = gen2.generate_batch(count=15)

        for e1, e2 in zip(b1, b2):
            self.assertEqual(e1.txn_id, e2.txn_id)
            self.assertEqual(e1.amount, e2.amount)
            self.assertEqual(e1.error_reason, e2.error_reason)


if __name__ == "__main__":
    unittest.main()
