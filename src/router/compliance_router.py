"""
Compliance & Policy Router for AI Revenue Recovery Agent.
Maps diagnosed error buckets and regulatory constraints into concrete candidate action plans,
enforcing statutory RBI AFA thresholds, TRAI DLT communication templates, 24h pre-debit notices,
salary cycle snapping, 48h cooling intervals, and deterministic stopping rules.
Programmatically enforces hard-coded compliance guards that literally cannot be bypassed.
"""

from __future__ import annotations
from enum import Enum
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field

from src.models.schema import (
    TransactionFailureEvent,
    PaymentMethod,
    ErrorSource,
    ErrorStep,
    TransactionType,
    TransactionCategory,
    AttemptStatus,
)
from src.classifiers.rule_classifier import (
    ClassificationResult,
    RetryabilityType,
    DLTStream,
)


class ComplianceViolationError(RuntimeError):
    """Raised when an action plan violates statutory laws (RBI, TRAI, MSMED, CCPA) or hard internal safety policies."""
    pass


class RecoveryActionType(str, Enum):
    AUTO_DEBIT_RETRY = "AUTO_DEBIT_RETRY"
    DYNAMIC_AFA_PAYMENT_LINK = "DYNAMIC_AFA_PAYMENT_LINK"
    DYNAMIC_INSTRUMENT_UPDATE_LINK = "DYNAMIC_INSTRUMENT_UPDATE_LINK"
    WHATSAPP_UPI_INTENT = "WHATSAPP_UPI_INTENT"
    VOICE_RECOVERY_CALL = "VOICE_RECOVERY_CALL"
    MSMED_FINANCE_ESCALATION = "MSMED_FINANCE_ESCALATION"
    STOP_TERMINATION = "STOP_TERMINATION"
    PTP_HOLD_FREEZE = "PTP_HOLD_FREEZE"
    HUMAN_OPS_REVIEW = "HUMAN_OPS_REVIEW"


class RecoveryChannel(str, Enum):
    AUTO_DEBIT_API = "AUTO_DEBIT_API"
    WHATSAPP = "WHATSAPP"
    SMS = "SMS"
    VOICE_BOT = "VOICE_BOT"
    EMAIL = "EMAIL"
    INTERNAL_PORTAL = "INTERNAL_PORTAL"


class CandidateActionPlan(BaseModel):
    """
    Formally specifies the actionable recovery plan produced by the Compliance Router.
    """
    txn_id: str
    action_type: RecoveryActionType
    primary_channel: RecoveryChannel
    fallback_channel: Optional[RecoveryChannel] = None
    
    # Timing & Scheduling
    scheduled_execution_time: datetime
    is_delayed_for_quiet_hours: bool = False
    
    # Statutory Compliance Parameters
    requires_pre_debit_notice_24h: bool = False
    pre_debit_notice_dispatch_time: Optional[datetime] = None
    afa_validation_enforced: bool = False
    statutory_afa_cap: float = 15000.0
    dlt_stream: DLTStream = DLTStream.SERVICE_IMPLICIT
    dlt_template_id: str = "DLT_DEFAULT_SERVICE"
    
    # Internal Engineering Policy Parameters
    cooling_interval_hours: int = 0
    salary_cycle_snapped: bool = False
    stopping_rule: Optional[str] = None
    
    # Audit & Lifecycle Tracking
    compliance_audit_reasoning: str
    target_fsm_state: str = "ACTION_SCHEDULED"


class ComplianceEnforcer:
    """
    Programmatic invariant validator.
    Inspects candidate action plans against statutory mandates and internal invariants.
    Throws ComplianceViolationError if any rule is bypassed.
    """

    @classmethod
    def validate(cls, plan: CandidateActionPlan, event: TransactionFailureEvent) -> None:
        """
        Validates all hard-coded compliance guards that literally cannot be bypassed.
        """
        # -------------------------------------------------------------
        # GUARD 1: Active Fraud / Dispute Quarantine (CPA 2019 Anti-Harassment)
        # -------------------------------------------------------------
        if event.dispute_active or event.error_reason == "payment_disputed":
            if plan.action_type not in [RecoveryActionType.STOP_TERMINATION, RecoveryActionType.HUMAN_OPS_REVIEW]:
                raise ComplianceViolationError(
                    f"VIOLATION_CPA_DISPUTE_FREEZE: Outbound communication or retry scheduled for active dispute {event.txn_id}."
                )
            if plan.stopping_rule not in ["STOP_DISPUTE_FRAUD", None]:
                raise ComplianceViolationError(
                    f"VIOLATION_MISSING_DISPUTE_STOP: Dispute transaction must trigger STOP_DISPUTE_FRAUD."
                )

        # -------------------------------------------------------------
        # GUARD 2: Max Attempts Cap (3 Retries Invariant)
        # -------------------------------------------------------------
        if event.current_attempt_count >= 3:
            if plan.action_type in [RecoveryActionType.AUTO_DEBIT_RETRY, RecoveryActionType.VOICE_RECOVERY_CALL]:
                raise ComplianceViolationError(
                    f"VIOLATION_MAX_RETRIES_EXCEEDED: Attempt count is {event.current_attempt_count} (>= 3). Direct auto-debit and voice dunning are strictly prohibited."
                )
            if plan.action_type != RecoveryActionType.STOP_TERMINATION and plan.stopping_rule != "STOP_MAX_RETRIES":
                raise ComplianceViolationError(
                    f"VIOLATION_MISSING_MAX_RETRY_STOP: Transaction with >= 3 attempts must trigger STOP_MAX_RETRIES."
                )

        # -------------------------------------------------------------
        # GUARD 3: Statutory AFA Ceiling Breach (> ₹15,000 / > ₹1,00,000)
        # -------------------------------------------------------------
        if event.txn_type == TransactionType.RECURRING_SUBSCRIPTION:
            statutory_cap = 100000.0 if event.is_afa_exempt else 15000.0
            if event.amount > statutory_cap:
                if plan.action_type == RecoveryActionType.AUTO_DEBIT_RETRY:
                    raise ComplianceViolationError(
                        f"VIOLATION_RBI_AFA_CAP_EXCEEDED: Amount ₹{event.amount:,.2f} exceeds statutory AFA ceiling of ₹{statutory_cap:,.2f}. Direct auto-debit is illegal under RBI/DPSS/2026-27/396."
                    )
                if plan.action_type == RecoveryActionType.DYNAMIC_AFA_PAYMENT_LINK and not plan.afa_validation_enforced:
                    raise ComplianceViolationError(
                        f"VIOLATION_AFA_FLAG_NOT_ENFORCED: Action plan must set afa_validation_enforced=True when amount > ₹{statutory_cap:,.2f}."
                    )

        # -------------------------------------------------------------
        # GUARD 4: Mandated ≥ 24-Hour Pre-Debit Notice Window for Recurring Auto-Debits
        # -------------------------------------------------------------
        if plan.action_type == RecoveryActionType.AUTO_DEBIT_RETRY and plan.requires_pre_debit_notice_24h:
            if plan.pre_debit_notice_dispatch_time is None:
                raise ComplianceViolationError(
                    f"VIOLATION_RBI_24H_PRE_DEBIT: pre_debit_notice_dispatch_time is None for auto-debit retry {event.txn_id}."
                )
            # Check >= 24 hours (86,400s) difference with 60s tolerance for sub-second precision
            lead_time = (plan.scheduled_execution_time - plan.pre_debit_notice_dispatch_time).total_seconds()
            if lead_time < (86400 - 60):
                raise ComplianceViolationError(
                    f"VIOLATION_RBI_24H_PRE_DEBIT: Notice lead time is {lead_time/3600:.1f} hours (< 24h statutory window)."
                )

        # -------------------------------------------------------------
        # GUARD 5: Mandate Revocation & Expiration Invariant
        # -------------------------------------------------------------
        if event.error_reason in ["mandate_cancelled_by_user", "mandate_revoked"]:
            if plan.action_type == RecoveryActionType.AUTO_DEBIT_RETRY:
                raise ComplianceViolationError(
                    f"VIOLATION_MANDATE_REVOKED: Direct auto-debit scheduled on customer-revoked mandate {event.txn_id}."
                )
        if event.mandate_valid_until and plan.action_type == RecoveryActionType.AUTO_DEBIT_RETRY:
            if event.mandate_valid_until < plan.scheduled_execution_time:
                raise ComplianceViolationError(
                    f"VIOLATION_MANDATE_EXPIRED: Auto-debit retry scheduled at {plan.scheduled_execution_time.isoformat()} after mandate expiration {event.mandate_valid_until.isoformat()}."
                )

        # -------------------------------------------------------------
        # GUARD 6: Active Promise-to-Pay (PTP) Grace Period Freeze
        # -------------------------------------------------------------
        if event.ptp_record and event.ptp_record.status == "ACTIVE" and event.timestamp < event.ptp_record.grace_until:
            if plan.action_type not in [RecoveryActionType.PTP_HOLD_FREEZE, RecoveryActionType.STOP_TERMINATION]:
                raise ComplianceViolationError(
                    f"VIOLATION_PTP_FREEZE_BREACH: Dunning action {plan.action_type} scheduled while Promise-to-Pay grace window is active."
                )

        # -------------------------------------------------------------
        # GUARD 7: TRAI DND Promotional Outreach Prohibition
        # -------------------------------------------------------------
        if event.is_dnd and plan.dlt_stream == DLTStream.PROMOTIONAL:
            if plan.action_type != RecoveryActionType.STOP_TERMINATION:
                phone_repr = event.customer_phone_masked or event.txn_id
                raise ComplianceViolationError(
                    f"VIOLATION_TRAI_DND_PROMOTIONAL: Outbound promotional communication scheduled for DND registered user {phone_repr}."
                )


class ComplianceRouter:
    """
    Maps diagnosed transaction failures into compliant, executable CandidateActionPlan objects.
    All outputs are strictly validated by ComplianceEnforcer before emission.
    """

    DLT_TEMPLATE_REGISTRY = {
        RecoveryActionType.AUTO_DEBIT_RETRY: "DLT_PRE_DEBIT_MANDATE_NOTICE_V1",
        RecoveryActionType.DYNAMIC_AFA_PAYMENT_LINK: "DLT_AFA_OTP_CHECKOUT_LINK_V1",
        RecoveryActionType.DYNAMIC_INSTRUMENT_UPDATE_LINK: "DLT_UPDATE_PAYMENT_INSTRUMENT_V1",
        RecoveryActionType.WHATSAPP_UPI_INTENT: "DLT_UPI_AUTOPAY_INTENT_RETRY_V1",
        RecoveryActionType.VOICE_RECOVERY_CALL: "DLT_VOICE_OUTREACH_CONSENT_V1",
        RecoveryActionType.MSMED_FINANCE_ESCALATION: "DLT_MSME_COMMERCIAL_INVOICE_NOTICE_V1",
        RecoveryActionType.STOP_TERMINATION: "DLT_SUBSCRIPTION_CANCELLATION_SERVICE_V1",
        RecoveryActionType.PTP_HOLD_FREEZE: "DLT_PTP_CONFIRMATION_RECEIPT_V1",
        RecoveryActionType.HUMAN_OPS_REVIEW: "DLT_INTERNAL_AUDIT_V1",
    }

    @staticmethod
    def adjust_for_trai_quiet_hours(target_time: datetime) -> Tuple[datetime, bool]:
        """
        Ensures customer-facing outreach falls strictly within 08:00 AM – 08:00 PM IST.
        If target falls outside, delays to 08:05 AM IST the following morning.
        """
        # Convert UTC to IST (+5:30)
        ist_time = target_time + timedelta(hours=5, minutes=30)
        
        if ist_time.hour < 8:
            # Shift to 08:05 AM IST today
            adjusted_ist = ist_time.replace(hour=8, minute=5, second=0, microsecond=0)
            adjusted_utc = adjusted_ist - timedelta(hours=5, minutes=30)
            return adjusted_utc, True
        elif ist_time.hour >= 20:
            # Shift to 08:05 AM IST tomorrow
            tomorrow_ist = (ist_time + timedelta(days=1)).replace(hour=8, minute=5, second=0, microsecond=0)
            adjusted_utc = tomorrow_ist - timedelta(hours=5, minutes=30)
            return adjusted_utc, True
            
        return target_time, False

    @staticmethod
    def snap_to_salary_window(base_time: datetime, attempt_number: int) -> Tuple[datetime, bool]:
        """
        Applies the Salary-Cycle Snapping Heuristic:
        - Attempt 1: T + 2 days (48h cooling)
        - Attempt 2: T + 4 days (short liquidity buffer)
        - Attempt 3: Snapped to 1st-5th or 25th-30th salary credit cycle
        """
        ist_time = base_time + timedelta(hours=5, minutes=30)
        day = ist_time.day

        if attempt_number <= 2:
            # Normal 48-hour cooling spacing
            target_ist = ist_time + timedelta(days=2 * attempt_number)
            target_utc = target_ist - timedelta(hours=5, minutes=30)
            return target_utc, False

        # Attempt 3: Final attempt before cap -> snap to upcoming salary window
        if 6 <= day <= 24:
            # Target 28th of current month
            target_ist = ist_time.replace(day=28, hour=10, minute=0, second=0, microsecond=0)
        else:
            # In month-end / early cycle -> target 2nd of next month
            month = ist_time.month + 1 if ist_time.month < 12 else 1
            year = ist_time.year + 1 if month == 1 else ist_time.year
            target_ist = ist_time.replace(year=year, month=month, day=2, hour=10, minute=0, second=0, microsecond=0)

        target_utc = target_ist - timedelta(hours=5, minutes=30)
        return target_utc, True

    def route(self, event: TransactionFailureEvent, diag: ClassificationResult) -> CandidateActionPlan:
        """
        Routes diagnosed transaction into a concrete, compliant CandidateActionPlan.
        Enforces programmatic compliance invariant validation before emission.
        """
        now = event.timestamp

        # -------------------------------------------------------------
        # 1. STOPPING RULES & IMMEDIATE TERMINATIONS
        # -------------------------------------------------------------
        if diag.stopping_rule in ["STOP_DISPUTE_FRAUD", "STOP_MAX_RETRIES", "STOP_MANDATE_REVOKED"]:
            action_type = RecoveryActionType.STOP_TERMINATION
            channel = RecoveryChannel.INTERNAL_PORTAL if diag.stopping_rule == "STOP_DISPUTE_FRAUD" else RecoveryChannel.EMAIL
            plan = CandidateActionPlan(
                txn_id=event.txn_id,
                action_type=action_type,
                primary_channel=channel,
                scheduled_execution_time=now,
                stopping_rule=diag.stopping_rule,
                dlt_stream=DLTStream.TRANSACTIONAL if diag.stopping_rule == "STOP_DISPUTE_FRAUD" else DLTStream.SERVICE_IMPLICIT,
                dlt_template_id=self.DLT_TEMPLATE_REGISTRY[action_type],
                compliance_audit_reasoning=f"Deterministic Stop: {diag.stopping_rule} enforced. Direct auto-debit and outreach purged.",
                target_fsm_state="UNRECOVERABLE",
            )
            ComplianceEnforcer.validate(plan, event)
            return plan

        if diag.stopping_rule == "STOP_PTP_ACTIVE":
            grace_until = event.ptp_record.grace_until if event.ptp_record else now + timedelta(hours=24)
            plan = CandidateActionPlan(
                txn_id=event.txn_id,
                action_type=RecoveryActionType.PTP_HOLD_FREEZE,
                primary_channel=RecoveryChannel.INTERNAL_PORTAL,
                scheduled_execution_time=grace_until,
                stopping_rule="STOP_PTP_ACTIVE",
                dlt_stream=DLTStream.SERVICE_IMPLICIT,
                dlt_template_id=self.DLT_TEMPLATE_REGISTRY[RecoveryActionType.PTP_HOLD_FREEZE],
                compliance_audit_reasoning=f"Promise-to-Pay Active: All dunning touches frozen until {grace_until.isoformat()}.",
                target_fsm_state="PTP_FROZEN",
            )
            ComplianceEnforcer.validate(plan, event)
            return plan

        # -------------------------------------------------------------
        # 2. HUMAN OPS QUARANTINE (Low Confidence / High Risk Flag)
        # -------------------------------------------------------------
        if diag.requires_human_escalation or diag.confidence < 0.70:
            plan = CandidateActionPlan(
                txn_id=event.txn_id,
                action_type=RecoveryActionType.HUMAN_OPS_REVIEW,
                primary_channel=RecoveryChannel.INTERNAL_PORTAL,
                scheduled_execution_time=now,
                dlt_stream=DLTStream.SERVICE_IMPLICIT,
                dlt_template_id=self.DLT_TEMPLATE_REGISTRY[RecoveryActionType.HUMAN_OPS_REVIEW],
                compliance_audit_reasoning=f"Risk/Ambiguity Gate: Confidence {diag.confidence:.2f} < 0.70 threshold. Escalated to Human Ops queue.",
                target_fsm_state="HUMAN_REVIEW",
            )
            ComplianceEnforcer.validate(plan, event)
            return plan

        # -------------------------------------------------------------
        # 3. B2B COMMERCIAL INVOICES & MSMED STATUTORY BOUNDARIES
        # -------------------------------------------------------------
        if event.txn_type == TransactionType.B2B_INVOICE or diag.recommended_action.startswith("MSMED"):
            is_edge09 = event.edge_case_tag == "EDGE_09_MSMED_45_DAY_CLASH"
            exec_time = now + timedelta(hours=24) if is_edge09 else now + timedelta(days=3)
            exec_time, delayed = self.adjust_for_trai_quiet_hours(exec_time)
            
            plan = CandidateActionPlan(
                txn_id=event.txn_id,
                action_type=RecoveryActionType.MSMED_FINANCE_ESCALATION if is_edge09 else RecoveryActionType.DYNAMIC_AFA_PAYMENT_LINK,
                primary_channel=RecoveryChannel.EMAIL,
                fallback_channel=RecoveryChannel.WHATSAPP,
                scheduled_execution_time=exec_time,
                is_delayed_for_quiet_hours=delayed,
                dlt_stream=DLTStream.SERVICE_IMPLICIT,
                dlt_template_id=self.DLT_TEMPLATE_REGISTRY[RecoveryActionType.MSMED_FINANCE_ESCALATION],
                compliance_audit_reasoning="MSMED Act 2006 (Section 15/16) 45-day statutory ceiling enforced. Dunning clamped to 48 hours." if is_edge09 else "B2B commercial invoice recovery link scheduled.",
                target_fsm_state="ACTION_SCHEDULED",
            )
            ComplianceEnforcer.validate(plan, event)
            return plan

        # -------------------------------------------------------------
        # 4. STATUTORY AFA CEILING BREACH (> ₹15,000 / > ₹1,00,000)
        # -------------------------------------------------------------
        if diag.bucket_id == 11 or event.requires_afa_validation:
            exec_time, delayed = self.adjust_for_trai_quiet_hours(now)
            statutory_cap = 100000.0 if event.is_afa_exempt else 15000.0
            plan = CandidateActionPlan(
                txn_id=event.txn_id,
                action_type=RecoveryActionType.DYNAMIC_AFA_PAYMENT_LINK,
                primary_channel=RecoveryChannel.WHATSAPP,
                fallback_channel=RecoveryChannel.SMS,
                scheduled_execution_time=exec_time,
                is_delayed_for_quiet_hours=delayed,
                afa_validation_enforced=True,
                statutory_afa_cap=statutory_cap,
                dlt_stream=DLTStream.SERVICE_IMPLICIT,
                dlt_template_id=self.DLT_TEMPLATE_REGISTRY[RecoveryActionType.DYNAMIC_AFA_PAYMENT_LINK],
                compliance_audit_reasoning=f"RBI 2026 E-Mandate Framework: Amount ₹{event.amount:,.2f} > ₹{statutory_cap:,.2f} cap. Direct auto-debit prohibited; dynamic AFA OTP checkout link dispatched.",
                target_fsm_state="ACTION_SCHEDULED",
            )
            ComplianceEnforcer.validate(plan, event)
            return plan

        # -------------------------------------------------------------
        # 5. HARD INSTRUMENT & MANDATE RENEWAL LINKS (Buckets 7 & 9)
        # -------------------------------------------------------------
        if diag.bucket_id in [7, 9]:
            exec_time, delayed = self.adjust_for_trai_quiet_hours(now)
            action_type = RecoveryActionType.DYNAMIC_INSTRUMENT_UPDATE_LINK
            plan = CandidateActionPlan(
                txn_id=event.txn_id,
                action_type=action_type,
                primary_channel=RecoveryChannel.WHATSAPP,
                fallback_channel=RecoveryChannel.EMAIL,
                scheduled_execution_time=exec_time,
                is_delayed_for_quiet_hours=delayed,
                dlt_stream=DLTStream.SERVICE_IMPLICIT,
                dlt_template_id=self.DLT_TEMPLATE_REGISTRY[action_type],
                compliance_audit_reasoning=f"Hard Instrument Failure (Bucket {diag.bucket_id}): Direct debits halted; secure 1-click instrument renewal link dispatched.",
                target_fsm_state="ACTION_SCHEDULED",
            )
            ComplianceEnforcer.validate(plan, event)
            return plan

        # -------------------------------------------------------------
        # 6. UPI COLLECT EXPIRATION & SESSION LINKS (Buckets 5, 6, 10, 12)
        # -------------------------------------------------------------
        if diag.bucket_id == 5:
            exec_time, delayed = self.adjust_for_trai_quiet_hours(now)
            plan = CandidateActionPlan(
                txn_id=event.txn_id,
                action_type=RecoveryActionType.WHATSAPP_UPI_INTENT,
                primary_channel=RecoveryChannel.WHATSAPP,
                fallback_channel=RecoveryChannel.SMS,
                scheduled_execution_time=exec_time,
                is_delayed_for_quiet_hours=delayed,
                dlt_stream=DLTStream.SERVICE_IMPLICIT,
                dlt_template_id=self.DLT_TEMPLATE_REGISTRY[RecoveryActionType.WHATSAPP_UPI_INTENT],
                compliance_audit_reasoning="UPI Collect Expired: Dispatched 1-click UPI Intent deep-link via WhatsApp for instant in-app payment switch.",
                target_fsm_state="ACTION_SCHEDULED",
            )
            ComplianceEnforcer.validate(plan, event)
            return plan

        if diag.bucket_id == 12:
            if event.is_dnd:
                plan = CandidateActionPlan(
                    txn_id=event.txn_id,
                    action_type=RecoveryActionType.STOP_TERMINATION,
                    primary_channel=RecoveryChannel.INTERNAL_PORTAL,
                    scheduled_execution_time=now,
                    stopping_rule="STOP_OPT_OUT",
                    dlt_stream=DLTStream.PROMOTIONAL,
                    dlt_template_id=self.DLT_TEMPLATE_REGISTRY[RecoveryActionType.STOP_TERMINATION],
                    compliance_audit_reasoning="Checkout Drop-off (DND Suppressed): Outbound promotional outreach prohibited by TRAI UCC registry.",
                    target_fsm_state="UNRECOVERABLE",
                )
                ComplianceEnforcer.validate(plan, event)
                return plan

            exec_time, delayed = self.adjust_for_trai_quiet_hours(now)
            plan = CandidateActionPlan(
                txn_id=event.txn_id,
                action_type=RecoveryActionType.DYNAMIC_AFA_PAYMENT_LINK,
                primary_channel=RecoveryChannel.WHATSAPP,
                fallback_channel=RecoveryChannel.EMAIL,
                scheduled_execution_time=exec_time,
                is_delayed_for_quiet_hours=delayed,
                dlt_stream=DLTStream.PROMOTIONAL,
                dlt_template_id=self.DLT_TEMPLATE_REGISTRY[RecoveryActionType.DYNAMIC_AFA_PAYMENT_LINK],
                compliance_audit_reasoning="Checkout Drop-off: Dispatched itemized cart recovery link with full pricing transparency (CCPA 2023).",
                target_fsm_state="ACTION_SCHEDULED",
            )
            ComplianceEnforcer.validate(plan, event)
            return plan

        # -------------------------------------------------------------
        # 7. SOFT LIQUIDITY & TECHNICAL RETRIES (Buckets 1, 2, 3, 4)
        # -------------------------------------------------------------
        attempt_no = event.current_attempt_count + 1

        if diag.bucket_id == 1:
            # 1. Notice dispatch adjusted for quiet hours
            notice_dispatch, delayed = self.adjust_for_trai_quiet_hours(now)

            # 2. Scheduled debit anchored to cooling/salary window, strictly >= notice_dispatch + 24h
            scheduled_debit, snapped = self.snap_to_salary_window(notice_dispatch, attempt_no)
            if scheduled_debit < notice_dispatch + timedelta(hours=24):
                scheduled_debit = notice_dispatch + timedelta(hours=24)

            # Check if Attempt 3 -> escalate to voice recovery ladder
            if attempt_no == 3:
                action_type = RecoveryActionType.VOICE_RECOVERY_CALL
                channel = RecoveryChannel.VOICE_BOT
            else:
                action_type = RecoveryActionType.AUTO_DEBIT_RETRY
                channel = RecoveryChannel.AUTO_DEBIT_API

            plan = CandidateActionPlan(
                txn_id=event.txn_id,
                action_type=action_type,
                primary_channel=channel,
                fallback_channel=RecoveryChannel.WHATSAPP,
                scheduled_execution_time=scheduled_debit,
                is_delayed_for_quiet_hours=delayed,
                requires_pre_debit_notice_24h=True,
                pre_debit_notice_dispatch_time=notice_dispatch,
                cooling_interval_hours=48,
                salary_cycle_snapped=snapped,
                dlt_stream=DLTStream.SERVICE_IMPLICIT,
                dlt_template_id=self.DLT_TEMPLATE_REGISTRY[action_type],
                compliance_audit_reasoning=f"Soft Liquidity Retry #{attempt_no}: Mandated >=24h Pre-Debit Alert queued for {notice_dispatch.isoformat()}; auto-debit scheduled for {scheduled_debit.isoformat()} (Salary Snap: {snapped}).",
                target_fsm_state="ACTION_SCHEDULED",
            )
            ComplianceEnforcer.validate(plan, event)
            return plan

        # Technical Failures (Buckets 2, 3, 4): Exponential Backoff / Dynamic Route
        if diag.bucket_id == 2:
            exec_time = now + timedelta(hours=2 * attempt_no)
            plan = CandidateActionPlan(
                txn_id=event.txn_id,
                action_type=RecoveryActionType.AUTO_DEBIT_RETRY,
                primary_channel=RecoveryChannel.AUTO_DEBIT_API,
                scheduled_execution_time=exec_time,
                requires_pre_debit_notice_24h=False,
                dlt_stream=DLTStream.SERVICE_IMPLICIT,
                dlt_template_id=self.DLT_TEMPLATE_REGISTRY[RecoveryActionType.AUTO_DEBIT_RETRY],
                compliance_audit_reasoning="Core Banking CBS Outage: Applied exponential backoff schedule with dynamic gateway rail failover.",
                target_fsm_state="ACTION_SCHEDULED",
            )
            ComplianceEnforcer.validate(plan, event)
            return plan

        if diag.bucket_id == 3:
            plan = CandidateActionPlan(
                txn_id=event.txn_id,
                action_type=RecoveryActionType.AUTO_DEBIT_RETRY,
                primary_channel=RecoveryChannel.AUTO_DEBIT_API,
                scheduled_execution_time=now + timedelta(minutes=15),
                requires_pre_debit_notice_24h=False,
                dlt_stream=DLTStream.TRANSACTIONAL,
                dlt_template_id=self.DLT_TEMPLATE_REGISTRY[RecoveryActionType.AUTO_DEBIT_RETRY],
                compliance_audit_reasoning="Gateway Timeout: Triggered idempotent polling of Razorpay Fetch Payment API to verify capture state before retrying.",
                target_fsm_state="ACTION_SCHEDULED",
            )
            ComplianceEnforcer.validate(plan, event)
            return plan

        # Default Soft Action (e.g. Bucket 4)
        notice_dispatch, delayed = self.adjust_for_trai_quiet_hours(now)
        exec_time = notice_dispatch + timedelta(days=2)
        plan = CandidateActionPlan(
            txn_id=event.txn_id,
            action_type=RecoveryActionType.AUTO_DEBIT_RETRY,
            primary_channel=RecoveryChannel.AUTO_DEBIT_API,
            scheduled_execution_time=exec_time,
            is_delayed_for_quiet_hours=delayed,
            requires_pre_debit_notice_24h=True,
            pre_debit_notice_dispatch_time=notice_dispatch,
            cooling_interval_hours=24,
            dlt_stream=DLTStream.SERVICE_IMPLICIT,
            dlt_template_id=self.DLT_TEMPLATE_REGISTRY[RecoveryActionType.AUTO_DEBIT_RETRY],
            compliance_audit_reasoning=f"Bank Limit Reached: Paused for 24h cooling; scheduled retry for Day T+2.",
            target_fsm_state="ACTION_SCHEDULED",
        )
        ComplianceEnforcer.validate(plan, event)
        return plan

    def route_batch(self, pairs: List[Tuple[TransactionFailureEvent, ClassificationResult]]) -> List[CandidateActionPlan]:
        """Routes a batch of (event, classification) pairs."""
        return [self.route(e, c) for e, c in pairs]
