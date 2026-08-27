import unittest
from datetime import datetime, timezone, timedelta
from src.generators.batch_generator import BatchFailureGenerator
from src.models.schema import (
    TransactionType,
    TransactionCategory,
    PromiseToPayRecord,
    AttemptRecord,
    AttemptStatus,
)
from src.classifiers.rule_classifier import DLTStream
from src.router.compliance_router import (
    ComplianceRouter,
    ComplianceEnforcer,
    ComplianceViolationError,
    CandidateActionPlan,
    RecoveryActionType,
    RecoveryChannel,
)


class TestHardCodedComplianceGuards(unittest.TestCase):
    """
    Adversarial test suite proving that statutory and engineering compliance guards
    CANNOT be bypassed under any circumstances.
    """
    def setUp(self):
        self.generator = BatchFailureGenerator(seed=42)
        self.router = ComplianceRouter()

    def test_guard_blocks_auto_debit_without_24h_pre_debit_notice(self):
        event = self.generator.generate_single_event(bucket_override=1, force_risk_flag=False)
        event.txn_type = TransactionType.RECURRING_SUBSCRIPTION
        
        # Craft an illegal action plan with only 2 hours notice
        now = event.timestamp
        illegal_plan = CandidateActionPlan(
            txn_id=event.txn_id,
            action_type=RecoveryActionType.AUTO_DEBIT_RETRY,
            primary_channel=RecoveryChannel.AUTO_DEBIT_API,
            scheduled_execution_time=now + timedelta(hours=2),
            requires_pre_debit_notice_24h=True,
            pre_debit_notice_dispatch_time=now,  # Only 2 hours prior!
            compliance_audit_reasoning="Illegal bypass test",
        )

        with self.assertRaises(ComplianceViolationError) as ctx:
            ComplianceEnforcer.validate(illegal_plan, event)
        self.assertIn("VIOLATION_RBI_24H_PRE_DEBIT", str(ctx.exception))

    def test_guard_blocks_auto_debit_exceeding_15k_afa_cap(self):
        event = self.generator.generate_single_event(bucket_override=1, force_risk_flag=False)
        event.txn_type = TransactionType.RECURRING_SUBSCRIPTION
        event.category = TransactionCategory.STANDARD
        event.amount = 15001.00  # Exceeds ₹15k cap

        illegal_plan = CandidateActionPlan(
            txn_id=event.txn_id,
            action_type=RecoveryActionType.AUTO_DEBIT_RETRY,  # Illegal auto-debit on > ₹15k
            primary_channel=RecoveryChannel.AUTO_DEBIT_API,
            scheduled_execution_time=event.timestamp + timedelta(days=2),
            requires_pre_debit_notice_24h=True,
            pre_debit_notice_dispatch_time=event.timestamp + timedelta(days=1),
            compliance_audit_reasoning="Illegal bypass test",
        )

        with self.assertRaises(ComplianceViolationError) as ctx:
            ComplianceEnforcer.validate(illegal_plan, event)
        self.assertIn("VIOLATION_RBI_AFA_CAP_EXCEEDED", str(ctx.exception))

    def test_guard_blocks_auto_debit_exceeding_1L_exempt_cap(self):
        event = self.generator.generate_single_event(bucket_override=1, force_risk_flag=False)
        event.txn_type = TransactionType.RECURRING_SUBSCRIPTION
        event.category = TransactionCategory.MUTUAL_FUND
        event.amount = 100001.00  # Exceeds ₹1L exempt cap

        illegal_plan = CandidateActionPlan(
            txn_id=event.txn_id,
            action_type=RecoveryActionType.AUTO_DEBIT_RETRY,
            primary_channel=RecoveryChannel.AUTO_DEBIT_API,
            scheduled_execution_time=event.timestamp + timedelta(days=2),
            requires_pre_debit_notice_24h=True,
            pre_debit_notice_dispatch_time=event.timestamp + timedelta(days=1),
            compliance_audit_reasoning="Illegal bypass test",
        )

        with self.assertRaises(ComplianceViolationError) as ctx:
            ComplianceEnforcer.validate(illegal_plan, event)
        self.assertIn("VIOLATION_RBI_AFA_CAP_EXCEEDED", str(ctx.exception))

    def test_guard_blocks_retry_when_3_attempts_exhausted(self):
        event = self.generator.generate_single_event(bucket_override=1, force_risk_flag=False)
        # Inject 3 prior failed attempts
        event.attempt_history = [
            AttemptRecord(attempt_number=1, timestamp=event.timestamp - timedelta(days=4), status=AttemptStatus.FAILED, reason="insufficient_funds", channel="AUTO_DEBIT"),
            AttemptRecord(attempt_number=2, timestamp=event.timestamp - timedelta(days=2), status=AttemptStatus.FAILED, reason="insufficient_funds", channel="AUTO_DEBIT"),
            AttemptRecord(attempt_number=3, timestamp=event.timestamp, status=AttemptStatus.FAILED, reason="insufficient_funds", channel="AUTO_DEBIT"),
        ]

        illegal_plan = CandidateActionPlan(
            txn_id=event.txn_id,
            action_type=RecoveryActionType.AUTO_DEBIT_RETRY,
            primary_channel=RecoveryChannel.AUTO_DEBIT_API,
            scheduled_execution_time=event.timestamp + timedelta(days=2),
            requires_pre_debit_notice_24h=True,
            pre_debit_notice_dispatch_time=event.timestamp + timedelta(days=1),
            compliance_audit_reasoning="Illegal 4th attempt bypass test",
        )

        with self.assertRaises(ComplianceViolationError) as ctx:
            ComplianceEnforcer.validate(illegal_plan, event)
        self.assertIn("VIOLATION_MAX_RETRIES_EXCEEDED", str(ctx.exception))

    def test_guard_blocks_auto_debit_on_revoked_mandate(self):
        event = self.generator.generate_single_event(bucket_override=8, force_risk_flag=False)
        event.dispute_active = False
        event.error_reason = "mandate_cancelled_by_user"

        illegal_plan = CandidateActionPlan(
            txn_id=event.txn_id,
            action_type=RecoveryActionType.AUTO_DEBIT_RETRY,
            primary_channel=RecoveryChannel.AUTO_DEBIT_API,
            scheduled_execution_time=event.timestamp + timedelta(days=2),
            requires_pre_debit_notice_24h=True,
            pre_debit_notice_dispatch_time=event.timestamp + timedelta(days=1),
            compliance_audit_reasoning="Illegal revoked mandate debit",
        )

        with self.assertRaises(ComplianceViolationError) as ctx:
            ComplianceEnforcer.validate(illegal_plan, event)
        self.assertIn("VIOLATION_MANDATE_REVOKED", str(ctx.exception))

    def test_guard_blocks_dunning_during_active_ptp(self):
        event = self.generator.generate_single_event(bucket_override=1, force_risk_flag=False)
        p_date = event.timestamp + timedelta(days=3)
        event.ptp_record = PromiseToPayRecord(
            promised_date=p_date,
            grace_until=p_date + timedelta(hours=24),
            promised_amount=event.amount,
            status="ACTIVE",
        )

        illegal_plan = CandidateActionPlan(
            txn_id=event.txn_id,
            action_type=RecoveryActionType.VOICE_RECOVERY_CALL,
            primary_channel=RecoveryChannel.VOICE_BOT,
            scheduled_execution_time=event.timestamp + timedelta(hours=12),
            compliance_audit_reasoning="Illegal PTP breach test",
        )

        with self.assertRaises(ComplianceViolationError) as ctx:
            ComplianceEnforcer.validate(illegal_plan, event)
        self.assertIn("VIOLATION_PTP_FREEZE_BREACH", str(ctx.exception))

    def test_guard_blocks_promotional_outreach_on_dnd(self):
        event = self.generator.generate_single_event(bucket_override=12, force_risk_flag=False)
        event.is_dnd = True

        illegal_plan = CandidateActionPlan(
            txn_id=event.txn_id,
            action_type=RecoveryActionType.DYNAMIC_AFA_PAYMENT_LINK,
            primary_channel=RecoveryChannel.WHATSAPP,
            scheduled_execution_time=event.timestamp,
            dlt_stream=DLTStream.PROMOTIONAL,
            compliance_audit_reasoning="Illegal DND promo link",
        )

        with self.assertRaises(ComplianceViolationError) as ctx:
            ComplianceEnforcer.validate(illegal_plan, event)
        self.assertIn("VIOLATION_TRAI_DND_PROMOTIONAL", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
