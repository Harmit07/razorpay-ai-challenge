import unittest
from datetime import datetime, timezone
from src.generators.batch_generator import BatchFailureGenerator
from src.classifiers.llm_fallback import (
    LLMFallbackClassifier,
    LLMDisambiguationResult,
    PTPExtractionResult,
)
from src.classifiers.rule_classifier import RetryabilityType


class TestLLMFallback(unittest.TestCase):
    def setUp(self):
        self.llm_parser = LLMFallbackClassifier()
        self.generator = BatchFailureGenerator(seed=42)

    def test_disambiguate_switch_timeout_rc91(self):
        event = self.generator.generate_single_event(bucket_override=13, force_risk_flag=False)
        event.raw_error_description = "DECLINE_RC_91: SWITCH TIMEOUT / ISSUER INOPERATIVE / RETRY_NOT_ALLOWED"
        
        result = self.llm_parser.disambiguate_error(event)
        self.assertEqual(result.assigned_bucket_id, 2)
        self.assertEqual(result.retryability, RetryabilityType.RETRYABLE_SOFT_DEBIT)
        self.assertGreaterEqual(result.confidence, 0.85)
        # Check one-line reasoning string for audit trail
        self.assertIsInstance(result.reasoning, str)
        self.assertGreater(len(result.reasoning), 15)
        self.assertIn("switch", result.reasoning.lower())

    def test_disambiguate_dormant_kyc_suspense(self):
        event = self.generator.generate_single_event(bucket_override=13, force_risk_flag=False)
        event.raw_error_description = "AC_RESTRICTED: ACCOUNT_IN_DORMANT_SUSPENSE_STATUS_CODE_402_KYC_PENDING"
        
        result = self.llm_parser.disambiguate_error(event)
        self.assertEqual(result.assigned_bucket_id, 10)
        self.assertEqual(result.retryability, RetryabilityType.RETRYABLE_LINK_ACTION)
        self.assertIn("KYC", result.reasoning)

    def test_disambiguate_velocity_burst(self):
        event = self.generator.generate_single_event(bucket_override=13, force_risk_flag=False)
        event.raw_error_description = "CUSTOM_FILTER_TRIGGER: VELOCITY_BURST_SCORE_88_FLAGGED_BY_ISSUER_CBS"
        
        result = self.llm_parser.disambiguate_error(event)
        self.assertEqual(result.assigned_bucket_id, 4)
        self.assertEqual(result.retryability, RetryabilityType.RETRYABLE_SOFT_DEBIT)
        self.assertIn("velocity", result.reasoning.lower())

    def test_disambiguate_response_57_restriction(self):
        event = self.generator.generate_single_event(bucket_override=13, force_risk_flag=False)
        event.raw_error_description = "RESP_57_TRANSACTION_NOT_PERMITTED_TO_CARDHOLDER_SPECIAL_SECURITY_BLOCK"
        
        result = self.llm_parser.disambiguate_error(event)
        self.assertEqual(result.assigned_bucket_id, 10)
        self.assertIn("Response 57", result.reasoning)

    def test_risk_flagged_escalation(self):
        event = self.generator.generate_single_event(bucket_override=13, force_risk_flag=True)
        result = self.llm_parser.disambiguate_error(event)
        self.assertTrue(result.requires_human_escalation)
        self.assertLess(result.confidence, 0.70)
        self.assertEqual(result.routing_destination, "HUMAN_REVIEW")

    def test_unresolvable_garbage_text(self):
        event = self.generator.generate_single_event(bucket_override=13, force_risk_flag=False)
        event.raw_error_description = "XYZ_CORRUPTED_HEX_BYTE_0x9999_GARBAGE_CRASH"
        
        result = self.llm_parser.disambiguate_error(event)
        self.assertEqual(result.assigned_bucket_id, 13)
        self.assertTrue(result.requires_human_escalation)
        self.assertLess(result.confidence, 0.70)
        self.assertIn("human operator", result.reasoning.lower())

    def test_ptp_entity_extraction_hinglish_salary(self):
        transcript = "Main salary aane par 5th ko pakka ₹5000 pay kar dunga"
        ref_date = datetime(2026, 8, 27, 10, 0, tzinfo=timezone.utc)
        
        ptp = self.llm_parser.extract_ptp_entities(transcript, reference_date=ref_date)
        self.assertTrue(ptp.ptp_detected)
        self.assertEqual(ptp.promised_amount, 5000.0)
        self.assertIsNotNone(ptp.promised_date)
        self.assertEqual(ptp.promised_date.day, 5)

    def test_ptp_entity_extraction_english_invoice(self):
        transcript = "I will clear this Rs. 85,000 invoice tomorrow for sure"
        ref_date = datetime(2026, 8, 27, 10, 0, tzinfo=timezone.utc)
        
        ptp = self.llm_parser.extract_ptp_entities(transcript, reference_date=ref_date)
        self.assertTrue(ptp.ptp_detected)
        self.assertEqual(ptp.promised_amount, 85000.0)
        self.assertEqual(ptp.promised_date.day, 28)

    def test_ptp_no_commitment(self):
        transcript = "I don't know why this failed, please check your app"
        ptp = self.llm_parser.extract_ptp_entities(transcript)
        self.assertFalse(ptp.ptp_detected)


if __name__ == "__main__":
    unittest.main()
