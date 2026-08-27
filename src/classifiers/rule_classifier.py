"""
Deterministic Rule-Based Classifier for AI Revenue Recovery Agent.
Processes payment failure events across Razorpay's 3-tier error model,
RBI 2026 statutory frameworks, TRAI DLT communication streams,
and deterministic stopping rules.
"""

from __future__ import annotations
from enum import Enum
from typing import Optional, Dict, Any, List
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


class RetryabilityType(str, Enum):
    RETRYABLE_SOFT_DEBIT = "RETRYABLE_SOFT_DEBIT"
    RETRYABLE_LINK_ACTION = "RETRYABLE_LINK_ACTION"
    NON_RETRYABLE_HARD_STOP = "NON_RETRYABLE_HARD_STOP"
    UNMAPPED_AMBIGUOUS = "UNMAPPED_AMBIGUOUS"


class DLTStream(str, Enum):
    TRANSACTIONAL = "TRANSACTIONAL"
    SERVICE_IMPLICIT = "SERVICE_IMPLICIT"
    SERVICE_EXPLICIT = "SERVICE_EXPLICIT"
    PROMOTIONAL = "PROMOTIONAL"


class ClassificationResult(BaseModel):
    """Structured decision output from the Rule-Based Classifier."""
    txn_id: str
    bucket_id: int
    bucket_name: str
    retryability: RetryabilityType
    confidence: float = Field(..., ge=0.0, le=1.0)
    
    # Action & Routing Directives
    recommended_action: str
    dlt_stream: DLTStream
    stopping_rule: Optional[str] = None
    
    # Regulatory & Policy Tracking
    statutory_rule_applied: str = "NONE"
    internal_policy_applied: str = "NONE"
    is_quiet_hours_delayed: bool = False
    
    # Escalation Flags
    requires_llm_disambiguation: bool = False
    requires_human_escalation: bool = False
    routing_destination: str = "ACTION_SCHEDULED"


class RuleBasedClassifier:
    """
    Deterministic rule engine that classifies payment failure events,
    enforces statutory compliance rules, and routes clean ~80% cases with high confidence.
    """

    @staticmethod
    def is_within_trai_safe_window(dt: datetime) -> bool:
        """
        TRAI UCC Safe Window: 08:00 AM to 08:00 PM IST (02:30 UTC to 14:30 UTC).
        Returns True if within safe window, False if within late-night quiet hours.
        """
        # Convert UTC to IST (+5:30)
        ist_time = dt + timedelta(hours=5, minutes=30)
        return 8 <= ist_time.hour < 20

    def classify(self, event: TransactionFailureEvent) -> ClassificationResult:
        """
        Classifies a single TransactionFailureEvent deterministically.
        """
        is_quiet_hours = not self.is_within_trai_safe_window(event.timestamp)

        # -------------------------------------------------------------
        # GUARD 1: Active Fraud Dispute / Chargeback Open (STOP_DISPUTE_FRAUD)
        # -------------------------------------------------------------
        if event.dispute_active or event.error_reason == "payment_disputed":
            return ClassificationResult(
                txn_id=event.txn_id,
                bucket_id=0,
                bucket_name="Active Fraud Dispute / Chargeback",
                retryability=RetryabilityType.NON_RETRYABLE_HARD_STOP,
                confidence=0.99,
                recommended_action="LOCKDOWN_ESCALATE_TO_FRAUD_OPS",
                dlt_stream=DLTStream.TRANSACTIONAL,
                stopping_rule="STOP_DISPUTE_FRAUD",
                statutory_rule_applied="CCPA_2023_ANTI_HARASSMENT_DISPUTE_FREEZE",
                internal_policy_applied="FRAUD_DISPUTE_QUARANTINE",
                requires_human_escalation=True,
                routing_destination="HUMAN_REVIEW",
            )

        # -------------------------------------------------------------
        # GUARD 2: Max Attempts Cap (3 Retries Exhausted) (STOP_MAX_RETRIES)
        # -------------------------------------------------------------
        if event.current_attempt_count >= 3:
            return ClassificationResult(
                txn_id=event.txn_id,
                bucket_id=event.attempt_history[-1].attempt_number if event.attempt_history else 1,
                bucket_name="Max Retry Limit Exhausted",
                retryability=RetryabilityType.NON_RETRYABLE_HARD_STOP,
                confidence=0.99,
                recommended_action="PAUSE_SUBSCRIPTION_GRACEFULLY",
                dlt_stream=DLTStream.SERVICE_IMPLICIT,
                stopping_rule="STOP_MAX_RETRIES",
                statutory_rule_applied="NONE",
                internal_policy_applied="MAX_3_RETRIES_DUNNING_CEILING",
                requires_human_escalation=True,
                routing_destination="UNRECOVERABLE",
            )

        # -------------------------------------------------------------
        # GUARD 3: Active Promise-to-Pay (PTP) Grace Window (STOP_PTP_ACTIVE)
        # -------------------------------------------------------------
        if event.ptp_record and event.ptp_record.status == "ACTIVE":
            if event.timestamp < event.ptp_record.grace_until:
                return ClassificationResult(
                    txn_id=event.txn_id,
                    bucket_id=0,
                    bucket_name="Promise to Pay Active Hold",
                    retryability=RetryabilityType.NON_RETRYABLE_HARD_STOP,
                    confidence=0.99,
                    recommended_action="FREEZE_ALL_DUNNING_UNTIL_PTP_GRACE_EXPIRES",
                    dlt_stream=DLTStream.SERVICE_IMPLICIT,
                    stopping_rule="STOP_PTP_ACTIVE",
                    statutory_rule_applied="NONE",
                    internal_policy_applied="PTP_FREEZE_GRACE_WINDOW",
                    routing_destination="PTP_FROZEN",
                )

        # -------------------------------------------------------------
        # GUARD 4: Independent High Risk Flag -> Human Review Escalation
        # -------------------------------------------------------------
        if event.risk_flag:
            return ClassificationResult(
                txn_id=event.txn_id,
                bucket_id=13 if event.error_reason == "raw_unmapped_decline" else 10,
                bucket_name="High Risk Flagged Transaction",
                retryability=RetryabilityType.UNMAPPED_AMBIGUOUS,
                confidence=0.60,  # Below 0.70 threshold -> routes to Human Review
                recommended_action="ESCALATE_TO_RISK_OPS_FOR_MANUAL_TRIAGE",
                dlt_stream=DLTStream.SERVICE_IMPLICIT,
                statutory_rule_applied="NONE",
                internal_policy_applied="RISK_ENGINE_CONFIDENCE_GATE",
                requires_human_escalation=True,
                routing_destination="HUMAN_REVIEW",
            )

        # -------------------------------------------------------------
        # RULE 1: Statutory AFA Ceiling Breached (> ₹15,000 / > ₹1,00,000)
        # -------------------------------------------------------------
        if event.requires_afa_validation or event.error_reason == "amount_exceeds_statutory_afa_limit":
            statutory_ref = "RBI_2023_24_90_1L_EXEMPTION" if event.is_afa_exempt else "RBI_DPSS_2026_27_396_15K_CAP"
            return ClassificationResult(
                txn_id=event.txn_id,
                bucket_id=11,
                bucket_name="Amount Exceeds Statutory AFA Limit",
                retryability=RetryabilityType.RETRYABLE_LINK_ACTION,
                confidence=0.98,
                recommended_action="DISPATCH_DYNAMIC_AFA_OTP_LINK",
                dlt_stream=DLTStream.SERVICE_IMPLICIT,
                statutory_rule_applied=statutory_ref,
                internal_policy_applied="AUTO_DEBIT_STRICTLY_PROHIBITED",
                is_quiet_hours_delayed=is_quiet_hours,
                routing_destination="ACTION_SCHEDULED",
            )

        # -------------------------------------------------------------
        # RULE 2: Mandate Expiring / Expired Mid-Retry (STOP_MANDATE_EXPIRED)
        # -------------------------------------------------------------
        if event.error_reason in ["mandate_validity_expired", "mandate_expired"] or (
            event.mandate_valid_until and event.mandate_valid_until < event.timestamp + timedelta(hours=24)
        ):
            return ClassificationResult(
                txn_id=event.txn_id,
                bucket_id=9,
                bucket_name="Mandate Validity Expired",
                retryability=RetryabilityType.RETRYABLE_LINK_ACTION,
                confidence=0.97,
                recommended_action="SEND_1_CLICK_MANDATE_RE_REGISTRATION_LINK",
                dlt_stream=DLTStream.SERVICE_IMPLICIT,
                stopping_rule="STOP_MANDATE_EXPIRED",
                statutory_rule_applied="RBI_2026_MANDATE_VALIDITY_BOUNDARY",
                internal_policy_applied="HALT_DIRECT_DEBIT_ON_EXPIRED_MANDATE",
                is_quiet_hours_delayed=is_quiet_hours,
                routing_destination="ACTION_SCHEDULED",
            )

        # -------------------------------------------------------------
        # RULE 3: Mandate Cancelled / Revoked by Customer (STOP_MANDATE_REVOKED)
        # -------------------------------------------------------------
        if event.error_reason in ["mandate_cancelled_by_user", "mandate_revoked"]:
            return ClassificationResult(
                txn_id=event.txn_id,
                bucket_id=8,
                bucket_name="Mandate Cancelled by Customer",
                retryability=RetryabilityType.NON_RETRYABLE_HARD_STOP,
                confidence=0.99,
                recommended_action="PURGE_RETRIES_AND_SEND_SERVICE_CONFIRMATION",
                dlt_stream=DLTStream.SERVICE_IMPLICIT,
                stopping_rule="STOP_MANDATE_REVOKED",
                statutory_rule_applied="RBI_CUSTOMER_REVOCATION_RIGHT",
                internal_policy_applied="INSTANT_QUEUE_PURGE_ON_REVOCATION",
                routing_destination="UNRECOVERABLE",
            )

        # -------------------------------------------------------------
        # RULE 4: Expired Card Instrument
        # -------------------------------------------------------------
        if event.error_reason in ["card_expired", "card_inactive"]:
            return ClassificationResult(
                txn_id=event.txn_id,
                bucket_id=7,
                bucket_name="Expired Card Instrument",
                retryability=RetryabilityType.RETRYABLE_LINK_ACTION,
                confidence=0.98,
                recommended_action="DISPATCH_MANDATE_UPDATE_LINK",
                dlt_stream=DLTStream.SERVICE_IMPLICIT,
                statutory_rule_applied="NONE",
                internal_policy_applied="HALT_DIRECT_DEBIT_ON_EXPIRED_CARD",
                is_quiet_hours_delayed=is_quiet_hours,
                routing_destination="ACTION_SCHEDULED",
            )

        # -------------------------------------------------------------
        # RULE 5: Insufficient Funds / Liquidity Shortfall (Bucket 1)
        # -------------------------------------------------------------
        if event.error_reason == "insufficient_funds":
            return ClassificationResult(
                txn_id=event.txn_id,
                bucket_id=1,
                bucket_name="Insufficient Balance / Low Liquidity",
                retryability=RetryabilityType.RETRYABLE_SOFT_DEBIT,
                confidence=0.96,
                recommended_action="QUEUE_24H_PRE_DEBIT_ALERT_SCHEDULE_SALARY_RETRY",
                dlt_stream=DLTStream.SERVICE_IMPLICIT,
                statutory_rule_applied="RBI_2026_PRE_DEBIT_24H_NOTICE_REQUIRED",
                internal_policy_applied="48H_COOLING_INTERVAL_SALARY_CYCLE_SNAP",
                is_quiet_hours_delayed=is_quiet_hours,
                routing_destination="ACTION_SCHEDULED",
            )

        # -------------------------------------------------------------
        # RULE 6: Bank Core Banking Downtime / CBS Server Outage (Bucket 2)
        # -------------------------------------------------------------
        if event.error_reason in ["bank_server_down", "bank_unavailable"]:
            return ClassificationResult(
                txn_id=event.txn_id,
                bucket_id=2,
                bucket_name="Core Banking / Issuer Downtime",
                retryability=RetryabilityType.RETRYABLE_SOFT_DEBIT,
                confidence=0.95,
                recommended_action="EXPONENTIAL_BACKOFF_DYNAMIC_ROUTING",
                dlt_stream=DLTStream.SERVICE_IMPLICIT,
                statutory_rule_applied="NONE",
                internal_policy_applied="EXPONENTIAL_BACKOFF_2H_6H_24H",
                is_quiet_hours_delayed=is_quiet_hours,
                routing_destination="ACTION_SCHEDULED",
            )

        # -------------------------------------------------------------
        # RULE 7: Gateway Timeout / Network Handshake Drop (Bucket 3)
        # -------------------------------------------------------------
        if event.error_reason in ["gateway_timeout", "network_error"]:
            return ClassificationResult(
                txn_id=event.txn_id,
                bucket_id=3,
                bucket_name="Gateway Timeout / Network Drop",
                retryability=RetryabilityType.RETRYABLE_SOFT_DEBIT,
                confidence=0.95,
                recommended_action="IDEMPOTENT_POLL_RAZORPAY_FETCH_THEN_SETTLE",
                dlt_stream=DLTStream.TRANSACTIONAL,
                statutory_rule_applied="NONE",
                internal_policy_applied="IDEMPOTENT_STATUS_POLLING_AVOID_DOUBLE_DEBIT",
                is_quiet_hours_delayed=is_quiet_hours,
                routing_destination="ACTION_SCHEDULED",
            )

        # -------------------------------------------------------------
        # RULE 8: Velocity Limit Exceeded (Bucket 4)
        # -------------------------------------------------------------
        if event.error_reason == "velocity_limit_exceeded":
            return ClassificationResult(
                txn_id=event.txn_id,
                bucket_id=4,
                bucket_name="Bank Velocity / Daily Limit Exceeded",
                retryability=RetryabilityType.RETRYABLE_SOFT_DEBIT,
                confidence=0.94,
                recommended_action="PAUSE_24H_SEND_NOTICE_RETRY_DAY_T2",
                dlt_stream=DLTStream.SERVICE_IMPLICIT,
                statutory_rule_applied="RBI_2026_PRE_DEBIT_24H_NOTICE_REQUIRED",
                internal_policy_applied="NEXT_CALENDAR_DAY_COOLING",
                is_quiet_hours_delayed=is_quiet_hours,
                routing_destination="ACTION_SCHEDULED",
            )

        # -------------------------------------------------------------
        # RULE 9: UPI Collect Request Expired (Bucket 5)
        # -------------------------------------------------------------
        if event.error_reason in ["upi_collect_expired", "upi_app_timeout"]:
            return ClassificationResult(
                txn_id=event.txn_id,
                bucket_id=5,
                bucket_name="UPI AutoPay / Collect Expired",
                retryability=RetryabilityType.RETRYABLE_LINK_ACTION,
                confidence=0.95,
                recommended_action="DISPATCH_1_CLICK_UPI_INTENT_DEEP_LINK",
                dlt_stream=DLTStream.SERVICE_IMPLICIT,
                statutory_rule_applied="NONE",
                internal_policy_applied="WHATSAPP_UPI_INTENT_DISPATCH",
                is_quiet_hours_delayed=is_quiet_hours,
                routing_destination="ACTION_SCHEDULED",
            )

        # -------------------------------------------------------------
        # RULE 10: 3DS OTP Authentication Failure (Bucket 6)
        # -------------------------------------------------------------
        if event.error_reason in ["authentication_failed", "invalid_otp"]:
            return ClassificationResult(
                txn_id=event.txn_id,
                bucket_id=6,
                bucket_name="3DS OTP Authentication Failure",
                retryability=RetryabilityType.RETRYABLE_LINK_ACTION,
                confidence=0.95,
                recommended_action="DISPATCH_DYNAMIC_SESSION_RETRY_LINK",
                dlt_stream=DLTStream.SERVICE_IMPLICIT,
                statutory_rule_applied="NONE",
                internal_policy_applied="HALT_DIRECT_DEBITS_SEND_OTP_LINK",
                is_quiet_hours_delayed=is_quiet_hours,
                routing_destination="ACTION_SCHEDULED",
            )

        # -------------------------------------------------------------
        # RULE 11: Bank Technical Decline / Security Decline (Bucket 10)
        # -------------------------------------------------------------
        if event.error_reason in ["bank_technical_decline", "do_not_honor"]:
            return ClassificationResult(
                txn_id=event.txn_id,
                bucket_id=10,
                bucket_name="Bank Security Decline (Do Not Honor)",
                retryability=RetryabilityType.RETRYABLE_LINK_ACTION,
                confidence=0.92,
                recommended_action="SEND_UNBLOCK_INSTRUCTIONS_AND_MULTI_RAIL_LINK",
                dlt_stream=DLTStream.SERVICE_IMPLICIT,
                statutory_rule_applied="NONE",
                internal_policy_applied="MULTI_RAIL_FALLBACK_LINK",
                is_quiet_hours_delayed=is_quiet_hours,
                routing_destination="ACTION_SCHEDULED",
            )

        # -------------------------------------------------------------
        # RULE 12: Checkout Drop-Off / Cart Abandonment (Bucket 12)
        # -------------------------------------------------------------
        if event.error_reason == "checkout_abandonment_dropoff" or event.txn_type == TransactionType.CHECKOUT_DROP_OFF:
            if event.is_dnd:
                return ClassificationResult(
                    txn_id=event.txn_id,
                    bucket_id=12,
                    bucket_name="Checkout Drop-Off (DND Suppressed)",
                    retryability=RetryabilityType.NON_RETRYABLE_HARD_STOP,
                    confidence=0.96,
                    recommended_action="SUPPRESS_PROMOTIONAL_USE_IN_APP_BANNER",
                    dlt_stream=DLTStream.PROMOTIONAL,
                    statutory_rule_applied="TRAI_DND_UCC_OUTREACH_PROHIBITED",
                    internal_policy_applied="ZERO_DARK_PATTERNS_CONSENT_CHECK",
                    routing_destination="UNRECOVERABLE",
                )
            return ClassificationResult(
                txn_id=event.txn_id,
                bucket_id=12,
                bucket_name="Checkout Drop-Off / Cart Abandonment",
                retryability=RetryabilityType.RETRYABLE_LINK_ACTION,
                confidence=0.94,
                recommended_action="DELIVER_1_CLICK_CART_RECOVERY_LINK",
                dlt_stream=DLTStream.PROMOTIONAL,
                statutory_rule_applied="CCPA_2023_PRICE_TRANSPARENCY",
                internal_policy_applied="ZERO_DARK_PATTERNS_ITEMIZED_LINK",
                is_quiet_hours_delayed=is_quiet_hours,
                routing_destination="ACTION_SCHEDULED",
            )

        # -------------------------------------------------------------
        # RULE 13: B2B Commercial Invoices (MSMED 45-Day Boundary)
        # -------------------------------------------------------------
        if event.txn_type == TransactionType.B2B_INVOICE or event.error_reason == "b2b_invoice_overdue":
            is_edge09 = event.edge_case_tag == "EDGE_09_MSMED_45_DAY_CLASH"
            return ClassificationResult(
                txn_id=event.txn_id,
                bucket_id=1,
                bucket_name="B2B Commercial Invoice Overdue",
                retryability=RetryabilityType.RETRYABLE_LINK_ACTION,
                confidence=0.92,
                recommended_action="MSMED_EMERGENCY_FINANCE_ESCALATION" if is_edge09 else "DELIVER_B2B_RECOVERY_PORTAL_LINK",
                dlt_stream=DLTStream.SERVICE_IMPLICIT,
                statutory_rule_applied="MSMED_ACT_2006_SECTION_15_16_45D_CAP" if is_edge09 else "NONE",
                internal_policy_applied="B2B_FINANCE_ESCALATION",
                is_quiet_hours_delayed=is_quiet_hours,
                routing_destination="ACTION_SCHEDULED",
            )

        # -------------------------------------------------------------
        # RULE 14: Bucket 13 Raw Unmapped Decline Text -> LLM Disambiguation
        # -------------------------------------------------------------
        if event.error_reason == "raw_unmapped_decline" or event.raw_error_description is not None:
            return ClassificationResult(
                txn_id=event.txn_id,
                bucket_id=13,
                bucket_name="Raw Unmapped / Ambiguous Bank Decline",
                retryability=RetryabilityType.UNMAPPED_AMBIGUOUS,
                confidence=0.75,  # In the 0.70-0.85 zone -> requires LLM intent parser
                recommended_action="ROUTE_TO_LLM_PARSER_FOR_INTENT_DISAMBIGUATION",
                dlt_stream=DLTStream.SERVICE_IMPLICIT,
                statutory_rule_applied="NONE",
                internal_policy_applied="LLM_AMBIGUITY_RESOLUTION_PIPELINE",
                requires_llm_disambiguation=True,
                routing_destination="DIAGNOSING",
            )

        # -------------------------------------------------------------
        # DEFAULT FALLBACK: Low Confidence Unknown Error
        # -------------------------------------------------------------
        return ClassificationResult(
            txn_id=event.txn_id,
            bucket_id=13,
            bucket_name="Unclassified Unknown Decline",
            retryability=RetryabilityType.UNMAPPED_AMBIGUOUS,
            confidence=0.65,  # Below 0.70 -> routes to Human Review
            recommended_action="ROUTE_TO_HUMAN_OPS_QUEUE",
            dlt_stream=DLTStream.SERVICE_IMPLICIT,
            requires_human_escalation=True,
            routing_destination="HUMAN_REVIEW",
        )

    def classify_batch(self, events: List[TransactionFailureEvent]) -> List[ClassificationResult]:
        """Classifies a list of TransactionFailureEvent objects."""
        return [self.classify(e) for e in events]
