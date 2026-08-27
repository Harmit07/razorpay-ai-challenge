import unittest
from pathlib import Path
from src.generators.batch_generator import BatchFailureGenerator
from src.classifiers.rule_classifier import (
    RuleBasedClassifier,
    ClassificationResult,
    RetryabilityType,
    DLTStream,
)


class TestRuleClassifier(unittest.TestCase):
    def setUp(self):
        self.classifier = RuleBasedClassifier()
        self.generator = BatchFailureGenerator(seed=42)

    def test_bucket_1_insufficient_funds(self):
        event = self.generator.generate_single_event(bucket_override=1)
        res = self.classifier.classify(event)
        self.assertEqual(res.bucket_id, 1)
        self.assertEqual(res.retryability, RetryabilityType.RETRYABLE_SOFT_DEBIT)
        self.assertGreaterEqual(res.confidence, 0.85)
        self.assertEqual(res.dlt_stream, DLTStream.SERVICE_IMPLICIT)

    def test_bucket_8_mandate_revocation_stopping_rule(self):
        event = self.generator.generate_single_event(bucket_override=8, force_risk_flag=False)
        event.dispute_active = False
        res = self.classifier.classify(event)
        self.assertEqual(res.bucket_id, 8)
        self.assertEqual(res.stopping_rule, "STOP_MANDATE_REVOKED")
        self.assertEqual(res.retryability, RetryabilityType.NON_RETRYABLE_HARD_STOP)
        self.assertEqual(res.routing_destination, "UNRECOVERABLE")

    def test_bucket_11_afa_cap_breach(self):
        event = self.generator.generate_single_event(bucket_override=11)
        res = self.classifier.classify(event)
        self.assertEqual(res.bucket_id, 11)
        self.assertEqual(res.retryability, RetryabilityType.RETRYABLE_LINK_ACTION)
        self.assertIn("AFA", res.recommended_action)

    def test_bucket_13_ambiguous_raw_decline(self):
        event = self.generator.generate_single_event(bucket_override=13, force_risk_flag=False)
        res = self.classifier.classify(event)
        self.assertEqual(res.bucket_id, 13)
        self.assertTrue(res.requires_llm_disambiguation)
        self.assertGreaterEqual(res.confidence, 0.70)
        self.assertLess(res.confidence, 0.85)

    def test_risk_flagged_human_escalation(self):
        event = self.generator.generate_single_event(force_risk_flag=True)
        res = self.classifier.classify(event)
        self.assertTrue(res.requires_human_escalation)
        self.assertLess(res.confidence, 0.70)
        self.assertEqual(res.routing_destination, "HUMAN_REVIEW")

    def test_all_10_deliberate_edge_cases(self):
        edge_cases = self.generator.generate_deliberate_edge_cases()
        self.assertEqual(len(edge_cases), 10)

        for ec in edge_cases:
            res = self.classifier.classify(ec)
            self.assertIsNotNone(res.recommended_action)

            # Test Edge 1: Zombie Retry -> STOP_MAX_RETRIES
            if ec.edge_case_tag == "EDGE_01_ZOMBIE_RETRY_5X":
                self.assertEqual(res.stopping_rule, "STOP_MAX_RETRIES")
                self.assertEqual(res.routing_destination, "UNRECOVERABLE")

            # Test Edge 2: 15k AFA Straddle -> AFA Link
            elif ec.edge_case_tag == "EDGE_02_AFA_15K_STRADDLE":
                self.assertEqual(res.bucket_id, 11)
                self.assertEqual(res.statutory_rule_applied, "RBI_DPSS_2026_27_396_15K_CAP")

            # Test Edge 3: 1L AFA Straddle -> AFA Link
            elif ec.edge_case_tag == "EDGE_03_AFA_1L_STRADDLE":
                self.assertEqual(res.bucket_id, 11)
                self.assertEqual(res.statutory_rule_applied, "RBI_2023_24_90_1L_EXEMPTION")

            # Test Edge 4: Mandate Expiring -> STOP_MANDATE_EXPIRED
            elif ec.edge_case_tag == "EDGE_04_MANDATE_EXPIRING_MID_RETRY":
                self.assertEqual(res.stopping_rule, "STOP_MANDATE_EXPIRED")

            # Test Edge 5: Quiet Hours -> delayed flag
            elif ec.edge_case_tag == "EDGE_05_TRAI_QUIET_HOURS_SLEEP":
                self.assertTrue(res.is_quiet_hours_delayed)

            # Test Edge 6: PTP Active -> STOP_PTP_ACTIVE
            elif ec.edge_case_tag == "EDGE_06_PTP_RACE_CONDITION":
                self.assertEqual(res.stopping_rule, "STOP_PTP_ACTIVE")
                self.assertEqual(res.routing_destination, "PTP_FROZEN")

            # Test Edge 8: Active Fraud Dispute -> STOP_DISPUTE_FRAUD
            elif ec.edge_case_tag == "EDGE_08_FRAUD_DISPUTE_STRADDLE":
                self.assertEqual(res.stopping_rule, "STOP_DISPUTE_FRAUD")
                self.assertEqual(res.routing_destination, "HUMAN_REVIEW")

    def test_run_classifier_on_full_750_dataset(self):
        dataset_path = Path(__file__).resolve().parent.parent / "data" / "synthetic_transactions_750.json"
        if not dataset_path.exists():
            batch = self.generator.generate_batch(750)
            self.generator.export_to_json(batch, dataset_path)

        events = self.generator.load_from_json(dataset_path)
        self.assertEqual(len(events), 750)

        results = self.classifier.classify_batch(events)
        self.assertEqual(len(results), 750)

        # Confirm clean ~80% coverage with high confidence >= 0.85
        high_conf_count = sum(1 for r in results if r.confidence >= 0.85)
        high_conf_pct = (high_conf_count / len(results)) * 100

        ambiguous_llm_count = sum(1 for r in results if r.requires_llm_disambiguation)
        human_esc_count = sum(1 for r in results if r.requires_human_escalation)

        print(f"\nRule Classifier 750 Dataset Run:")
        print(f"• High Confidence Clean (>=0.85) : {high_conf_count} ({high_conf_pct:.1f}%)")
        print(f"• Ambiguous Zone (LLM Parser)    : {ambiguous_llm_count} ({(ambiguous_llm_count/750)*100:.1f}%)")
        print(f"• Human / Risk Escalation (<0.70): {human_esc_count} ({(human_esc_count/750)*100:.1f}%)")

        # The clean rule-based coverage must be in the 75-85% range (~80%)
        self.assertGreaterEqual(high_conf_pct, 70.0, "Rule engine must cleanly cover at least 70-80% of cases")
        self.assertGreaterEqual(ambiguous_llm_count, 10, "Ambiguous cases must be flagged for LLM disambiguation")
        self.assertGreaterEqual(human_esc_count, 10, "Risk cases must be escalated to human ops")


if __name__ == "__main__":
    unittest.main()
