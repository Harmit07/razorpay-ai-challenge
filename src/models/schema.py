"""
Core Data Schemas & Models for AI Revenue Recovery Agent.
Implements Razorpay 3-tier error taxonomy, regulatory AFA attributes,
attempt history tracking, Promise-to-Pay state, and PII masking.
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator


class PaymentMethod(str, Enum):
    CARD = "card"
    UPI_AUTOPAY = "upi_autopay"
    NACH = "nach"
    NETBANKING = "netbanking"
    UPI_COLLECT = "upi_collect"


class ErrorSource(str, Enum):
    CUSTOMER = "customer"
    GATEWAY = "gateway"
    BANK = "bank"
    BUSINESS = "business"
    NETWORK = "network"


class ErrorStep(str, Enum):
    PAYMENT_INITIATION = "payment_initiation"
    PAYMENT_AUTHENTICATION = "payment_authentication"
    PAYMENT_AUTHORIZATION = "payment_authorization"
    PAYMENT_CAPTURE = "payment_capture"


class TransactionType(str, Enum):
    RECURRING_SUBSCRIPTION = "RECURRING_SUBSCRIPTION"
    CHECKOUT_DROP_OFF = "CHECKOUT_DROP_OFF"
    B2B_INVOICE = "B2B_INVOICE"


class TransactionCategory(str, Enum):
    STANDARD = "STANDARD"
    MUTUAL_FUND = "MUTUAL_FUND"
    INSURANCE_PREMIUM = "INSURANCE_PREMIUM"
    CREDIT_CARD_BILL = "CREDIT_CARD_BILL"


class AttemptStatus(str, Enum):
    QUEUED = "QUEUED"
    PRE_DEBIT_DELIVERED = "PRE_DEBIT_DELIVERED"
    AUTO_DEBIT_ATTEMPTED = "AUTO_DEBIT_ATTEMPTED"
    LINK_DISPATCHED = "LINK_DISPATCHED"
    VOICE_OUTREACH_COMPLETED = "VOICE_OUTREACH_COMPLETED"
    PAID = "PAID"
    FAILED = "FAILED"
    OPTED_OUT = "OPTED_OUT"
    PTP_RECORDED = "PTP_RECORDED"


class AttemptRecord(BaseModel):
    attempt_number: int = Field(..., ge=1, le=5, description="Attempt sequence number (1-indexed)")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of the attempt")
    channel: str = Field(..., description="Channel used: AUTO_DEBIT, WHATSAPP_LINK, SMS_ALERT, VOICE_CALL, PRE_DEBIT_ALERT")
    status: AttemptStatus = Field(..., description="Outcome status of the attempt")
    error_reason: Optional[str] = Field(None, description="Error reason if attempt failed")
    raw_response_snippet: Optional[str] = Field(None, description="Safe snippet of gateway response")


class PromiseToPayRecord(BaseModel):
    promised_date: datetime = Field(..., description="Customer promised payment timestamp")
    promised_amount: float = Field(..., gt=0, description="Rupee amount promised")
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp when PTP was recorded")
    grace_until: datetime = Field(..., description="Grace expiry timestamp (promised_date + 24 hours)")
    status: str = Field(default="ACTIVE", description="PTP state: ACTIVE, FULFILLED, BREACHED")


class TransactionFailureEvent(BaseModel):
    """
    Primary schema representing a revenue-at-risk event ingested by the AI Recovery Agent.
    """
    txn_id: str = Field(..., description="Unique transaction or payment ID (e.g., pay_01HZ89K12)")
    amount: float = Field(..., gt=0, description="Transaction amount in INR")
    method: PaymentMethod = Field(..., description="Payment rail / instrument method")
    error_code: str = Field(..., description="Razorpay error code (e.g., BAD_REQUEST_ERROR, GATEWAY_ERROR)")
    error_source: ErrorSource = Field(..., description="Origin of error: customer, gateway, bank, business, network")
    error_step: ErrorStep = Field(..., description="Step where failure occurred")
    error_reason: str = Field(..., description="Exact machine-readable reason (e.g., insufficient_funds, card_expired)")
    txn_type: TransactionType = Field(default=TransactionType.RECURRING_SUBSCRIPTION, description="Type of transaction")
    mandate_id: Optional[str] = Field(None, description="Unique Mandate ID (e.g., man_01HZ89K12) for recurring mandates")
    category: TransactionCategory = Field(default=TransactionCategory.STANDARD, description="Regulatory category under RBI 2026 framework")
    
    # Masked Customer Identifiers (DPDP 2023 & PCI-DSS Compliance)
    customer_id: str = Field(..., description="Customer reference identifier (e.g., cust_01HZ89K12)")
    customer_phone_masked: str = Field(..., description="Masked phone number (e.g., +91-98****9012)")
    customer_email_masked: str = Field(..., description="Masked email address (e.g., r*****l@example.com)")
    
    # Compliance & Safety Flags
    is_dnd: bool = Field(default=False, description="Whether customer is registered on TRAI DND registry")
    dispute_active: bool = Field(default=False, description="Whether an active fraud dispute/chargeback is open")
    mandate_valid_until: Optional[datetime] = Field(None, description="Mandate expiry date for recurring subscriptions")
    
    # Lifecycle & Audit State
    attempt_history: List[AttemptRecord] = Field(default_factory=list, description="Historical list of recovery attempts")
    ptp_record: Optional[PromiseToPayRecord] = Field(None, description="Active Promise-to-Pay record if set")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Initial failure ingestion timestamp")

    @field_validator("customer_phone_masked")
    @classmethod
    def validate_phone_masked(cls, v: str) -> str:
        if "****" not in v and len(v) > 8:
            # Enforce masking if raw phone passed accidentally
            return f"{v[:6]}****{v[-4:]}"
        return v

    @field_validator("customer_email_masked")
    @classmethod
    def validate_email_masked(cls, v: str) -> str:
        if "@" in v and "****" not in v:
            parts = v.split("@")
            user = parts[0]
            masked_user = f"{user[0]}*****{user[-1]}" if len(user) > 2 else f"{user[0]}*****"
            return f"{masked_user}@{parts[1]}"
        return v

    @property
    def is_afa_exempt(self) -> bool:
        """Returns True if category is eligible for relaxed ₹1,00,000 threshold."""
        return self.category in [
            TransactionCategory.MUTUAL_FUND,
            TransactionCategory.INSURANCE_PREMIUM,
            TransactionCategory.CREDIT_CARD_BILL,
        ]

    @property
    def statutory_afa_cap(self) -> float:
        """Returns the statutory no-AFA limit (₹15,000 or ₹1,00,000)."""
        return 100000.0 if self.is_afa_exempt else 15000.0

    @property
    def requires_afa_validation(self) -> bool:
        """True if the transaction amount exceeds the statutory AFA ceiling."""
        return self.amount > self.statutory_afa_cap

    @property
    def current_attempt_count(self) -> int:
        """Returns number of previous attempts made."""
        return len(self.attempt_history)
