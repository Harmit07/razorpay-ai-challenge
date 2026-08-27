import unittest
from datetime import datetime, timezone
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


class TestSchema(unittest.TestCase):
    def test_valid_transaction_creation(self):
        event = TransactionFailureEvent(
            txn_id="pay_01HZ89K12",
            amount=4999.00,
            method=PaymentMethod.UPI_AUTOPAY,
            error_code="BAD_REQUEST_ERROR",
            error_source=ErrorSource.CUSTOMER,
            error_step=ErrorStep.PAYMENT_AUTHORIZATION,
            error_reason="insufficient_funds",
            txn_type=TransactionType.RECURRING_SUBSCRIPTION,
            mandate_id="man_01HZ89K12",
            category=TransactionCategory.STANDARD,
            customer_id="cust_01HZ89K12",
            customer_phone_masked="+91-9812345678",
            customer_email_masked="rahul.verma@example.com",
        )

        self.assertEqual(event.txn_id, "pay_01HZ89K12")
        self.assertEqual(event.amount, 4999.00)
        self.assertEqual(event.method, PaymentMethod.UPI_AUTOPAY)
        self.assertFalse(event.requires_afa_validation)
        self.assertEqual(event.statutory_afa_cap, 15000.00)
        # Verify automatic PII masking validator
        self.assertTrue("****" in event.customer_phone_masked)
        self.assertTrue("*****" in event.customer_email_masked)

    def test_afa_limits_and_exemptions(self):
        # 1. Standard Category: ₹16,000 exceeds ₹15,000 cap
        event_standard = TransactionFailureEvent(
            txn_id="pay_std_1",
            amount=16000.00,
            method=PaymentMethod.CARD,
            error_code="BAD_REQUEST_ERROR",
            error_source=ErrorSource.BUSINESS,
            error_step=ErrorStep.PAYMENT_INITIATION,
            error_reason="amount_exceeds_statutory_afa_limit",
            category=TransactionCategory.STANDARD,
            customer_id="cust_1",
            customer_phone_masked="+91-98****9012",
            customer_email_masked="u*****r@example.com",
        )
        self.assertTrue(event_standard.requires_afa_validation)
        self.assertEqual(event_standard.statutory_afa_cap, 15000.00)

        # 2. Mutual Fund (SIP): ₹75,000 is under ₹1,00,000 cap
        event_sip = TransactionFailureEvent(
            txn_id="pay_sip_1",
            amount=75000.00,
            method=PaymentMethod.NACH,
            error_code="BAD_REQUEST_ERROR",
            error_source=ErrorSource.CUSTOMER,
            error_step=ErrorStep.PAYMENT_AUTHORIZATION,
            error_reason="insufficient_funds",
            category=TransactionCategory.MUTUAL_FUND,
            customer_id="cust_2",
            customer_phone_masked="+91-98****9012",
            customer_email_masked="u*****r@example.com",
        )
        self.assertFalse(event_sip.requires_afa_validation)
        self.assertEqual(event_sip.statutory_afa_cap, 100000.00)

        # 3. Insurance Premium: ₹1,20,000 exceeds ₹1,00,000 cap
        event_ins = TransactionFailureEvent(
            txn_id="pay_ins_1",
            amount=120000.00,
            method=PaymentMethod.CARD,
            error_code="BAD_REQUEST_ERROR",
            error_source=ErrorSource.BUSINESS,
            error_step=ErrorStep.PAYMENT_INITIATION,
            error_reason="amount_exceeds_statutory_afa_limit",
            category=TransactionCategory.INSURANCE_PREMIUM,
            customer_id="cust_3",
            customer_phone_masked="+91-98****9012",
            customer_email_masked="u*****r@example.com",
        )
        self.assertTrue(event_ins.requires_afa_validation)
        self.assertEqual(event_ins.statutory_afa_cap, 100000.00)

    def test_attempt_history_and_ptp_tracking(self):
        now = datetime.now(timezone.utc)
        event = TransactionFailureEvent(
            txn_id="pay_ptp_1",
            amount=2999.00,
            method=PaymentMethod.UPI_AUTOPAY,
            error_code="BAD_REQUEST_ERROR",
            error_source=ErrorSource.CUSTOMER,
            error_step=ErrorStep.PAYMENT_AUTHORIZATION,
            error_reason="insufficient_funds",
            customer_id="cust_4",
            customer_phone_masked="+91-98****9012",
            customer_email_masked="u*****r@example.com",
            attempt_history=[
                AttemptRecord(
                    attempt_number=1,
                    timestamp=now,
                    channel="PRE_DEBIT_ALERT",
                    status=AttemptStatus.PRE_DEBIT_DELIVERED,
                )
            ],
            ptp_record=PromiseToPayRecord(
                promised_date=now,
                promised_amount=2999.00,
                grace_until=now,
                status="ACTIVE",
            ),
        )

        self.assertEqual(event.current_attempt_count, 1)
        self.assertIsNotNone(event.ptp_record)
        self.assertEqual(event.ptp_record.status, "ACTIVE")


if __name__ == "__main__":
    unittest.main()
