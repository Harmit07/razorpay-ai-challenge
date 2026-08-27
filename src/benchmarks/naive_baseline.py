"""
Naive Recovery Baseline Simulator for AI Revenue Recovery Agent.
Implements the industry-standard "blind retry-everything-once-immediately" baseline.
Tracks conversion yields, wasted API calls, and logs every statutory/regulatory violation committed.
"""

from __future__ import annotations
import random
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field

from src.models.schema import (
    TransactionFailureEvent,
    PaymentMethod,
    TransactionType,
    TransactionCategory,
)


class NaiveSimulationResults(BaseModel):
    """Metrics produced by the Naive Baseline strategy."""
    total_transactions: int
    total_revenue_at_risk_inr: float
    total_recovered_revenue_inr: float
    total_unrecovered_revenue_inr: float
    recovery_rate_pct: float
    
    recovered_count: int
    failed_count: int
    wasted_api_calls: int
    
    # Statutory Violations Committed by Naive Strategy
    total_compliance_violations: int
    violation_rbi_no_24h_pre_debit_notice: int
    violation_rbi_afa_cap_breached: int
    violation_rbi_mandate_revoked_retry: int
    violation_rbi_mandate_expired_retry: int
    violation_cpa_dispute_harassment: int
    violation_trai_dnd_spam: int
    violation_max_retries_exceeded: int


class NaiveBaselineRunner:
    """
    Simulates the naive industry approach:
    - Retries every transaction once immediately (or within fixed 24h)
    - Uses only the original payment instrument
    - No root-cause diagnosis
    - No 24h pre-debit alert
    - No AFA threshold check
    - No salary cycle snapping
    - No multi-channel recovery ladder (no WhatsApp UPI link, no Voice Bot)
    - Blindly ignores mandate revocations, disputes, and DND status
    """

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def run_simulation(self, events: List[TransactionFailureEvent]) -> NaiveSimulationResults:
        total_rev_at_risk = sum(e.amount for e in events)
        total_recovered = 0.0
        recovered_count = 0
        failed_count = 0
        wasted_api_calls = 0

        # Violation counters
        v_no_notice = 0
        v_afa_cap = 0
        v_revoked = 0
        v_expired = 0
        v_dispute = 0
        v_dnd = 0
        v_max_retries = 0

        for event in events:
            # The naive baseline blindly triggers an API retry for everything
            wasted_api_calls += 1

            # -------------------------------------------------------------
            # 1. TALLY STATUTORY & REGULATORY VIOLATIONS
            # -------------------------------------------------------------
            # Violation 1: RBI 24h Pre-Debit Notice (breached on all recurring retries)
            if event.txn_type == TransactionType.RECURRING_SUBSCRIPTION:
                v_no_notice += 1

            # Violation 2: RBI AFA Cap Breach (retrying amount > ₹15k / > ₹1L via auto-debit)
            if event.txn_type == TransactionType.RECURRING_SUBSCRIPTION:
                cap = 100000.0 if event.is_afa_exempt else 15000.0
                if event.amount > cap:
                    v_afa_cap += 1

            # Violation 3: Mandate Revoked
            if event.error_reason == "mandate_cancelled_by_user":
                v_revoked += 1

            # Violation 4: Mandate Expired
            if event.error_reason == "mandate_validity_expired" or (event.mandate_valid_until and event.mandate_valid_until < event.timestamp + timedelta(hours=24)):
                v_expired += 1

            # Violation 5: CPA 2019 Dispute Harassment (Consumer Protection Act 2019)
            if event.dispute_active:
                v_dispute += 1

            # Violation 6: TRAI DND Violation (sending SMS/Calls to DND numbers)
            if event.is_dnd:
                v_dnd += 1

            # Violation 7: Max Retries Exceeded (> 3 attempts)
            if event.current_attempt_count >= 3:
                v_max_retries += 1

            # -------------------------------------------------------------
            # 2. COMPUTE NAIVE CONVERSION SUCCESS
            # -------------------------------------------------------------
            # Naive conversion probabilities are severely degraded:
            # - Hard fails (expired card, revoked mandate, expired mandate, checkout drop-off) convert at 0%
            # - Bank downtime retry immediately converts at only ~15% (bank still down)
            # - Low balance retry immediately converts at only ~12% (salary not credited yet)
            is_recovered = False

            if event.error_reason in ["mandate_cancelled_by_user", "mandate_validity_expired", "card_expired"]:
                is_recovered = False  # 0% chance on dead instrument
            elif event.dispute_active:
                is_recovered = False  # Blocked by fraud
            elif event.txn_type == TransactionType.CHECKOUT_DROP_OFF:
                is_recovered = False  # Naive retry doesn't send 1-click cart recovery link
            elif event.error_reason == "bank_server_down":
                is_recovered = (self.rng.random() < 0.15)  # Bank switch might recover briefly
            elif event.error_reason == "insufficient_funds":
                is_recovered = (self.rng.random() < 0.12)  # Low probability without salary cycle snap
            elif event.error_reason == "upi_collect_request_expired":
                is_recovered = False  # Dead collect request cannot be re-charged without new intent link
            else:
                is_recovered = (self.rng.random() < 0.10)

            if is_recovered:
                recovered_count += 1
                total_recovered += event.amount
            else:
                failed_count += 1

        total_unrecovered = total_rev_at_risk - total_recovered
        recov_rate = (total_recovered / total_rev_at_risk * 100) if total_rev_at_risk > 0 else 0.0
        total_violations = (v_no_notice + v_afa_cap + v_revoked + v_expired + v_dispute + v_dnd + v_max_retries)

        return NaiveSimulationResults(
            total_transactions=len(events),
            total_revenue_at_risk_inr=round(total_rev_at_risk, 2),
            total_recovered_revenue_inr=round(total_recovered, 2),
            total_unrecovered_revenue_inr=round(total_unrecovered, 2),
            recovery_rate_pct=round(recov_rate, 2),
            recovered_count=recovered_count,
            failed_count=failed_count,
            wasted_api_calls=wasted_api_calls,
            total_compliance_violations=total_violations,
            violation_rbi_no_24h_pre_debit_notice=v_no_notice,
            violation_rbi_afa_cap_breached=v_afa_cap,
            violation_rbi_mandate_revoked_retry=v_revoked,
            violation_rbi_mandate_expired_retry=v_expired,
            violation_cpa_dispute_harassment=v_dispute,
            violation_trai_dnd_spam=v_dnd,
            violation_max_retries_exceeded=v_max_retries,
        )
