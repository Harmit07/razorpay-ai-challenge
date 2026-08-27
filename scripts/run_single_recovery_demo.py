#!/usr/bin/env python3
"""
Interactive Start-to-Finish End-to-End Recovery Simulation Demo.
Runs a single transaction through the entire AI Revenue Recovery state machine:
DETECTED -> DIAGNOSING -> ACTION_SCHEDULED -> 24h PRE-DEBIT NOTICE -> CLOCK FAST-FORWARD ->
RETRYING -> VOICE BOT ESCALATION -> PTP NEGOTIATION (PTP_FROZEN) -> PAYMENT CAPTURED (RECOVERED).
Outputs a clean, video-ready structured JSON audit trail.
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from src.models.schema import (
    TransactionFailureEvent,
    PaymentMethod,
    TransactionType,
    TransactionCategory,
    PromiseToPayRecord,
    ErrorSource,
    ErrorStep,
)
from src.classifiers.rule_classifier import RuleBasedClassifier
from src.classifiers.llm_fallback import LLMFallbackClassifier
from src.router.compliance_router import (
    ComplianceRouter,
    RecoveryActionType,
    RecoveryChannel,
)
from src.orchestrator.state_machine import (
    TransactionLifecycleFSM,
    RecoveryState,
)
from src.scheduler.simulated_clock import (
    SimulatedClockScheduler,
    TaskType,
)
from src.audit.audit_logger import ComplianceAuditLogger


def run_full_recovery_lifecycle_demo(txn_scenario: str = "INSUFFICIENT_FUNDS_WITH_VOICE_PTP"):
    base_time = datetime(2026, 8, 27, 10, 0, 0, tzinfo=timezone.utc)
    scheduler = SimulatedClockScheduler(initial_time=base_time)
    audit_logger = ComplianceAuditLogger()
    rule_classifier = RuleBasedClassifier()
    llm_parser = LLMFallbackClassifier()
    router = ComplianceRouter()

    print("\n" + "=" * 80)
    print("🎬 AI REVENUE RECOVERY AGENT — END-TO-END TRANSACTION LIFECYCLE DEMO")
    print("=" * 80)

    # 1. INGESTION (DETECTED)
    event = TransactionFailureEvent(
        txn_id="sub_live_recov_9824",
        amount=4999.00,
        method=PaymentMethod.UPI_AUTOPAY,
        error_code="BAD_REQUEST_ERROR",
        error_source=ErrorSource.CUSTOMER,
        error_step=ErrorStep.PAYMENT_AUTHORIZATION,
        error_reason="insufficient_funds",
        txn_type=TransactionType.RECURRING_SUBSCRIPTION,
        mandate_id="man_razorpay_sub_8831",
        category=TransactionCategory.STANDARD,
        customer_id="cust_rahul_sharma",
        customer_phone_masked="+91-9876****4321",
        customer_email_masked="r*****l@example.com",
        timestamp=base_time,
    )

    fsm = TransactionLifecycleFSM(event)
    print(f"📥 [STEP 1: INGESTION] Event Detected: Txn ID: {event.txn_id} | Amount: ₹{event.amount:,.2f}")
    print(f"   • Customer: {event.customer_phone_masked} | Reason: {event.error_reason}")
    print(f"   • State Machine: {fsm.current_state.value}")

    audit_logger.log_transition(
        event=event,
        from_state=RecoveryState.DETECTED,
        to_state=RecoveryState.DIAGNOSING,
        event_type="FAILURE_DETECTED",
        channel="GATEWAY_WEBHOOK",
        statutory_rule_applied="NONE",
        internal_policy_applied="TRIAGE_INGESTION_GATE",
        decision_rationale=f"Payment failure ingested: {event.error_reason}. Routing to diagnostic engine.",
        outcome_status="DIAGNOSING",
        timestamp=scheduler.current_time,
    )

    # 2. DIAGNOSIS (DIAGNOSING)
    fsm.transition_to_diagnosing(now=scheduler.current_time)
    diag = rule_classifier.classify(event)
    print(f"\n🧠 [STEP 2: DIAGNOSIS] Diagnostic Result:")
    print(f"   • Assigned Bucket : Bucket {diag.bucket_id} ({diag.bucket_name})")
    print(f"   • Confidence Score: {diag.confidence:.2f} (Clean Rule Match >= 0.85)")
    print(f"   • Action Directive: {diag.recommended_action}")
    print(f"   • State Machine   : {fsm.current_state.value}")

    # 3. COMPLIANCE ROUTING (ACTION_SCHEDULED)
    plan = router.route(event, diag)
    fsm.transition_to_action_scheduled(plan, diag, now=scheduler.current_time)
    tasks = scheduler.schedule_action_plan(plan)
    print(f"\n⚖️ [STEP 3: COMPLIANCE ROUTER] Action Plan Formulated:")
    print(f"   • Action Type           : {plan.action_type.value}")
    print(f"   • Statutory Rule Applied: {diag.statutory_rule_applied}")
    print(f"   • Mandated 24h Notice   : {plan.requires_pre_debit_notice_24h} (Dispatch: {plan.pre_debit_notice_dispatch_time.strftime('%Y-%m-%d %H:%M:%S UTC')})")
    print(f"   • Scheduled Debit Time  : {plan.scheduled_execution_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"   • DLT Template ID       : {plan.dlt_template_id} (Stream: {plan.dlt_stream.value})")
    print(f"   • Enqueued Tasks        : {len(tasks)} tasks in Priority Queue")
    print(f"   • State Machine         : {fsm.current_state.value}")

    audit_logger.log_transition(
        event=event,
        from_state=RecoveryState.DIAGNOSING,
        to_state=RecoveryState.ACTION_SCHEDULED,
        event_type="ACTION_PLAN_SCHEDULED",
        channel=plan.primary_channel.value,
        statutory_rule_applied=diag.statutory_rule_applied,
        internal_policy_applied=diag.internal_policy_applied,
        decision_rationale=plan.compliance_audit_reasoning,
        outcome_status="SCHEDULED",
        communication_type=plan.dlt_stream.value,
        afa_required=plan.afa_validation_enforced,
        afa_status="NOT_REQUIRED",
        timestamp=scheduler.current_time,
    )

    # 4. DISPATCH 24H PRE-DEBIT NOTICE
    print(f"\n📲 [STEP 4: 24H PRE-DEBIT ALERT] Fast-forwarding clock to notice dispatch time...")
    scheduler.fast_forward_to(plan.pre_debit_notice_dispatch_time)
    print(f"   • Current Virtual Time: {scheduler.current_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"   • Dispatched DLT Service Notice to {event.customer_phone_masked} with opt-out link.")

    audit_logger.log_transition(
        event=event,
        from_state=RecoveryState.ACTION_SCHEDULED,
        to_state=RecoveryState.ACTION_SCHEDULED,
        event_type="PRE_DEBIT_NOTIFICATION_DISPATCHED",
        channel="WHATSAPP_SERVICE",
        statutory_rule_applied="RBI_2026_PRE_DEBIT_24H_NOTICE_REQUIRED",
        internal_policy_applied="INTERNAL_SAFE_HOURS_08_TO_20_IST",
        decision_rationale=f"Dispatched statutory >=24h pre-debit alert prior to retry. Opt-out link included.",
        outcome_status="PRE_DEBIT_DELIVERED",
        communication_type=plan.dlt_stream.value,
        grievance_details_included=True,
        timestamp=scheduler.current_time,
    )

    # 5. FAST FORWARD CLOCK TO RETRY DEBIT TIME (48h Cooling)
    print(f"\n⏱️ [STEP 5: CLOCK FAST-FORWARD] Advancing clock past 24h statutory window to scheduled retry time...")
    scheduler.fast_forward_to(plan.scheduled_execution_time)
    print(f"   • Current Virtual Time: {scheduler.current_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    fsm.transition_to_retrying(attempt_number=1, channel=RecoveryChannel.AUTO_DEBIT_API, now=scheduler.current_time)
    print(f"   • Executing Auto-Debit Retry #1 via NPCI UPI AutoPay...")
    print(f"   • State Machine: {fsm.current_state.value}")

    audit_logger.log_transition(
        event=event,
        from_state=RecoveryState.ACTION_SCHEDULED,
        to_state=RecoveryState.RETRYING,
        event_type="AUTO_DEBIT_ATTEMPT_1_EXECUTED",
        channel="AUTO_DEBIT_API",
        statutory_rule_applied="RBI_2026_PRE_DEBIT_24H_NOTICE_REQUIRED",
        internal_policy_applied="48H_COOLING_INTERVAL_SALARY_CYCLE_SNAP",
        decision_rationale="Statutory notice window satisfied. Executed automated recurring debit attempt #1.",
        outcome_status="SOFT_FAILURE_RETRY_UNSUCCESSFUL",
        timestamp=scheduler.current_time,
    )

    # 6. ESCALATION TO AI VOICE BOT WITH PTP NEGOTIATION
    print(f"\n🎙️ [STEP 6: ESCALATION LADDER] Auto-Debit #1 soft declined (Balance still low). Escalating to AI Voice Assistant...")
    fsm.transition_to_escalated(
        channel=RecoveryChannel.VOICE_BOT,
        reason="Soft liquidity retry #1 unsuccessful. Initiating empathetic Hinglish voice recovery assistant.",
        now=scheduler.current_time,
    )
    print(f"   • Placed conversational AI voice call to {event.customer_phone_masked}")
    print(f"   • Customer Transcript: \"Main salary credit hone par September 5th ko pakka ₹4,999 pay kar dunga.\"")
    
    # LLM PTP Entity Extraction
    ptp_extracted = llm_parser.extract_ptp_entities(
        "Main salary credit hone par September 5th ko pakka ₹4999 pay kar dunga",
        reference_date=scheduler.current_time,
    )
    print(f"   • Extracted PTP Entities: Promised Date={ptp_extracted.promised_date.strftime('%Y-%m-%d')} | Amount=₹{ptp_extracted.promised_amount:,.2f} | Conf={ptp_extracted.confidence:.2f}")

    audit_logger.log_transition(
        event=event,
        from_state=RecoveryState.RETRYING,
        to_state=RecoveryState.ESCALATED,
        event_type="AI_VOICE_OUTREACH_ENGAGED",
        channel="VOICE_BOT",
        statutory_rule_applied="NONE",
        internal_policy_applied="RESPECTFUL_HINGLISH_VOICE_DUNNING",
        decision_rationale="Empathetic voice recovery bot engaged. Customer committed to Promise-to-Pay (PTP).",
        outcome_status="PTP_AGREEMENT_REACHED",
        timestamp=scheduler.current_time,
    )

    # 7. FREEZE ACTIVE DUNNING (PTP_FROZEN)
    ptp_record = PromiseToPayRecord(
        promised_date=ptp_extracted.promised_date,
        promised_amount=ptp_extracted.promised_amount,
        recorded_at=scheduler.current_time,
        grace_until=ptp_extracted.promised_date + timedelta(hours=24),
        status="ACTIVE",
    )
    fsm.transition_to_ptp_frozen(ptp_record, now=scheduler.current_time)
    scheduler.schedule_task(
        txn_id=event.txn_id,
        task_type=TaskType.PTP_GRACE_EXPIRY_CHECK,
        scheduled_time=ptp_record.grace_until,
    )
    print(f"\n❄️ [STEP 7: PTP ACTIVE FREEZE] Freezing all dunning and automated touches:")
    print(f"   • Stopping Rule Active: STOP_PTP_ACTIVE")
    print(f"   • Dunning Frozen Until: {ptp_record.grace_until.strftime('%Y-%m-%d %H:%M:%S UTC')} (Grace Window)")
    print(f"   • State Machine       : {fsm.current_state.value}")

    audit_logger.log_transition(
        event=event,
        from_state=RecoveryState.ESCALATED,
        to_state=RecoveryState.PTP_FROZEN,
        event_type="PTP_HOLD_FROZEN",
        channel="INTERNAL_PORTAL",
        statutory_rule_applied="NONE",
        internal_policy_applied="PTP_FREEZE_GRACE_WINDOW",
        decision_rationale=f"Promise-to-Pay locked for {ptp_record.promised_date.strftime('%Y-%m-%d')}. All dunning touches frozen until {ptp_record.grace_until.strftime('%Y-%m-%d')}.",
        outcome_status="FROZEN_PENDING_PTP_FULFILLMENT",
        active_ptp_date=ptp_record.promised_date,
        stop_rule_triggered="STOP_PTP_ACTIVE",
        timestamp=scheduler.current_time,
    )

    # 8. PAYMENT CAPTURED WEBHOOK (RECOVERED)
    payment_settlement_time = ptp_record.promised_date.replace(hour=11, minute=30)
    scheduler.fast_forward_to(payment_settlement_time)
    print(f"\n🎉 [STEP 8: RECOVERY RESOLUTION] Customer clears payment on promised date ({scheduler.current_time.strftime('%Y-%m-%d %H:%M:%S UTC')}):")
    print(f"   • Ingested Razorpay Webhook: payment.captured (Ref: pay_ptp_full_recovery_8812)")
    print(f"   • Settled Amount           : ₹{event.amount:,.2f}")
    
    # Cancel all future pending scheduler tasks for this transaction
    purged = scheduler.cancel_tasks_for_txn(event.txn_id, reason="STOP_PAID: Webhook confirmed payment capture")
    fsm.transition_to_recovered(payment_ref="pay_ptp_full_recovery_8812", settled_amount=event.amount, now=scheduler.current_time)
    print(f"   • Queue Purged             : {purged} pending tasks cancelled instantly (STOP_PAID)")
    print(f"   • Final Terminal State     : {fsm.current_state.value} 🚀")

    audit_logger.log_transition(
        event=event,
        from_state=RecoveryState.PTP_FROZEN,
        to_state=RecoveryState.RECOVERED,
        event_type="WEBHOOK_PAYMENT_CAPTURED",
        channel="RAZORPAY_WEBHOOK",
        statutory_rule_applied="RBI_POST_DEBIT_GRIEVANCE_RECEIPT",
        internal_policy_applied="INSTANT_QUEUE_PURGE_ON_SETTLEMENT",
        decision_rationale="Payment captured in full on PTP promise date. Dispatched confirmation receipt with grievance redressal officer details.",
        outcome_status="RECOVERED_IN_FULL",
        grievance_details_included=True,
        stop_rule_triggered="STOP_PAID",
        timestamp=scheduler.current_time,
    )

    # 9. EXPORT & DISPLAY CLEAN AUDIT TRAIL
    export_json_path = root_dir / "data" / "demo_single_txn_audit_trail.json"
    export_md_path = root_dir / "data" / "demo_single_txn_audit_report.md"
    audit_logger.export_to_json(export_json_path, indent=2)
    audit_logger.export_to_markdown_report(export_md_path, title=f"Audit Trail for Recovered Transaction {event.txn_id}")

    print("\n" + "=" * 80)
    print("📜 STRUCTURED VIDEO-READY JSON AUDIT TRAIL (EXPORTED)")
    print("=" * 80)
    with open(export_json_path, "r", encoding="utf-8") as f:
        print(f.read())

    print("\n" + "=" * 80)
    print(f"✅ Demo complete! Audit logs saved to:")
    print(f"   • JSON    : {export_json_path}")
    print(f"   • Markdown: {export_md_path}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    run_full_recovery_lifecycle_demo()
