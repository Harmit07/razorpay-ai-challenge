import unittest
from pathlib import Path
from datetime import datetime, timezone, timedelta
from src.models.schema import PromiseToPayRecord
from src.generators.batch_generator import BatchFailureGenerator
from src.classifiers.rule_classifier import RuleBasedClassifier
from src.router.compliance_router import (
    ComplianceRouter,
    RecoveryActionType,
    RecoveryChannel,
    CandidateActionPlan,
)


class TestComplianceRouter(unittest.TestCase):
    def setUp(self):
        self.generator = BatchFailureGenerator(seed=42)
        self.classifier = RuleBasedClassifier()
        self.router = ComplianceRouter()

    def test_route_bucket_1_insufficient_funds(self):
        event = self.generator.generate_single_event(bucket_override=1, force_risk_flag=False)
        diag = self.classifier.classify(event)
        plan = self.router.route(event, diag)

        self.assertEqual(plan.action_type, RecoveryActionType.AUTO_DEBIT_RETRY)
        self.assertTrue(plan.requires_pre_debit_notice_24h)
        self.assertIsNotNone(plan.pre_debit_notice_dispatch_time)
        self.assertGreaterEqual(plan.cooling_interval_hours, 48)
        self.assertEqual(plan.primary_channel, RecoveryChannel.AUTO_DEBIT_API)

    def test_route_bucket_11_afa_cap_breach(self):
        event = self.generator.generate_single_event(bucket_override=11, force_risk_flag=False)
        diag = self.classifier.classify(event)
        plan = self.router.route(event, diag)

        self.assertEqual(plan.action_type, RecoveryActionType.DYNAMIC_AFA_PAYMENT_LINK)
        self.assertTrue(plan.afa_validation_enforced)
        self.assertIn(plan.primary_channel, [RecoveryChannel.WHATSAPP, RecoveryChannel.SMS])

    def test_route_bucket_7_expired_instrument(self):
        event = self.generator.generate_single_event(bucket_override=7, force_risk_flag=False)
        diag = self.classifier.classify(event)
        plan = self.router.route(event, diag)

        self.assertEqual(plan.action_type, RecoveryActionType.DYNAMIC_INSTRUMENT_UPDATE_LINK)
        self.assertEqual(plan.primary_channel, RecoveryChannel.WHATSAPP)

    def test_route_stopping_rule_revocation(self):
        event = self.generator.generate_single_event(bucket_override=8, force_risk_flag=False)
        event.dispute_active = False
        diag = self.classifier.classify(event)
        plan = self.router.route(event, diag)

        self.assertEqual(plan.action_type, RecoveryActionType.STOP_TERMINATION)
        self.assertEqual(plan.stopping_rule, "STOP_MANDATE_REVOKED")
        self.assertEqual(plan.target_fsm_state, "UNRECOVERABLE")

    def test_route_ptp_active_freeze(self):
        event = self.generator.generate_single_event(bucket_override=1, force_risk_flag=False)
        p_date = event.timestamp + timedelta(days=3)
        event.ptp_record = PromiseToPayRecord(
            promised_date=p_date,
            grace_until=p_date + timedelta(hours=24),
            promised_amount=event.amount,
            status="ACTIVE",
        )
        diag = self.classifier.classify(event)
        plan = self.router.route(event, diag)

        self.assertEqual(plan.action_type, RecoveryActionType.PTP_HOLD_FREEZE)
        self.assertEqual(plan.stopping_rule, "STOP_PTP_ACTIVE")
        self.assertEqual(plan.target_fsm_state, "PTP_FROZEN")

    def test_trai_quiet_hours_delay(self):
        # 11:30 PM IST (18:00 UTC)
        night_time = datetime(2026, 8, 27, 18, 0, tzinfo=timezone.utc)
        adjusted_utc, delayed = self.router.adjust_for_trai_quiet_hours(night_time)
        
        self.assertTrue(delayed)
        # Check that adjusted time is 08:05 AM IST (02:35 UTC next day)
        ist_adjusted = adjusted_utc + timedelta(hours=5, minutes=30)
        self.assertEqual(ist_adjusted.hour, 8)
        self.assertEqual(ist_adjusted.minute, 5)

    def test_full_750_dataset_routing(self):
        dataset_path = Path(__file__).resolve().parent.parent / "data" / "synthetic_transactions_750.json"
        events = self.generator.load_from_json(dataset_path)
        
        diag_results = self.classifier.classify_batch(events)
        plans = self.router.route_batch(list(zip(events, diag_results)))
        
        self.assertEqual(len(plans), 750)
        
        action_counts = {}
        for p in plans:
            action_counts[p.action_type.value] = action_counts.get(p.action_type.value, 0) + 1

        print("\nCompliance Router Action Plan Distribution (750 TXNS):")
        for act, cnt in sorted(action_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"• {act:<32}: {cnt:>4} ({(cnt/750)*100:>5.1f}%)")


if __name__ == "__main__":
    unittest.main()
