import json
import unittest
from pathlib import Path
from datetime import datetime, timezone, timedelta
from src.generators.batch_generator import BatchFailureGenerator
from src.classifiers.rule_classifier import RuleBasedClassifier
from src.router.compliance_router import ComplianceRouter
from src.orchestrator.state_machine import RecoveryState
from src.audit.audit_logger import ComplianceAuditLogger, AuditRecord


class TestComplianceAuditLogger(unittest.TestCase):
    def setUp(self):
        self.generator = BatchFailureGenerator(seed=42)
        self.classifier = RuleBasedClassifier()
        self.router = ComplianceRouter()
        self.logger = ComplianceAuditLogger()
        self.output_dir = Path(__file__).resolve().parent.parent / "data" / "test_audit_exports"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def test_log_state_transitions(self):
        event = self.generator.generate_single_event(bucket_override=1, force_risk_flag=False)
        diag = self.classifier.classify(event)
        plan = self.router.route(event, diag)

        # Transition 1: DETECTED -> DIAGNOSING
        r1 = self.logger.log_transition(
            event=event,
            from_state=RecoveryState.DETECTED,
            to_state=RecoveryState.DIAGNOSING,
            event_type="PAYMENT_FAILURE_INGESTED",
            channel="SYSTEM_GATEWAY",
            statutory_rule_applied="NONE",
            internal_policy_applied="RULE_ENGINE_TRIAGE",
            decision_rationale=f"Ingested failure {event.error_reason}. Routing to diagnostic engine.",
            outcome_status="DIAGNOSING",
        )
        self.assertEqual(r1.entity_id, event.txn_id)
        self.assertIn("****", r1.customer_masked)

        # Transition 2: DIAGNOSING -> ACTION_SCHEDULED
        r2 = self.logger.log_transition(
            event=event,
            from_state=RecoveryState.DIAGNOSING,
            to_state=RecoveryState.ACTION_SCHEDULED,
            event_type="AUTO_DEBIT_RETRY_SCHEDULED",
            channel="AUTO_DEBIT_API",
            statutory_rule_applied=diag.statutory_rule_applied,
            internal_policy_applied=diag.internal_policy_applied,
            decision_rationale=plan.compliance_audit_reasoning,
            outcome_status="SCHEDULED",
            afa_required=plan.afa_validation_enforced,
            afa_status="NOT_REQUIRED",
        )
        self.assertEqual(r2.statutory_rule_applied, "RBI_2026_PRE_DEBIT_24H_NOTICE_REQUIRED")

        # Transition 3: ACTION_SCHEDULED -> RECOVERED
        r3 = self.logger.log_transition(
            event=event,
            from_state=RecoveryState.ACTION_SCHEDULED,
            to_state=RecoveryState.RECOVERED,
            event_type="WEBHOOK_PAYMENT_CAPTURED",
            channel="RAZORPAY_WEBHOOK",
            statutory_rule_applied="NONE",
            internal_policy_applied="TERMINAL_RECOVERY_SUCCESS",
            decision_rationale="Payment successfully captured. Audit log sealed.",
            outcome_status="RECOVERED",
            stop_rule_triggered="STOP_PAID",
        )
        self.assertEqual(r3.stop_rule_triggered, "STOP_PAID")

        trail = self.logger.get_trail_for_entity(event.txn_id)
        self.assertEqual(len(trail), 3)

    def test_export_to_json_and_jsonl(self):
        event = self.generator.generate_single_event(bucket_override=11, force_risk_flag=False)
        diag = self.classifier.classify(event)
        plan = self.router.route(event, diag)

        self.logger.log_transition(
            event=event,
            from_state=RecoveryState.DIAGNOSING,
            to_state=RecoveryState.ACTION_SCHEDULED,
            event_type="DYNAMIC_AFA_LINK_SCHEDULED",
            channel="WHATSAPP",
            statutory_rule_applied=diag.statutory_rule_applied,
            internal_policy_applied=diag.internal_policy_applied,
            decision_rationale=plan.compliance_audit_reasoning,
            outcome_status="SCHEDULED",
            afa_required=True,
            afa_status="AFA_REQUIRED_LINK_SENT",
        )

        json_path = self.output_dir / "audit_trail.json"
        jsonl_path = self.output_dir / "audit_trail.jsonl"
        md_path = self.output_dir / "audit_report.md"

        self.logger.export_to_json(json_path)
        self.logger.export_to_jsonl(jsonl_path)
        self.logger.export_to_markdown_report(md_path)

        self.assertTrue(json_path.exists())
        self.assertTrue(jsonl_path.exists())
        self.assertTrue(md_path.exists())

        # Verify JSON content
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["entity_id"], event.txn_id)
            self.assertEqual(data[0]["afa_status"], "AFA_REQUIRED_LINK_SENT")

    def test_compute_summary_metrics(self):
        # Log multiple diverse transactions
        for b_id in [1, 2, 8, 11]:
            e = self.generator.generate_single_event(bucket_override=b_id, force_risk_flag=False)
            d = self.classifier.classify(e)
            p = self.router.route(e, d)
            self.logger.log_transition(
                event=e,
                from_state=RecoveryState.DIAGNOSING,
                to_state=RecoveryState.ACTION_SCHEDULED,
                event_type="SCHEDULED",
                channel="AUTO_DEBIT_API",
                statutory_rule_applied=d.statutory_rule_applied,
                internal_policy_applied=d.internal_policy_applied,
                decision_rationale=p.compliance_audit_reasoning,
                outcome_status="SCHEDULED",
                stop_rule_triggered=p.stopping_rule,
            )

        metrics = self.logger.compute_summary_metrics()
        self.assertEqual(metrics["total_audit_events"], 4)
        self.assertTrue(metrics["pii_redaction_verified"])
        self.assertTrue(metrics["hash_chain_verified"])
        self.assertEqual(metrics["hash_chain_verified_count"], 4)
        self.assertIn("statutory_rules_invoked", metrics)

    def test_sha256_hash_chain_integrity(self):
        """Tests that audit records are cryptographically chained and verified."""
        for idx in range(5):
            e = self.generator.generate_single_event(bucket_override=(idx % 12) + 1, force_risk_flag=False)
            d = self.classifier.classify(e)
            p = self.router.route(e, d)
            self.logger.log_transition(
                event=e,
                from_state=RecoveryState.DIAGNOSING,
                to_state=RecoveryState.ACTION_SCHEDULED,
                event_type="ACTION_SCHEDULED",
                channel="AUTO_DEBIT_API",
                statutory_rule_applied=d.statutory_rule_applied,
                internal_policy_applied=d.internal_policy_applied,
                decision_rationale=p.compliance_audit_reasoning,
                outcome_status="SCHEDULED",
            )

        is_valid, count, err = self.logger.verify_chain_integrity()
        self.assertTrue(is_valid)
        self.assertEqual(count, 5)
        self.assertIsNone(err)

    def test_sha256_tamper_detection(self):
        """Tests that any unauthorized tampering breaks the SHA-256 hash chain."""
        for idx in range(3):
            e = self.generator.generate_single_event(bucket_override=1, force_risk_flag=False)
            self.logger.log_transition(
                event=e,
                from_state=RecoveryState.DETECTED,
                to_state=RecoveryState.DIAGNOSING,
                event_type="FAILURE_INGESTED",
                channel="GATEWAY_WEBHOOK",
                statutory_rule_applied="NONE",
                internal_policy_applied="RULE_ENGINE_TRIAGE",
                decision_rationale="Original authentic record.",
                outcome_status="DIAGNOSING",
            )

        # Deliberately tamper with record 1
        self.logger._records[1].decision_rationale = "TAMPERED: Altered decision rationale without re-hashing."
        
        is_valid, bad_idx, err = self.logger.verify_chain_integrity()
        self.assertFalse(is_valid)
        self.assertEqual(bad_idx, 1)
        self.assertIn("Tampered record", err)

    def test_expected_value_economic_modeling(self):
        """Tests Expected Value (EV) calculation: EV = (p_recover * amount) - cost - annoyance."""
        e = self.generator.generate_single_event(bucket_override=1, force_risk_flag=False)
        e.amount = 10000.0
        
        # WhatsApp link: p=0.80, cost=0.15, annoyance=0.50 -> EV = 8000 - 0.65 = 7999.35
        r = self.logger.log_transition(
            event=e,
            from_state=RecoveryState.DIAGNOSING,
            to_state=RecoveryState.ACTION_SCHEDULED,
            event_type="DYNAMIC_AFA_LINK_SCHEDULED",
            channel="WHATSAPP_SERVICE",
            statutory_rule_applied="RBI_2026_PRE_DEBIT_24H_NOTICE_REQUIRED",
            internal_policy_applied="WHATSAPP_AFA_RECOVERY",
            decision_rationale="EV Optimized link dispatch.",
            outcome_status="SCHEDULED",
            p_recovery_estimate=0.80,
            channel_cost_inr=0.15,
            annoyance_penalty_inr=0.50,
            expected_value_inr=7999.35,
        )
        self.assertEqual(r.expected_value_inr, 7999.35)
        self.assertEqual(r.p_recovery_estimate, 0.80)
        self.assertEqual(r.channel_cost_inr, 0.15)


if __name__ == "__main__":
    unittest.main()
