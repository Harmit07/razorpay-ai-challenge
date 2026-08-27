"""
Comprehensive Edge Case Test Suite for AI Revenue Recovery Router.
Tests all 10 mission-critical production edge cases from edge-cases.md.
Explicitly verifies that the router and compliance enforcer refuse unsafe actions,
throw ComplianceViolationError, and produce auditable refusal rationale.
"""

import unittest
from datetime import datetime, timezone, timedelta
from src.generators.batch_generator import BatchFailureGenerator
from src.classifiers.rule_classifier import RuleBasedClassifier, DLTStream
from src.router.compliance_router import (
    ComplianceRouter,
    ComplianceEnforcer,
    ComplianceViolationError,
    CandidateActionPlan,
    RecoveryActionType,
    RecoveryChannel,
)


class TestEdgeCaseRouterGuards(unittest.TestCase):
    def setUp(self):
        self.generator = BatchFailureGenerator(seed=42)
        self.classifier = RuleBasedClassifier()
        self.router = ComplianceRouter()
        self.edge_cases = {ec.edge_case_tag: ec for ec in self.generator.generate_deliberate_edge_cases()}

    # =========================================================================
    # EDGE-01: Zombie Retry Loop (Attempt Count >= 3)
    # =========================================================================
    def test_edge_01_zombie_retry_refusal(self):
        ec = self.edge_cases["EDGE_01_ZOMBIE_RETRY_5X"]
        diag = self.classifier.classify(ec)
        plan = self.router.route(ec, diag)

        # 1. Compliant plan must terminate gracefully
        self.assertEqual(plan.action_type, RecoveryActionType.STOP_TERMINATION)
        self.assertEqual(plan.stopping_rule, "STOP_MAX_RETRIES")
        self.assertIn("STOP_MAX_RETRIES enforced", plan.compliance_audit_reasoning)

        # 2. Programmatic Refusal Proof: If a naive system attempts 4th auto-debit retry
        unsafe_plan = CandidateActionPlan(
            txn_id=ec.txn_id,
            action_type=RecoveryActionType.AUTO_DEBIT_RETRY,
            primary_channel=RecoveryChannel.AUTO_DEBIT_API,
            scheduled_execution_time=ec.timestamp + timedelta(days=2),
            requires_pre_debit_notice_24h=True,
            pre_debit_notice_dispatch_time=ec.timestamp,
            compliance_audit_reasoning="Naive 4th attempt retry",
        )
        with self.assertRaises(ComplianceViolationError) as ctx:
            ComplianceEnforcer.validate(unsafe_plan, ec)
        self.assertIn("VIOLATION_MAX_RETRIES_EXCEEDED", str(ctx.exception))
        print(f"\n[EDGE-01 REFUSAL AUDIT LOG]: Bounded Refusal -> {ctx.exception}")

    # =========================================================================
    # EDGE-02: The ₹15,001 AFA Straddle (Standard E-Mandate > ₹15,000)
    # =========================================================================
    def test_edge_02_afa_15k_straddle_refusal(self):
        ec = self.edge_cases["EDGE_02_AFA_15K_STRADDLE"]
        diag = self.classifier.classify(ec)
        plan = self.router.route(ec, diag)

        # 1. Compliant plan must force AFA link
        self.assertEqual(plan.action_type, RecoveryActionType.DYNAMIC_AFA_PAYMENT_LINK)
        self.assertTrue(plan.afa_validation_enforced)
        self.assertEqual(plan.statutory_afa_cap, 15000.0)

        # 2. Programmatic Refusal Proof: Refuse direct auto-debit retry without OTP on ₹15,001
        unsafe_plan = CandidateActionPlan(
            txn_id=ec.txn_id,
            action_type=RecoveryActionType.AUTO_DEBIT_RETRY,
            primary_channel=RecoveryChannel.AUTO_DEBIT_API,
            scheduled_execution_time=ec.timestamp + timedelta(days=2),
            requires_pre_debit_notice_24h=True,
            pre_debit_notice_dispatch_time=ec.timestamp + timedelta(days=1),
            compliance_audit_reasoning="Naive auto-debit retry on ₹15,001",
        )
        with self.assertRaises(ComplianceViolationError) as ctx:
            ComplianceEnforcer.validate(unsafe_plan, ec)
        self.assertIn("VIOLATION_RBI_AFA_CAP_EXCEEDED", str(ctx.exception))
        print(f"[EDGE-02 REFUSAL AUDIT LOG]: Bounded Refusal -> {ctx.exception}")

    # =========================================================================
    # EDGE-03: The ₹1,00,001 Exemption Straddle (Mutual Fund SIP > ₹1,00,000)
    # =========================================================================
    def test_edge_03_afa_1L_straddle_refusal(self):
        ec = self.edge_cases["EDGE_03_AFA_1L_STRADDLE"]
        diag = self.classifier.classify(ec)
        plan = self.router.route(ec, diag)

        # 1. Compliant plan must force AFA OTP Link for SIP > ₹1,00,000
        self.assertEqual(plan.action_type, RecoveryActionType.DYNAMIC_AFA_PAYMENT_LINK)
        self.assertTrue(plan.afa_validation_enforced)
        self.assertEqual(plan.statutory_afa_cap, 100000.0)

        # 2. Programmatic Refusal Proof: Refuse direct auto-debit retry on ₹1,00,001 SIP
        unsafe_plan = CandidateActionPlan(
            txn_id=ec.txn_id,
            action_type=RecoveryActionType.AUTO_DEBIT_RETRY,
            primary_channel=RecoveryChannel.AUTO_DEBIT_API,
            scheduled_execution_time=ec.timestamp + timedelta(days=2),
            requires_pre_debit_notice_24h=True,
            pre_debit_notice_dispatch_time=ec.timestamp + timedelta(days=1),
            compliance_audit_reasoning="Naive auto-debit retry on ₹1,00,001 SIP",
        )
        with self.assertRaises(ComplianceViolationError) as ctx:
            ComplianceEnforcer.validate(unsafe_plan, ec)
        self.assertIn("VIOLATION_RBI_AFA_CAP_EXCEEDED", str(ctx.exception))
        print(f"[EDGE-03 REFUSAL AUDIT LOG]: Bounded Refusal -> {ctx.exception}")

    # =========================================================================
    # EDGE-04: Mandate Expiring Mid-Retry (Validity expires in 12 hours)
    # =========================================================================
    def test_edge_04_mandate_expiring_mid_retry_refusal(self):
        ec = self.edge_cases["EDGE_04_MANDATE_EXPIRING_MID_RETRY"]
        diag = self.classifier.classify(ec)
        plan = self.router.route(ec, diag)

        # 1. Compliant plan must dispatch instrument update link for mandate renewal
        self.assertEqual(plan.action_type, RecoveryActionType.DYNAMIC_INSTRUMENT_UPDATE_LINK)

        # 2. Programmatic Refusal Proof: Refuse scheduling auto-debit on Day T+2 after mandate expires
        unsafe_plan = CandidateActionPlan(
            txn_id=ec.txn_id,
            action_type=RecoveryActionType.AUTO_DEBIT_RETRY,
            primary_channel=RecoveryChannel.AUTO_DEBIT_API,
            scheduled_execution_time=ec.timestamp + timedelta(days=2),  # Mandate expires in 12h!
            requires_pre_debit_notice_24h=True,
            pre_debit_notice_dispatch_time=ec.timestamp,
            compliance_audit_reasoning="Naive retry on expired mandate",
        )
        with self.assertRaises(ComplianceViolationError) as ctx:
            ComplianceEnforcer.validate(unsafe_plan, ec)
        self.assertIn("VIOLATION_MANDATE_EXPIRED", str(ctx.exception))
        print(f"[EDGE-04 REFUSAL AUDIT LOG]: Bounded Refusal -> {ctx.exception}")

    # =========================================================================
    # EDGE-05: TRAI Quiet Hours Outreach Sleep (11:45 PM IST Failure)
    # =========================================================================
    def test_edge_05_quiet_hours_delayed_dispatch(self):
        ec = self.edge_cases["EDGE_05_TRAI_QUIET_HOURS_SLEEP"]
        adjusted_utc, delayed = ComplianceRouter.adjust_for_trai_quiet_hours(ec.timestamp)
        
        self.assertTrue(delayed, "Late-night outreach at 23:45 IST must be delayed for quiet hours")
        ist_time = adjusted_utc + timedelta(hours=5, minutes=30)
        self.assertEqual(ist_time.hour, 8)
        self.assertEqual(ist_time.minute, 5)

    # =========================================================================
    # EDGE-06: Promise-to-Pay (PTP) Race Condition (Active PTP Hold)
    # =========================================================================
    def test_edge_06_ptp_race_condition_refusal(self):
        ec = self.edge_cases["EDGE_06_PTP_RACE_CONDITION"]
        diag = self.classifier.classify(ec)
        plan = self.router.route(ec, diag)

        # 1. Compliant plan freezes outreach
        self.assertEqual(plan.action_type, RecoveryActionType.PTP_HOLD_FREEZE)
        self.assertEqual(plan.stopping_rule, "STOP_PTP_ACTIVE")
        self.assertEqual(plan.target_fsm_state, "PTP_FROZEN")

        # 2. Programmatic Refusal Proof: Refuse harassing customer with voice call during active PTP
        unsafe_plan = CandidateActionPlan(
            txn_id=ec.txn_id,
            action_type=RecoveryActionType.VOICE_RECOVERY_CALL,
            primary_channel=RecoveryChannel.VOICE_BOT,
            scheduled_execution_time=ec.timestamp + timedelta(hours=6),
            compliance_audit_reasoning="Naive dunning call during PTP grace",
        )
        with self.assertRaises(ComplianceViolationError) as ctx:
            ComplianceEnforcer.validate(unsafe_plan, ec)
        self.assertIn("VIOLATION_PTP_FREEZE_BREACH", str(ctx.exception))
        print(f"[EDGE-06 REFUSAL AUDIT LOG]: Bounded Refusal -> {ctx.exception}")

    # =========================================================================
    # EDGE-07: Post-Failure Mandate Cancellation (STOP_MANDATE_REVOKED)
    # =========================================================================
    def test_edge_07_mandate_revoked_refusal(self):
        ec = self.edge_cases["EDGE_07_MANDATE_REVOKED_POST_FAILURE"]
        diag = self.classifier.classify(ec)
        plan = self.router.route(ec, diag)

        # 1. Compliant plan terminates workflow
        self.assertEqual(plan.action_type, RecoveryActionType.STOP_TERMINATION)
        self.assertEqual(plan.stopping_rule, "STOP_MANDATE_REVOKED")

        # 2. Programmatic Refusal Proof: Refuse direct auto-debit on cancelled mandate
        unsafe_plan = CandidateActionPlan(
            txn_id=ec.txn_id,
            action_type=RecoveryActionType.AUTO_DEBIT_RETRY,
            primary_channel=RecoveryChannel.AUTO_DEBIT_API,
            scheduled_execution_time=ec.timestamp + timedelta(days=2),
            requires_pre_debit_notice_24h=True,
            pre_debit_notice_dispatch_time=ec.timestamp + timedelta(days=1),
            compliance_audit_reasoning="Naive retry on revoked mandate",
        )
        with self.assertRaises(ComplianceViolationError) as ctx:
            ComplianceEnforcer.validate(unsafe_plan, ec)
        self.assertIn("VIOLATION_MANDATE_REVOKED", str(ctx.exception))
        print(f"[EDGE-07 REFUSAL AUDIT LOG]: Bounded Refusal -> {ctx.exception}")

    # =========================================================================
    # EDGE-08: Active Fraud Dispute / Chargeback Straddle (STOP_DISPUTE_FRAUD)
    # =========================================================================
    def test_edge_08_fraud_dispute_lockdown_refusal(self):
        ec = self.edge_cases["EDGE_08_FRAUD_DISPUTE_STRADDLE"]
        diag = self.classifier.classify(ec)
        plan = self.router.route(ec, diag)

        # 1. Compliant plan locks down workflow to Fraud Ops
        self.assertEqual(plan.action_type, RecoveryActionType.STOP_TERMINATION)
        self.assertEqual(plan.stopping_rule, "STOP_DISPUTE_FRAUD")
        self.assertEqual(plan.target_fsm_state, "UNRECOVERABLE")

        # 2. Programmatic Refusal Proof: Refuse outbound WhatsApp dunning on disputed charge
        unsafe_plan = CandidateActionPlan(
            txn_id=ec.txn_id,
            action_type=RecoveryActionType.DYNAMIC_AFA_PAYMENT_LINK,
            primary_channel=RecoveryChannel.WHATSAPP,
            scheduled_execution_time=ec.timestamp,
            compliance_audit_reasoning="Naive dunning on active fraud dispute",
        )
        with self.assertRaises(ComplianceViolationError) as ctx:
            ComplianceEnforcer.validate(unsafe_plan, ec)
        self.assertIn("VIOLATION_CPA_DISPUTE_FREEZE", str(ctx.exception))
        print(f"[EDGE-08 REFUSAL AUDIT LOG]: Bounded Refusal -> {ctx.exception}")

    # =========================================================================
    # EDGE-09: MSMED 45-Day Statutory Invoicing Clash (Day 43)
    # =========================================================================
    def test_edge_09_msmed_45_day_clash(self):
        ec = self.edge_cases["EDGE_09_MSMED_45_DAY_CLASH"]
        diag = self.classifier.classify(ec)
        plan = self.router.route(ec, diag)

        self.assertEqual(plan.action_type, RecoveryActionType.MSMED_FINANCE_ESCALATION)
        self.assertIn("MSMED Act 2006", plan.compliance_audit_reasoning)
        self.assertLessEqual(plan.scheduled_execution_time - ec.timestamp, timedelta(days=2))

    # =========================================================================
    # EDGE-10: Unmapped High-Risk Gateway Error
    # =========================================================================
    def test_edge_10_risk_flag_quarantine(self):
        ec = self.edge_cases["EDGE_10_AMBIGUOUS_HIGH_RISK"]
        diag = self.classifier.classify(ec)
        plan = self.router.route(ec, diag)

        self.assertEqual(plan.action_type, RecoveryActionType.HUMAN_OPS_REVIEW)
        self.assertEqual(plan.target_fsm_state, "HUMAN_REVIEW")


if __name__ == "__main__":
    unittest.main()
