"""
Batch Failure Generator for AI Revenue Recovery Agent.
Generates realistic, diverse synthetic batches of 600-800 transactions
across recurring subscriptions, checkout drop-offs, and B2B invoices,
faithfully implementing Razorpay's 3-tier error taxonomy, RBI 2026 E-Mandate caps,
TRAI quiet hours distributions, and 10 deliberate production edge cases.
"""

import json
import random
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path

from src.models.schema import (
    TransactionFailureEvent,
    PaymentMethod,
    ErrorSource,
    ErrorStep,
    TransactionType,
    TransactionCategory,
    AttemptRecord,
    AttemptStatus,
    PromiseToPayRecord,
)


class BatchFailureGenerator:
    """
    Generates synthetic batches of failed payment events modeled on Razorpay's error taxonomy.
    """

    RAW_UNSTRUCTURED_DECLINES = [
        "U30-SWITCH_UNAVAILABLE_CODE_987: Issuer switch dropped packet during inter-bank settlement route",
        "DECLINE_RC_91: SWITCH TIMEOUT / ISSUER INOPERATIVE / RETRY_NOT_ALLOWED_BY_RULE_44",
        "AC_RESTRICTED: ACCOUNT_IN_DORMANT_SUSPENSE_STATUS_CODE_402_KYC_PENDING",
        "CUSTOM_FILTER_TRIGGER: VELOCITY_BURST_SCORE_88_FLAGGED_BY_ISSUER_CBS",
        "UNSTRUCTURED_DECLINE_STRING: BANK_CBS_ERROR_EXT_FAIL_UNKNOWN_RESPONSE_CODE_99",
        "RESP_57_TRANSACTION_NOT_PERMITTED_TO_CARDHOLDER_SPECIAL_SECURITY_BLOCK",
        "GW_REJECT_101: CORE_BANKING_SYSTEM_SOCKET_CLOSED_UNEXPECTEDLY",
    ]

    # Realistic error bucket distributions and signatures
    BUCKET_SIGNATURES = [
        # Bucket 1: Insufficient Balance (Soft / Liquidity)
        {
            "bucket_id": 1,
            "weight": 28,
            "error_code": "BAD_REQUEST_ERROR",
            "error_source": ErrorSource.CUSTOMER,
            "error_step": ErrorStep.PAYMENT_AUTHORIZATION,
            "error_reason": "insufficient_funds",
            "method": PaymentMethod.UPI_AUTOPAY,
            "txn_type": TransactionType.RECURRING_SUBSCRIPTION,
            "category": TransactionCategory.STANDARD,
            "amount_range": (299.0, 14999.0),
        },
        # Bucket 2: Bank Outage / Server Down (Soft / Technical)
        {
            "bucket_id": 2,
            "weight": 10,
            "error_code": "GATEWAY_ERROR",
            "error_source": ErrorSource.GATEWAY,
            "error_step": ErrorStep.PAYMENT_AUTHORIZATION,
            "error_reason": "bank_server_down",
            "method": PaymentMethod.CARD,
            "txn_type": TransactionType.RECURRING_SUBSCRIPTION,
            "category": TransactionCategory.STANDARD,
            "amount_range": (999.0, 9999.0),
        },
        # Bucket 3: Gateway Timeout / Socket Hangup (Soft / Network)
        {
            "bucket_id": 3,
            "weight": 7,
            "error_code": "GATEWAY_ERROR",
            "error_source": ErrorSource.NETWORK,
            "error_step": ErrorStep.PAYMENT_AUTHORIZATION,
            "error_reason": "gateway_timeout",
            "method": PaymentMethod.CARD,
            "txn_type": TransactionType.RECURRING_SUBSCRIPTION,
            "category": TransactionCategory.STANDARD,
            "amount_range": (499.0, 12000.0),
        },
        # Bucket 4: Velocity Limit Exceeded (Soft / Bank Limit)
        {
            "bucket_id": 4,
            "weight": 5,
            "error_code": "BAD_REQUEST_ERROR",
            "error_source": ErrorSource.BANK,
            "error_step": ErrorStep.PAYMENT_AUTHORIZATION,
            "error_reason": "velocity_limit_exceeded",
            "method": PaymentMethod.UPI_AUTOPAY,
            "txn_type": TransactionType.RECURRING_SUBSCRIPTION,
            "category": TransactionCategory.STANDARD,
            "amount_range": (5000.0, 14000.0),
        },
        # Bucket 5: UPI Collect Request Expired (Customer Action)
        {
            "bucket_id": 5,
            "weight": 9,
            "error_code": "BAD_REQUEST_ERROR",
            "error_source": ErrorSource.CUSTOMER,
            "error_step": ErrorStep.PAYMENT_AUTHORIZATION,
            "error_reason": "upi_collect_expired",
            "method": PaymentMethod.UPI_COLLECT,
            "txn_type": TransactionType.RECURRING_SUBSCRIPTION,
            "category": TransactionCategory.STANDARD,
            "amount_range": (199.0, 7999.0),
        },
        # Bucket 6: 3DS OTP Authentication Failure (Customer Drop)
        {
            "bucket_id": 6,
            "weight": 7,
            "error_code": "BAD_REQUEST_ERROR",
            "error_source": ErrorSource.CUSTOMER,
            "error_step": ErrorStep.PAYMENT_AUTHENTICATION,
            "error_reason": "authentication_failed",
            "method": PaymentMethod.CARD,
            "txn_type": TransactionType.RECURRING_SUBSCRIPTION,
            "category": TransactionCategory.STANDARD,
            "amount_range": (1499.0, 15000.0),
        },
        # Bucket 7: Expired Card Instrument (Hard Failure)
        {
            "bucket_id": 7,
            "weight": 6,
            "error_code": "BAD_REQUEST_ERROR",
            "error_source": ErrorSource.CUSTOMER,
            "error_step": ErrorStep.PAYMENT_INITIATION,
            "error_reason": "card_expired",
            "method": PaymentMethod.CARD,
            "txn_type": TransactionType.RECURRING_SUBSCRIPTION,
            "category": TransactionCategory.STANDARD,
            "amount_range": (999.0, 8999.0),
        },
        # Bucket 8: Mandate Revoked by Customer (Hard Terminal Stop)
        {
            "bucket_id": 8,
            "weight": 4,
            "error_code": "BAD_REQUEST_ERROR",
            "error_source": ErrorSource.CUSTOMER,
            "error_step": ErrorStep.PAYMENT_AUTHORIZATION,
            "error_reason": "mandate_cancelled_by_user",
            "method": PaymentMethod.UPI_AUTOPAY,
            "txn_type": TransactionType.RECURRING_SUBSCRIPTION,
            "category": TransactionCategory.STANDARD,
            "amount_range": (499.0, 4999.0),
        },
        # Bucket 9: Mandate Validity Expired (Hard Stop)
        {
            "bucket_id": 9,
            "weight": 3,
            "error_code": "BAD_REQUEST_ERROR",
            "error_source": ErrorSource.CUSTOMER,
            "error_step": ErrorStep.PAYMENT_INITIATION,
            "error_reason": "mandate_validity_expired",
            "method": PaymentMethod.NACH,
            "txn_type": TransactionType.RECURRING_SUBSCRIPTION,
            "category": TransactionCategory.STANDARD,
            "amount_range": (1200.0, 15000.0),
        },
        # Bucket 10: Bank Technical Decline / Security Filter
        {
            "bucket_id": 10,
            "weight": 4,
            "error_code": "GATEWAY_ERROR",
            "error_source": ErrorSource.BANK,
            "error_step": ErrorStep.PAYMENT_AUTHORIZATION,
            "error_reason": "bank_technical_decline",
            "method": PaymentMethod.CARD,
            "txn_type": TransactionType.RECURRING_SUBSCRIPTION,
            "category": TransactionCategory.STANDARD,
            "amount_range": (2500.0, 14500.0),
        },
        # Bucket 11: Statutory AFA Ceiling Breached (> ₹15k / > ₹1L)
        {
            "bucket_id": 11,
            "weight": 5,
            "error_code": "BAD_REQUEST_ERROR",
            "error_source": ErrorSource.BUSINESS,
            "error_step": ErrorStep.PAYMENT_INITIATION,
            "error_reason": "amount_exceeds_statutory_afa_limit",
            "method": PaymentMethod.CARD,
            "txn_type": TransactionType.RECURRING_SUBSCRIPTION,
            "category": TransactionCategory.STANDARD,
            "amount_range": (18000.0, 65000.0),
        },
        # Bucket 12: Checkout Drop-Off / Cart Abandonment
        {
            "bucket_id": 12,
            "weight": 6,
            "error_code": "BAD_REQUEST_ERROR",
            "error_source": ErrorSource.CUSTOMER,
            "error_step": ErrorStep.PAYMENT_INITIATION,
            "error_reason": "checkout_abandonment_dropoff",
            "method": PaymentMethod.UPI_COLLECT,
            "txn_type": TransactionType.CHECKOUT_DROP_OFF,
            "category": TransactionCategory.STANDARD,
            "amount_range": (499.0, 12999.0),
        },
        # Bucket 13: Raw Unmapped / Ambiguous Bank Decline Text
        {
            "bucket_id": 13,
            "weight": 6,
            "error_code": "GATEWAY_ERROR",
            "error_source": ErrorSource.GATEWAY,
            "error_step": ErrorStep.PAYMENT_AUTHORIZATION,
            "error_reason": "raw_unmapped_decline",
            "method": PaymentMethod.CARD,
            "txn_type": TransactionType.RECURRING_SUBSCRIPTION,
            "category": TransactionCategory.STANDARD,
            "amount_range": (999.0, 14000.0),
        },
    ]

    def __init__(self, seed: Optional[int] = 42):
        self.rng = random.Random(seed)

    def generate_deliberate_edge_cases(self, base_timestamp: Optional[datetime] = None) -> List[TransactionFailureEvent]:
        """
        Generates 10 deliberate, concrete, named production edge cases
        designed to test graceful degradation, stopping rules, and regulatory adherence.
        """
        if base_timestamp is None:
            base_timestamp = datetime.now(timezone.utc)

        edge_cases: List[TransactionFailureEvent] = []

        # EDGE-01: The Zombie Retry Trap (Customer failing 5x across cycles, 3 attempts exhausted)
        edge_cases.append(
            TransactionFailureEvent(
                txn_id="pay_edge01_zombie5x",
                amount=2499.00,
                method=PaymentMethod.UPI_AUTOPAY,
                error_code="BAD_REQUEST_ERROR",
                error_source=ErrorSource.CUSTOMER,
                error_step=ErrorStep.PAYMENT_AUTHORIZATION,
                error_reason="insufficient_funds",
                txn_type=TransactionType.RECURRING_SUBSCRIPTION,
                mandate_id="man_edge01_zombie",
                category=TransactionCategory.STANDARD,
                customer_id="cust_edge01_chronic",
                customer_phone_masked="+91-9811****9001",
                customer_email_masked="z*****e@example.com",
                edge_case_tag="EDGE_01_ZOMBIE_RETRY_5X",
                attempt_history=[
                    AttemptRecord(attempt_number=1, timestamp=base_timestamp - timedelta(days=6), channel="PRE_DEBIT_ALERT", status=AttemptStatus.PRE_DEBIT_DELIVERED, error_reason="insufficient_funds"),
                    AttemptRecord(attempt_number=2, timestamp=base_timestamp - timedelta(days=4), channel="AUTO_DEBIT", status=AttemptStatus.FAILED, error_reason="insufficient_funds"),
                    AttemptRecord(attempt_number=3, timestamp=base_timestamp - timedelta(days=2), channel="AUTO_DEBIT", status=AttemptStatus.FAILED, error_reason="insufficient_funds"),
                ],
                timestamp=base_timestamp,
            )
        )

        # EDGE-02: The ₹15,000 AFA Straddle (₹15,001.00 on Standard Subscription)
        edge_cases.append(
            TransactionFailureEvent(
                txn_id="pay_edge02_afa15k",
                amount=15001.00,  # Exceeds ₹15k cap by exactly ₹1
                method=PaymentMethod.CARD,
                error_code="BAD_REQUEST_ERROR",
                error_source=ErrorSource.BUSINESS,
                error_step=ErrorStep.PAYMENT_INITIATION,
                error_reason="amount_exceeds_statutory_afa_limit",
                txn_type=TransactionType.RECURRING_SUBSCRIPTION,
                mandate_id="man_edge02_afa15k",
                category=TransactionCategory.STANDARD,
                customer_id="cust_edge02_hival",
                customer_phone_masked="+91-9822****9002",
                customer_email_masked="a*****a@example.com",
                edge_case_tag="EDGE_02_AFA_15K_STRADDLE",
                timestamp=base_timestamp,
            )
        )

        # EDGE-03: The ₹1,00,000 Exemption Straddle (₹1,00,001.00 on Mutual Fund SIP)
        edge_cases.append(
            TransactionFailureEvent(
                txn_id="pay_edge03_afa1L",
                amount=100001.00,  # Exceeds relaxed ₹1L cap by exactly ₹1
                method=PaymentMethod.NACH,
                error_code="BAD_REQUEST_ERROR",
                error_source=ErrorSource.BUSINESS,
                error_step=ErrorStep.PAYMENT_INITIATION,
                error_reason="amount_exceeds_statutory_afa_limit",
                txn_type=TransactionType.RECURRING_SUBSCRIPTION,
                mandate_id="man_edge03_sip1L",
                category=TransactionCategory.MUTUAL_FUND,
                customer_id="cust_edge03_investor",
                customer_phone_masked="+91-9833****9003",
                customer_email_masked="s*****p@example.com",
                edge_case_tag="EDGE_03_AFA_1L_STRADDLE",
                timestamp=base_timestamp,
            )
        )

        # EDGE-04: Mandate Expiring Mid-Retry Cycle (Expires in +12 hours)
        edge_cases.append(
            TransactionFailureEvent(
                txn_id="pay_edge04_expiring_mandate",
                amount=4999.00,
                method=PaymentMethod.CARD,
                error_code="BAD_REQUEST_ERROR",
                error_source=ErrorSource.CUSTOMER,
                error_step=ErrorStep.PAYMENT_AUTHORIZATION,
                error_reason="insufficient_funds",
                txn_type=TransactionType.RECURRING_SUBSCRIPTION,
                mandate_id="man_edge04_expiring",
                category=TransactionCategory.STANDARD,
                customer_id="cust_edge04_exp",
                customer_phone_masked="+91-9844****9004",
                customer_email_masked="e*****p@example.com",
                edge_case_tag="EDGE_04_MANDATE_EXPIRING_MID_RETRY",
                mandate_valid_until=base_timestamp + timedelta(hours=12),  # Expiring before 24h/48h cooling elapses
                timestamp=base_timestamp,
            )
        )

        # EDGE-05: The TRAI Quiet Hours Sleep Trap (Ingested at 23:45 IST)
        # 23:45 IST is 18:15 UTC
        quiet_time = base_timestamp.replace(hour=18, minute=45, second=0, microsecond=0)
        edge_cases.append(
            TransactionFailureEvent(
                txn_id="pay_edge05_quiet_hours",
                amount=1499.00,
                method=PaymentMethod.UPI_AUTOPAY,
                error_code="GATEWAY_ERROR",
                error_source=ErrorSource.GATEWAY,
                error_step=ErrorStep.PAYMENT_AUTHORIZATION,
                error_reason="bank_server_down",
                txn_type=TransactionType.RECURRING_SUBSCRIPTION,
                mandate_id="man_edge05_night",
                category=TransactionCategory.STANDARD,
                customer_id="cust_edge05_nightowl",
                customer_phone_masked="+91-9855****9005",
                customer_email_masked="n*****t@example.com",
                edge_case_tag="EDGE_05_TRAI_QUIET_HOURS_SLEEP",
                timestamp=quiet_time,
            )
        )

        # EDGE-06: Active Promise-to-Pay (PTP) Race Condition
        promise_date = base_timestamp + timedelta(days=4)
        edge_cases.append(
            TransactionFailureEvent(
                txn_id="pay_edge06_ptp_active",
                amount=7500.00,
                method=PaymentMethod.UPI_AUTOPAY,
                error_code="BAD_REQUEST_ERROR",
                error_source=ErrorSource.CUSTOMER,
                error_step=ErrorStep.PAYMENT_AUTHORIZATION,
                error_reason="insufficient_funds",
                txn_type=TransactionType.RECURRING_SUBSCRIPTION,
                mandate_id="man_edge06_ptp",
                category=TransactionCategory.STANDARD,
                customer_id="cust_edge06_ptp",
                customer_phone_masked="+91-9866****9006",
                customer_email_masked="p*****p@example.com",
                edge_case_tag="EDGE_06_PTP_RACE_CONDITION",
                ptp_record=PromiseToPayRecord(
                    promised_date=promise_date,
                    promised_amount=7500.00,
                    recorded_at=base_timestamp - timedelta(hours=6),
                    grace_until=promise_date + timedelta(hours=24),
                    status="ACTIVE",
                ),
                timestamp=base_timestamp,
            )
        )

        # EDGE-07: Post-Failure Mandate Revocation by User
        edge_cases.append(
            TransactionFailureEvent(
                txn_id="pay_edge07_mandate_revoked",
                amount=3999.00,
                method=PaymentMethod.UPI_AUTOPAY,
                error_code="BAD_REQUEST_ERROR",
                error_source=ErrorSource.CUSTOMER,
                error_step=ErrorStep.PAYMENT_AUTHORIZATION,
                error_reason="mandate_cancelled_by_user",
                txn_type=TransactionType.RECURRING_SUBSCRIPTION,
                mandate_id="man_edge07_revoked",
                category=TransactionCategory.STANDARD,
                customer_id="cust_edge07_cancel",
                customer_phone_masked="+91-9877****9007",
                customer_email_masked="c*****l@example.com",
                edge_case_tag="EDGE_07_MANDATE_REVOKED_POST_FAILURE",
                timestamp=base_timestamp,
            )
        )

        # EDGE-08: Fraud Chargeback / Active Dispute Straddle
        edge_cases.append(
            TransactionFailureEvent(
                txn_id="pay_edge08_fraud_dispute",
                amount=12500.00,
                method=PaymentMethod.CARD,
                error_code="BAD_REQUEST_ERROR",
                error_source=ErrorSource.CUSTOMER,
                error_step=ErrorStep.PAYMENT_AUTHORIZATION,
                error_reason="mandate_cancelled_by_user",
                txn_type=TransactionType.RECURRING_SUBSCRIPTION,
                mandate_id="man_edge08_dispute",
                category=TransactionCategory.STANDARD,
                customer_id="cust_edge08_fraud",
                customer_phone_masked="+91-9888****9008",
                customer_email_masked="d*****e@example.com",
                dispute_active=True,
                risk_flag=True,
                edge_case_tag="EDGE_08_FRAUD_DISPUTE_STRADDLE",
                timestamp=base_timestamp,
            )
        )

        # EDGE-09: MSMED 45-Day Statutory Ceiling Clash (B2B Invoice on Day 43)
        edge_cases.append(
            TransactionFailureEvent(
                txn_id="pay_edge09_msmed45d",
                amount=85000.00,
                method=PaymentMethod.NETBANKING,
                error_code="BAD_REQUEST_ERROR",
                error_source=ErrorSource.BUSINESS,
                error_step=ErrorStep.PAYMENT_AUTHORIZATION,
                error_reason="b2b_invoice_overdue",
                txn_type=TransactionType.B2B_INVOICE,
                category=TransactionCategory.STANDARD,
                customer_id="cust_edge09_supplier",
                customer_phone_masked="+91-9899****9009",
                customer_email_masked="m*****d@example.com",
                edge_case_tag="EDGE_09_MSMED_45_DAY_CLASH",
                raw_error_description="MSME Supplier Registered under Section 15. Invoice age: 43 days.",
                timestamp=base_timestamp,
            )
        )

        # EDGE-10: Unrecognized Switch Timeout with High Risk Flag
        edge_cases.append(
            TransactionFailureEvent(
                txn_id="pay_edge10_switch_risk",
                amount=11500.00,
                method=PaymentMethod.CARD,
                error_code="GATEWAY_ERROR",
                error_source=ErrorSource.GATEWAY,
                error_step=ErrorStep.PAYMENT_AUTHORIZATION,
                error_reason="raw_unmapped_decline",
                txn_type=TransactionType.RECURRING_SUBSCRIPTION,
                category=TransactionCategory.STANDARD,
                customer_id="cust_edge10_risk",
                customer_phone_masked="+91-9800****9010",
                customer_email_masked="r*****k@example.com",
                risk_flag=True,
                raw_error_description="U30-SWITCH_UNAVAILABLE_CODE_987: Issuer switch dropped packet during inter-bank settlement route",
                edge_case_tag="EDGE_10_AMBIGUOUS_HIGH_RISK",
                timestamp=base_timestamp,
            )
        )

        return edge_cases

    def generate_single_event(
        self,
        bucket_override: Optional[int] = None,
        base_timestamp: Optional[datetime] = None,
        force_risk_flag: Optional[bool] = None,
        force_txn_type: Optional[TransactionType] = None,
    ) -> TransactionFailureEvent:
        """Generates a single synthetic TransactionFailureEvent."""
        if base_timestamp is None:
            past_offset_hours = self.rng.randint(0, 336)
            base_timestamp = datetime.now(timezone.utc) - timedelta(hours=past_offset_hours)

        # Select bucket based on weights or override
        if bucket_override is not None:
            config = next(b for b in self.BUCKET_SIGNATURES if b["bucket_id"] == bucket_override)
        else:
            weights = [b["weight"] for b in self.BUCKET_SIGNATURES]
            config = self.rng.choices(self.BUCKET_SIGNATURES, weights=weights, k=1)[0]

        # Determine Transaction Type (Mix of Recurring ~70%, Checkout Drop-off ~20%, B2B ~10%)
        if force_txn_type is not None:
            txn_type = force_txn_type
        elif config["bucket_id"] == 12:
            txn_type = TransactionType.CHECKOUT_DROP_OFF
        else:
            type_roll = self.rng.random()
            if type_roll < 0.70:
                txn_type = TransactionType.RECURRING_SUBSCRIPTION
            elif type_roll < 0.90:
                txn_type = TransactionType.CHECKOUT_DROP_OFF
            else:
                txn_type = TransactionType.B2B_INVOICE

        # Generate unique IDs
        rand_suffix = uuid.UUID(int=self.rng.getrandbits(128)).hex[:8]
        txn_id = f"pay_{rand_suffix}"
        cust_id = f"cust_{rand_suffix}"
        mandate_id = f"man_{rand_suffix}" if txn_type == TransactionType.RECURRING_SUBSCRIPTION else None

        # Determine Payment Method based on Txn Type
        if txn_type == TransactionType.B2B_INVOICE:
            method = self.rng.choice([PaymentMethod.NETBANKING, PaymentMethod.NACH, PaymentMethod.CARD])
        elif txn_type == TransactionType.CHECKOUT_DROP_OFF:
            method = self.rng.choice([PaymentMethod.UPI_COLLECT, PaymentMethod.CARD, PaymentMethod.NETBANKING])
        else:
            method = config["method"]

        # Determine Amount & Category (including occasional SIP/Insurance category and B2B high value)
        category = config["category"]
        if txn_type == TransactionType.B2B_INVOICE:
            amount = round(self.rng.uniform(15000.0, 185000.0), 2)
        elif config["bucket_id"] == 11 and self.rng.random() < 0.35:
            category = self.rng.choice([TransactionCategory.MUTUAL_FUND, TransactionCategory.INSURANCE_PREMIUM])
            amount = round(self.rng.uniform(105000.0, 250000.0), 2)
        elif self.rng.random() < 0.08:
            category = self.rng.choice([TransactionCategory.MUTUAL_FUND, TransactionCategory.INSURANCE_PREMIUM])
            amount = round(self.rng.uniform(5000.0, 85000.0), 2)
        else:
            min_amt, max_amt = config["amount_range"]
            amount = round(self.rng.uniform(min_amt, max_amt), 2)

        # Generate masked customer PII (DPDP 2023 compliant)
        phone_mid = f"{self.rng.randint(10, 99)}"
        phone_end = f"{self.rng.randint(1000, 9999)}"
        phone_masked = f"+91-98{phone_mid}****{phone_end}"
        email_masked = f"user_{rand_suffix[:3]}*****@example.com"

        # Generate realistic previous attempt history
        attempt_history: List[AttemptRecord] = []
        hist_roll = self.rng.random()
        if hist_roll < 0.20 and config["bucket_id"] in [1, 2, 4, 5]:
            attempt_history.append(
                AttemptRecord(
                    attempt_number=1,
                    timestamp=base_timestamp - timedelta(hours=self.rng.randint(48, 96)),
                    channel="PRE_DEBIT_ALERT",
                    status=AttemptStatus.PRE_DEBIT_DELIVERED,
                    error_reason="insufficient_funds",
                )
            )
            if hist_roll < 0.08:
                attempt_history.append(
                    AttemptRecord(
                        attempt_number=2,
                        timestamp=base_timestamp - timedelta(hours=self.rng.randint(24, 44)),
                        channel="AUTO_DEBIT",
                        status=AttemptStatus.FAILED,
                        error_reason="insufficient_funds",
                    )
                )

        # Safety & compliance flags
        is_dnd = self.rng.random() < 0.15
        dispute_active = (config["bucket_id"] == 8 and self.rng.random() < 0.25)

        # Independent Risk Flag
        if force_risk_flag is not None:
            risk_flag = force_risk_flag
        else:
            base_risk_prob = 0.35 if config["bucket_id"] == 13 else 0.08
            risk_flag = self.rng.random() < base_risk_prob

        # Raw / Ambiguous decline description
        raw_error_description = None
        if config["bucket_id"] == 13:
            raw_error_description = self.rng.choice(self.RAW_UNSTRUCTURED_DECLINES)
        elif self.rng.random() < 0.12:
            raw_error_description = f"GW_INFO_LOG: {config['error_reason']}_RC_{self.rng.randint(10, 99)}"

        # Optional Promise-to-Pay for B2B or recurring cases
        ptp_record = None
        if self.rng.random() < 0.06 and not dispute_active:
            promise_date = base_timestamp + timedelta(days=self.rng.randint(2, 6))
            ptp_record = PromiseToPayRecord(
                promised_date=promise_date,
                promised_amount=amount,
                recorded_at=base_timestamp,
                grace_until=promise_date + timedelta(hours=24),
                status="ACTIVE",
            )

        # Mandate validity timeline
        mandate_valid_until = None
        if mandate_id:
            if config["bucket_id"] == 9:
                mandate_valid_until = base_timestamp - timedelta(days=self.rng.randint(1, 10))
            else:
                mandate_valid_until = base_timestamp + timedelta(days=self.rng.randint(60, 365))

        return TransactionFailureEvent(
            txn_id=txn_id,
            amount=amount,
            method=method,
            error_code=config["error_code"],
            error_source=config["error_source"],
            error_step=config["error_step"],
            error_reason=config["error_reason"],
            txn_type=txn_type,
            mandate_id=mandate_id,
            category=category,
            customer_id=cust_id,
            customer_phone_masked=phone_masked,
            customer_email_masked=email_masked,
            is_dnd=is_dnd,
            dispute_active=dispute_active,
            risk_flag=risk_flag,
            raw_error_description=raw_error_description,
            mandate_valid_until=mandate_valid_until,
            attempt_history=attempt_history,
            ptp_record=ptp_record,
            timestamp=base_timestamp,
        )

    def generate_batch(self, count: int = 750, inject_edge_cases: bool = True) -> List[TransactionFailureEvent]:
        """
        Generates a robust, representative batch of N failure events (recommended: 600-800).
        Ensures full coverage of all 13 taxonomy buckets, 10 deliberate edge cases,
        realistic error weights, and authentic edge case representation.
        """
        batch: List[TransactionFailureEvent] = []

        # 1. Deliberately inject the 10 named edge cases if requested
        if inject_edge_cases:
            edge_cases = self.generate_deliberate_edge_cases()
            batch.extend(edge_cases)

        if count <= len(batch) + 13:
            # Small test batch
            for b_id in range(1, min(14, count - len(batch) + 1)):
                batch.append(self.generate_single_event(bucket_override=b_id))
            while len(batch) < count:
                batch.append(self.generate_single_event())
            self.rng.shuffle(batch)
            return batch

        # For larger batches (e.g. 50, 700, 750, 800):
        # 2. Guarantee coverage across all 13 buckets
        bucket_copies = 2 if count >= 100 else 1
        for b_id in range(1, 14):
            for _ in range(bucket_copies):
                batch.append(self.generate_single_event(bucket_override=b_id))

        # 3. Scale statistical edge case targets proportionally to batch count
        risk_target = max(3, int(count * 0.08))
        for _ in range(risk_target):
            batch.append(self.generate_single_event(force_risk_flag=True))

        afa_target = max(2, int(count * 0.05))
        for _ in range(afa_target):
            batch.append(self.generate_single_event(bucket_override=11))

        b2b_target = max(2, int(count * 0.10))
        for _ in range(b2b_target):
            batch.append(self.generate_single_event(force_txn_type=TransactionType.B2B_INVOICE))

        checkout_target = max(3, int(count * 0.15))
        for _ in range(checkout_target):
            batch.append(self.generate_single_event(force_txn_type=TransactionType.CHECKOUT_DROP_OFF, bucket_override=12))

        # 4. Fill the remainder up to target count using realistic statistical weights
        remaining = max(0, count - len(batch))
        for _ in range(remaining):
            batch.append(self.generate_single_event())

        # If base targets slightly exceed count on small counts, slice to exact count
        if len(batch) > count:
            batch = batch[:count]

        # Shuffle for realistic distribution
        self.rng.shuffle(batch)
        return batch

    def export_to_json(self, events: List[TransactionFailureEvent], filepath: str | Path) -> None:
        """Serializes and saves a batch of TransactionFailureEvent objects to JSON."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        raw_list = [json.loads(event.model_dump_json()) for event in events]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(raw_list, f, indent=2)

    def load_from_json(self, filepath: str | Path) -> List[TransactionFailureEvent]:
        """Loads a batch of TransactionFailureEvent objects from a JSON file."""
        path = Path(filepath)
        with open(path, "r", encoding="utf-8") as f:
            raw_list = json.load(f)
        return [TransactionFailureEvent(**item) for item in raw_list]

    @staticmethod
    def print_batch_summary(events: List[TransactionFailureEvent]) -> Dict[str, Any]:
        """Computes and prints structured metrics about a generated transaction batch."""
        total_count = len(events)
        total_revenue_at_risk = sum(e.amount for e in events)

        # Count by txn_type
        txn_types: Dict[str, int] = {}
        for e in events:
            txn_types[e.txn_type.value] = txn_types.get(e.txn_type.value, 0) + 1

        # Count by error reason
        reasons: Dict[str, int] = {}
        for e in events:
            reasons[e.error_reason] = reasons.get(e.error_reason, 0) + 1

        # Count by error source
        sources: Dict[str, int] = {}
        for e in events:
            sources[e.error_source.value] = sources.get(e.error_source.value, 0) + 1

        # Count by category
        categories: Dict[str, int] = {}
        for e in events:
            categories[e.category.value] = categories.get(e.category.value, 0) + 1

        # Compliance & Risk metrics
        afa_required_count = sum(1 for e in events if e.requires_afa_validation)
        risk_flag_count = sum(1 for e in events if e.risk_flag)
        dnd_count = sum(1 for e in events if e.is_dnd)
        dispute_count = sum(1 for e in events if e.dispute_active)
        ambiguous_count = sum(1 for e in events if e.raw_error_description is not None)
        ptp_count = sum(1 for e in events if e.ptp_record is not None)

        # Count injected edge cases
        injected_edge_cases: Dict[str, int] = {}
        for e in events:
            if e.edge_case_tag:
                injected_edge_cases[e.edge_case_tag] = injected_edge_cases.get(e.edge_case_tag, 0) + 1

        summary = {
            "total_transactions": total_count,
            "total_revenue_at_risk_inr": round(total_revenue_at_risk, 2),
            "average_ticket_size_inr": round(total_revenue_at_risk / total_count, 2) if total_count > 0 else 0,
            "transaction_type_breakdown": txn_types,
            "error_source_breakdown": sources,
            "top_error_reasons": sorted(reasons.items(), key=lambda x: x[1], reverse=True),
            "afa_required_count": afa_required_count,
            "risk_flagged_count": risk_flag_count,
            "dnd_registered_count": dnd_count,
            "dispute_active_count": dispute_count,
            "ambiguous_raw_decline_count": ambiguous_count,
            "active_ptp_count": ptp_count,
            "injected_edge_cases_count": len(injected_edge_cases),
            "injected_edge_cases_breakdown": injected_edge_cases,
        }
        return summary
