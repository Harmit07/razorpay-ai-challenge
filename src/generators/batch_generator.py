"""
Batch Generator Skeleton for AI Revenue Recovery Agent.
Generates realistic, diverse synthetic batches of payment failure events
across all 12 error taxonomy buckets, regulatory thresholds, and real-world edge cases.
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

    # Realistic error bucket distributions and signatures
    BUCKET_SIGNATURES = [
        # Bucket 1: Insufficient Balance (Soft / Liquidity)
        {
            "bucket_id": 1,
            "weight": 30,
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
            "weight": 12,
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
            "weight": 8,
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
            "weight": 10,
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
            "weight": 8,
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
    ]

    def __init__(self, seed: Optional[int] = 42):
        self.rng = random.Random(seed)

    def generate_single_event(
        self,
        bucket_override: Optional[int] = None,
        base_timestamp: Optional[datetime] = None,
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
            mandate_valid_until=mandate_valid_until,
            attempt_history=attempt_history,
            timestamp=base_timestamp,
        )

    def generate_batch(self, count: int = 50) -> List[TransactionFailureEvent]:
        """Generates a batch of N failure events ensuring coverage across all 12 buckets."""
        batch: List[TransactionFailureEvent] = []

        # Guarantee at least 1 of each of the 12 concrete buckets
        for b_id in range(1, 13):
            batch.append(self.generate_single_event(bucket_override=b_id))

        # Fill the remaining batch using realistic statistical weights
        remaining = max(0, count - 12)
        for _ in range(remaining):
            batch.append(self.generate_single_event())

        return batch
