"""
Batch Generator Skeleton for AI Revenue Recovery Agent.
Generates realistic, diverse synthetic batches of payment failure events
across all 13 error taxonomy buckets (including raw/ambiguous declines),
independent risk flags, regulatory thresholds, and real-world edge cases.
"""

import random
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

from src.models.schema import (
    TransactionFailureEvent,
    PaymentMethod,
    ErrorSource,
    ErrorStep,
    TransactionType,
    TransactionCategory,
    AttemptRecord,
    AttemptStatus,
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
            "weight": 5,
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

    def generate_single_event(
        self,
        bucket_override: Optional[int] = None,
        base_timestamp: Optional[datetime] = None,
        force_risk_flag: Optional[bool] = None,
    ) -> TransactionFailureEvent:
        """Generates a single synthetic TransactionFailureEvent."""
        if base_timestamp is None:
            base_timestamp = datetime.now(timezone.utc) - timedelta(hours=self.rng.randint(1, 72))

        # Select bucket based on weights or override
        if bucket_override is not None:
            config = next(b for b in self.BUCKET_SIGNATURES if b["bucket_id"] == bucket_override)
        else:
            weights = [b["weight"] for b in self.BUCKET_SIGNATURES]
            config = self.rng.choices(self.BUCKET_SIGNATURES, weights=weights, k=1)[0]

        # Generate unique IDs
        rand_suffix = uuid.UUID(int=self.rng.getrandbits(128)).hex[:8]
        txn_id = f"pay_{rand_suffix}"
        cust_id = f"cust_{rand_suffix}"
        mandate_id = f"man_{rand_suffix}" if config["txn_type"] == TransactionType.RECURRING_SUBSCRIPTION else None

        # Determine Amount & Category (including occasional SIP/Insurance category)
        category = config["category"]
        if config["bucket_id"] == 11 and self.rng.random() < 0.3:
            category = TransactionCategory.MUTUAL_FUND
            amount = round(self.rng.uniform(105000.0, 250000.0), 2)
        else:
            min_amt, max_amt = config["amount_range"]
            amount = round(self.rng.uniform(min_amt, max_amt), 2)

        # Generate masked customer PII
        phone_mid = f"{self.rng.randint(10, 99)}"
        phone_end = f"{self.rng.randint(1000, 9999)}"
        phone_masked = f"+91-98{phone_mid}****{phone_end}"
        email_masked = f"user_{rand_suffix[:3]}*****@example.com"

        # Generate optional previous attempt history for some events
        attempt_history = []
        if self.rng.random() < 0.25 and config["bucket_id"] in [1, 2, 5]:
            attempt_history.append(
                AttemptRecord(
                    attempt_number=1,
                    timestamp=base_timestamp - timedelta(hours=self.rng.randint(24, 48)),
                    channel="PRE_DEBIT_ALERT",
                    status=AttemptStatus.PRE_DEBIT_DELIVERED,
                    error_reason="insufficient_funds",
                )
            )

        # Safety & compliance flags
        is_dnd = self.rng.random() < 0.15
        dispute_active = (config["bucket_id"] == 8 and self.rng.random() < 0.2)

        # Independent Risk Flag (Fraud / High Risk)
        if force_risk_flag is not None:
            risk_flag = force_risk_flag
        else:
            # Independent ~10% probability of risk_flag across any event, higher for bucket 13
            base_risk_prob = 0.35 if config["bucket_id"] == 13 else 0.08
            risk_flag = self.rng.random() < base_risk_prob

        # Raw / Ambiguous decline description
        raw_error_description = None
        if config["bucket_id"] == 13:
            raw_error_description = self.rng.choice(self.RAW_UNSTRUCTURED_DECLINES)
        elif self.rng.random() < 0.12:
            raw_error_description = f"GW_INFO_LOG: {config['error_reason']}_RC_{self.rng.randint(10, 99)}"

        mandate_valid_until = None
        if mandate_id:
            if config["bucket_id"] == 9:
                mandate_valid_until = base_timestamp - timedelta(days=2)  # Expired
            else:
                mandate_valid_until = base_timestamp + timedelta(days=self.rng.randint(60, 365))

        return TransactionFailureEvent(
            txn_id=txn_id,
            amount=amount,
            method=config["method"],
            error_code=config["error_code"],
            error_source=config["error_source"],
            error_step=config["error_step"],
            error_reason=config["error_reason"],
            txn_type=config["txn_type"],
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
            timestamp=base_timestamp,
        )

    def generate_batch(self, count: int = 50) -> List[TransactionFailureEvent]:
        """Generates a batch of N failure events ensuring coverage across all 13 buckets, risk flags, and ambiguous text."""
        batch: List[TransactionFailureEvent] = []

        # Guarantee at least 1 of each of the 13 concrete buckets
        for b_id in range(1, 14):
            batch.append(self.generate_single_event(bucket_override=b_id))

        # Explicitly guarantee at least 3 risk-flagged events in the batch
        for _ in range(3):
            batch.append(self.generate_single_event(force_risk_flag=True))

        # Fill the remaining batch using realistic statistical weights
        remaining = max(0, count - len(batch))
        for _ in range(remaining):
            batch.append(self.generate_single_event())

        return batch
