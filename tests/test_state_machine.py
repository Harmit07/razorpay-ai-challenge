import unittest
from datetime import datetime, timezone, timedelta
from src.generators.batch_generator import BatchFailureGenerator
from src.models.schema import PromiseToPayRecord, AttemptRecord, AttemptStatus
from src.classifiers.rule_classifier import RuleBasedClassifier
from src.router.compliance_router import ComplianceRouter, RecoveryChannel, RecoveryActionType, ComplianceViolationError
from src.orchestrator.state_machine import (
    TransactionLifecycleFSM,
    RecoveryState,
    InvalidStateTransitionError,
)


class TestTransactionLifecycleFSM(unittest.TestCase):
    def setUp(self):
        self.generator = BatchFailureGenerator(seed=42)
        self.classifier = RuleBasedClassifier()
        self.router = ComplianceRouter()

    def test_happy_path_lifecycle_to_recovered(self):
        event = self.generator.generate_single_event(bucket_override=1, force_risk_flag=False)
        fsm = TransactionLifecycleFSM(event)
        
        # 1. State: DETECTED
        self.assertEqual(fsm.current_state, RecoveryState.DETECTED)

        # 2. State: DIAGNOSING
        fsm.transition_to_diagnosing()
        self.assertEqual(fsm.current_state, RecoveryState.DIAGNOSING)

        # 3. State: ACTION_SCHEDULED
        diag = self.classifier.classify(event)
        plan = self.router.route(event, diag)
        fsm.transition_to_action_scheduled(plan, diag)
        self.assertEqual(fsm.current_state, RecoveryState.ACTION_SCHEDULED)
        self.assertEqual(len(fsm.audit_trail), 1)

        # 4. State: RETRYING
        fsm.transition_to_retrying(attempt_number=1, channel=RecoveryChannel.AUTO_DEBIT_API)
        self.assertEqual(fsm.current_state, RecoveryState.RETRYING)

        # 5. State: RECOVERED (Terminal Success)
        fsm.transition_to_recovered(payment_ref="pay_settled_12345", settled_amount=event.amount)
        self.assertEqual(fsm.current_state, RecoveryState.RECOVERED)
        self.assertEqual(len(fsm.history), 4)

    def test_escalation_and_ptp_flow(self):
        event = self.generator.generate_single_event(bucket_override=1, force_risk_flag=False)
        fsm = TransactionLifecycleFSM(event)
        
        fsm.transition_to_diagnosing()
        diag = self.classifier.classify(event)
        plan = self.router.route(event, diag)
        fsm.transition_to_action_scheduled(plan, diag)
        fsm.transition_to_retrying(attempt_number=1, channel=RecoveryChannel.AUTO_DEBIT_API)

        # Attempt 1 fails -> Escalate to Voice/PTP ladder
        fsm.transition_to_escalated(
            channel=RecoveryChannel.VOICE_BOT,
            reason="Attempt #1 soft fail; initiating Hinglish voice recovery assistant with PTP negotiation.",
        )
        self.assertEqual(fsm.current_state, RecoveryState.ESCALATED)

        # Customer commits to PTP -> Transition to PTP_FROZEN
        p_date = datetime.now(timezone.utc) + timedelta(days=3)
        ptp = PromiseToPayRecord(
            promised_date=p_date,
            grace_until=p_date + timedelta(hours=24),
            promised_amount=event.amount,
            status="ACTIVE",
        )
        fsm.transition_to_ptp_frozen(ptp)
        self.assertEqual(fsm.current_state, RecoveryState.PTP_FROZEN)

        # Customer pays before grace expires -> RECOVERED
        fsm.transition_to_recovered(payment_ref="pay_ptp_cleared_99", settled_amount=event.amount)
        self.assertEqual(fsm.current_state, RecoveryState.RECOVERED)

    def test_ptp_broken_resumes_dunning(self):
        event = self.generator.generate_single_event(bucket_override=1, force_risk_flag=False)
        fsm = TransactionLifecycleFSM(event)
        
        fsm.transition_to_diagnosing()
        diag = self.classifier.classify(event)
        plan = self.router.route(event, diag)
        fsm.transition_to_action_scheduled(plan, diag)
        fsm.transition_to_retrying(attempt_number=1, channel=RecoveryChannel.AUTO_DEBIT_API)
        fsm.transition_to_escalated(channel=RecoveryChannel.VOICE_BOT, reason="Voice outreach")

        # PTP set in past that has now expired
        expired_date = datetime.now(timezone.utc) - timedelta(days=2)
        ptp = PromiseToPayRecord(
            promised_date=expired_date,
            grace_until=expired_date + timedelta(hours=24),
            promised_amount=event.amount,
            status="ACTIVE",
        )
        fsm.transition_to_ptp_frozen(ptp)

        # PTP elapsed -> resume retrying
        fsm.transition_to_retrying(attempt_number=2, channel=RecoveryChannel.AUTO_DEBIT_API)
        self.assertEqual(fsm.current_state, RecoveryState.RETRYING)

    def test_stopping_rule_terminal_unrecoverable(self):
        event = self.generator.generate_single_event(bucket_override=8, force_risk_flag=False)
        event.dispute_active = False
        fsm = TransactionLifecycleFSM(event)

        fsm.transition_to_diagnosing()
        diag = self.classifier.classify(event)
        
        # Revoked mandate halts directly to UNRECOVERABLE
        fsm.transition_to_unrecoverable(
            stopping_rule="STOP_MANDATE_REVOKED",
            reason="Customer cancelled e-mandate. Direct debits and retries purged immediately.",
        )
        self.assertEqual(fsm.current_state, RecoveryState.UNRECOVERABLE)

    def test_invalid_state_transition_throws_error(self):
        event = self.generator.generate_single_event(bucket_override=1)
        fsm = TransactionLifecycleFSM(event)

        # Illegal: Jumping from DETECTED directly to RETRYING without diagnosis
        with self.assertRaises(InvalidStateTransitionError):
            fsm.transition_to_retrying(attempt_number=1, channel=RecoveryChannel.AUTO_DEBIT_API)

        # Transition to terminal state RECOVERED
        fsm.transition_to_diagnosing()
        diag = self.classifier.classify(event)
        plan = self.router.route(event, diag)
        fsm.transition_to_action_scheduled(plan, diag)
        fsm.transition_to_recovered(payment_ref="pay_done", settled_amount=event.amount)

        # Illegal: Trying to transition out of terminal state RECOVERED
        with self.assertRaises(InvalidStateTransitionError):
            fsm.transition_to_diagnosing()

    def test_compliance_violation_in_fsm_blocked(self):
        event = self.generator.generate_single_event(bucket_override=1, force_risk_flag=False)
        event.attempt_history = [
            AttemptRecord(attempt_number=1, timestamp=datetime.now(timezone.utc), status=AttemptStatus.FAILED, reason="insufficient_funds", channel="AUTO_DEBIT"),
            AttemptRecord(attempt_number=2, timestamp=datetime.now(timezone.utc), status=AttemptStatus.FAILED, reason="insufficient_funds", channel="AUTO_DEBIT"),
            AttemptRecord(attempt_number=3, timestamp=datetime.now(timezone.utc), status=AttemptStatus.FAILED, reason="insufficient_funds", channel="AUTO_DEBIT"),
        ]
        fsm = TransactionLifecycleFSM(event)
        fsm.transition_to_diagnosing()
        
        # Transitioning to RETRYING when attempt count >= 3 is blocked by compliance invariant
        fsm.current_state = RecoveryState.ACTION_SCHEDULED
        with self.assertRaises(ComplianceViolationError):
            fsm.transition_to_retrying(attempt_number=4, channel=RecoveryChannel.AUTO_DEBIT_API)


if __name__ == "__main__":
    unittest.main()
