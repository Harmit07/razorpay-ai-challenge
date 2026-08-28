"""
Three-Tier LLM Diagnostic Engine for AI Revenue Recovery Agent.

Architecture:
  Tier 1 (Regex):   Deterministic pattern matching for known bank decline signatures (~80% of cases).
                    Zero latency, zero cost, zero hallucination risk. Handles structured error codes.
  Tier 2 (LLM API): Real-time OpenRouter API calls with multi-model cascading fallback for
                    genuinely ambiguous/unmapped bank decline strings (~15% of cases).
                    Models: Gemini 2.5 Flash → Llama 4 Scout → DeepSeek R1 → NVIDIA Nemotron.
  Tier 3 (Human):   Unresolvable declines escalated to human operator queue (~5% of cases).

Also extracts Promise-to-Pay (PTP) structured entities from unstructured English/Hinglish
conversational transcripts using LLM-powered entity extraction.
"""

from __future__ import annotations
import os
import re
import json
import logging
import requests
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from pydantic import BaseModel, Field

from src.models.schema import (
    TransactionFailureEvent,
    PaymentMethod,
    ErrorSource,
    ErrorStep,
    TransactionType,
    TransactionCategory,
)
from src.classifiers.rule_classifier import RetryabilityType, DLTStream

logger = logging.getLogger(__name__)


# =====================================================================
# OpenRouter Multi-Model Cascade Configuration
# =====================================================================
from dotenv import load_dotenv
load_dotenv()  # Auto-load .env file from project root

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

# Model cascade: if one model fails or rate-limits, fall through to the next
MODEL_CASCADE = [
    {"id": "google/gemini-2.5-flash",               "name": "Gemini 2.5 Flash",        "provider": "Google"},
    {"id": "meta-llama/llama-4-scout:free",          "name": "Llama 4 Scout",           "provider": "Meta"},
    {"id": "deepseek/deepseek-r1:free",              "name": "DeepSeek R1",             "provider": "DeepSeek"},
    {"id": "nvidia/llama-3.1-nemotron-70b-instruct:free", "name": "Nemotron 70B",       "provider": "NVIDIA"},
]

# Taxonomy reference for LLM prompt context
BUCKET_TAXONOMY = {
    1:  "Insufficient Balance / Low Liquidity",
    2:  "Core Banking / Issuer Downtime",
    3:  "Gateway Timeout / Network Drop",
    4:  "Bank Velocity / Daily Limit Exceeded",
    5:  "UPI AutoPay / Collect Expired",
    6:  "3DS OTP Authentication Failure",
    7:  "Expired Card Instrument",
    8:  "Mandate Cancelled by Customer",
    9:  "Mandate Validity Expired",
    10: "Bank Security Decline (Do Not Honor)",
    11: "Amount Exceeds Statutory AFA Limit",
    12: "Checkout Drop-Off / Cart Abandonment",
    13: "Unresolved Ambiguous Bank Decline",
}

BUCKET_ACTIONS = {
    1:  "QUEUE_24H_PRE_DEBIT_ALERT_SCHEDULE_SALARY_RETRY",
    2:  "EXPONENTIAL_BACKOFF_DYNAMIC_ROUTING",
    3:  "IDEMPOTENT_POLL_RAZORPAY_FETCH_THEN_SETTLE",
    4:  "PAUSE_24H_SEND_NOTICE_RETRY_DAY_T2",
    5:  "DISPATCH_1_CLICK_UPI_INTENT_DEEP_LINK",
    6:  "DISPATCH_DYNAMIC_SESSION_RETRY_LINK",
    7:  "DISPATCH_MANDATE_UPDATE_LINK",
    8:  "PURGE_RETRIES_AND_SEND_SERVICE_CONFIRMATION",
    9:  "SEND_1_CLICK_MANDATE_RE_REGISTRATION_LINK",
    10: "SEND_UNBLOCK_INSTRUCTIONS_AND_MULTI_RAIL_LINK",
    11: "DISPATCH_DYNAMIC_AFA_OTP_LINK",
    12: "DELIVER_1_CLICK_CART_RECOVERY_LINK",
    13: "ROUTE_TO_HUMAN_OPS_QUEUE",
}

BUCKET_RETRYABILITY = {
    1:  RetryabilityType.RETRYABLE_SOFT_DEBIT,
    2:  RetryabilityType.RETRYABLE_SOFT_DEBIT,
    3:  RetryabilityType.RETRYABLE_SOFT_DEBIT,
    4:  RetryabilityType.RETRYABLE_SOFT_DEBIT,
    5:  RetryabilityType.RETRYABLE_LINK_ACTION,
    6:  RetryabilityType.RETRYABLE_LINK_ACTION,
    7:  RetryabilityType.RETRYABLE_LINK_ACTION,
    8:  RetryabilityType.NON_RETRYABLE_HARD_STOP,
    9:  RetryabilityType.RETRYABLE_LINK_ACTION,
    10: RetryabilityType.RETRYABLE_LINK_ACTION,
    11: RetryabilityType.RETRYABLE_LINK_ACTION,
    12: RetryabilityType.RETRYABLE_LINK_ACTION,
    13: RetryabilityType.UNMAPPED_AMBIGUOUS,
}


class LLMDisambiguationResult(BaseModel):
    """
    Structured outcome produced by the LLM Diagnostic Parser.
    The 'reasoning' field serves as the immutable audit trail record.
    """
    txn_id: str
    assigned_bucket_id: int
    assigned_bucket_name: str
    retryability: RetryabilityType
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str = Field(..., description="One-line auditable rationale for recovery log")
    recommended_action: str
    dlt_stream: DLTStream
    requires_human_escalation: bool = False
    routing_destination: str = "ACTION_SCHEDULED"
    model_used: str = "openrouter-cascade-v1"


class PTPExtractionResult(BaseModel):
    """Structured Promise-to-Pay entities parsed from unstructured text."""
    ptp_detected: bool
    promised_date: Optional[datetime] = None
    promised_amount: Optional[float] = None
    condition: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    raw_transcript_snippet: str


def _build_classification_prompt(raw_text: str, error_code: str, error_source: str, method: str) -> str:
    """Builds the structured classification prompt for the LLM."""
    bucket_list = "\n".join([f"  {bid}: {bname}" for bid, bname in BUCKET_TAXONOMY.items()])

    return f"""You are an expert Indian payment failure diagnostic engine for Razorpay.
Your task is to classify an ambiguous bank decline message into exactly ONE of the following error buckets.

ERROR BUCKETS:
{bucket_list}

TRANSACTION CONTEXT:
- Raw Bank Decline Text: "{raw_text}"
- Razorpay Error Code: {error_code}
- Error Source: {error_source}
- Payment Method: {method}

INSTRUCTIONS:
1. Analyze the raw decline text and transaction context.
2. Assign exactly ONE bucket_id (1-13) that best matches the root cause.
3. Provide a confidence score between 0.0 and 1.0.
4. Write a one-line reasoning explaining your classification decision.
5. If you cannot confidently classify (confidence < 0.70), assign bucket_id 13.

Respond ONLY with valid JSON in this exact format (no markdown, no explanation):
{{"bucket_id": <int>, "confidence": <float>, "reasoning": "<one-line string>"}}"""


def _build_ptp_extraction_prompt(transcript: str, reference_date: datetime) -> str:
    """Builds the PTP entity extraction prompt for the LLM with explicit reference date."""
    ref_date_str = reference_date.strftime("%Y-%m-%d")
    tomorrow_str = (reference_date + timedelta(days=1)).strftime("%Y-%m-%d")
    return f"""You are a payment recovery NLU engine specialized in Indian English and Hinglish.
Extract Promise-to-Pay (PTP) entities from this customer conversation transcript.

CURRENT CONTEXT:
- Today's Reference Date: {ref_date_str} (UTC)
- Tomorrow's Date: {tomorrow_str}

TRANSCRIPT:
"{transcript}"

INSTRUCTIONS:
1. Detect if the customer is promising to pay (ptp_detected: true/false).
2. Extract the promised amount in INR if mentioned (e.g., "5000", "5k" = 5000, "1.5L" = 150000).
3. Extract the promised date as an ISO-8601 date string (YYYY-MM-DD) based on Today's Reference Date ({ref_date_str}):
   - "kal" / "tomorrow" = {tomorrow_str}
   - "salary aane do" / "salary" = 1st of next month
   - "5th ko" / "on 5th" = 5th of current/next month
4. Extract any conditions mentioned (e.g., "after salary", "by weekend").
5. Assign a confidence score between 0.0 and 1.0.

Respond ONLY with valid JSON in this exact format (no markdown, no explanation):
{{"ptp_detected": <bool>, "amount": <float|null>, "date": "<YYYY-MM-DD|null>", "condition": "<string|null>", "confidence": <float>}}"""


def _call_openrouter(prompt: str, max_tokens: int = 256) -> Tuple[Optional[str], str]:
    """
    Calls OpenRouter API with multi-model cascading fallback.
    Returns: (response_text, model_used) or (None, "none") if all models fail.
    """
    if not OPENROUTER_API_KEY:
        logger.warning("OPENROUTER_API_KEY not set. Falling back to regex-only mode.")
        return None, "no-api-key"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/Harmit07/razorpay-ai-challenge",
        "X-Title": "Razorpay AI Revenue Recovery Agent",
    }

    for model_spec in MODEL_CASCADE:
        model_id = model_spec["id"]
        model_name = model_spec["name"]
        try:
            payload = {
                "model": model_id,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a payment failure classification engine. Respond ONLY with valid JSON. No markdown, no explanation, no code fences."
                    },
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": max_tokens,
                "temperature": 0.1,  # Low temperature for deterministic classification
                "top_p": 0.9,
            }

            response = requests.post(
                OPENROUTER_API_URL,
                headers=headers,
                json=payload,
                timeout=15,
            )

            if response.status_code == 429:
                # Rate limited on this model -> try next model in cascade
                logger.info(f"OpenRouter rate limit on {model_name}, cascading to next model...")
                continue

            if response.status_code != 200:
                logger.warning(f"OpenRouter error {response.status_code} on {model_name}: {response.text[:200]}")
                continue

            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if content:
                actual_model = data.get("model", model_id)
                logger.info(f"OpenRouter success via {model_name} (actual: {actual_model})")
                return content.strip(), model_name
            else:
                logger.warning(f"Empty response from {model_name}")
                continue

        except requests.exceptions.Timeout:
            logger.warning(f"OpenRouter timeout on {model_name}, cascading...")
            continue
        except requests.exceptions.ConnectionError:
            logger.warning(f"OpenRouter connection error on {model_name}, cascading...")
            continue
        except Exception as e:
            logger.warning(f"OpenRouter unexpected error on {model_name}: {e}")
            continue

    logger.warning("All OpenRouter models exhausted. Falling back to regex/human escalation.")
    return None, "all-models-exhausted"


def _parse_llm_json(raw_response: str) -> Optional[Dict[str, Any]]:
    """Safely parses LLM JSON response, handling common formatting issues."""
    if not raw_response:
        return None

    # Strip markdown code fences if the model included them despite instructions
    cleaned = raw_response.strip()
    if cleaned.startswith("```"):
        # Remove opening fence (```json or ```)
        first_newline = cleaned.index("\n") if "\n" in cleaned else len(cleaned)
        cleaned = cleaned[first_newline + 1:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find JSON object within the response
        match = re.search(r'\{[^{}]*\}', cleaned)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return None


class LLMFallbackClassifier:
    """
    Three-Tier LLM Diagnostic Engine.

    Tier 1: Deterministic regex pattern matching for known bank decline signatures.
    Tier 2: Real-time OpenRouter API with multi-model cascading fallback.
    Tier 3: Human operator escalation for genuinely unresolvable cases.
    """

    SEMANTIC_ERROR_PATTERNS = [
        # Pattern 1: Switch / Inter-bank routing drops -> Bucket 2 (Core Banking Outage)
        {
            "pattern": r"(?i)(switch.*unavailable|rc[-_]?91|issuer.*inoperative|cbs.*socket.*closed|cbs.*error.*ext|dropped.*packet|routing.*failure)",
            "bucket_id": 2,
            "bucket_name": "Core Banking / Issuer Downtime",
            "retryability": RetryabilityType.RETRYABLE_SOFT_DEBIT,
            "confidence": 0.91,
            "reasoning": "Unstructured decline indicates temporary NPCI switch/issuer CBS routing timeout; safe for automated retry with exponential backoff.",
            "recommended_action": "EXPONENTIAL_BACKOFF_DYNAMIC_ROUTING",
            "dlt_stream": DLTStream.SERVICE_IMPLICIT,
            "routing_destination": "ACTION_SCHEDULED",
        },
        # Pattern 2: Dormant / Suspense account / KYC freeze -> Bucket 10 (Bank Security Decline)
        {
            "pattern": r"(?i)(account.*dormant|suspense.*status|kyc.*pending|ac.*restricted|code[-_]?402)",
            "bucket_id": 10,
            "bucket_name": "Bank Security Decline (Do Not Honor)",
            "retryability": RetryabilityType.RETRYABLE_LINK_ACTION,
            "confidence": 0.89,
            "reasoning": "Issuer flagged account as dormant/KYC restricted; direct auto-debit halted; dispatched unblocking instructions & alternate payment link.",
            "recommended_action": "SEND_UNBLOCK_INSTRUCTIONS_AND_MULTI_RAIL_LINK",
            "dlt_stream": DLTStream.SERVICE_IMPLICIT,
            "routing_destination": "ACTION_SCHEDULED",
        },
        # Pattern 3: Velocity / Burst limits -> Bucket 4 (Velocity Limit Exceeded)
        {
            "pattern": r"(?i)(velocity.*burst|frequency.*exceeded|limit.*restricted.*by.*issuer|velocity.*score)",
            "bucket_id": 4,
            "bucket_name": "Bank Velocity / Daily Limit Exceeded",
            "retryability": RetryabilityType.RETRYABLE_SOFT_DEBIT,
            "confidence": 0.88,
            "reasoning": "Bank response indicates temporary transaction frequency/velocity cap exceeded; retry scheduled for next calendar day after cooling.",
            "recommended_action": "PAUSE_24H_SEND_NOTICE_RETRY_DAY_T2",
            "dlt_stream": DLTStream.SERVICE_IMPLICIT,
            "routing_destination": "ACTION_SCHEDULED",
        },
        # Pattern 4: Cardholder security restrictions -> Bucket 10 (Bank Security Decline)
        {
            "pattern": r"(?i)(resp[-_]?57|not.*permitted.*to.*cardholder|special.*security.*block|security.*filter.*flag)",
            "bucket_id": 10,
            "bucket_name": "Bank Security Decline (Do Not Honor)",
            "retryability": RetryabilityType.RETRYABLE_LINK_ACTION,
            "confidence": 0.87,
            "reasoning": "Response 57 cardholder permission block requires user to enable e-mandate channel permissions in issuer banking app.",
            "recommended_action": "SEND_UNBLOCK_INSTRUCTIONS_AND_MULTI_RAIL_LINK",
            "dlt_stream": DLTStream.SERVICE_IMPLICIT,
            "routing_destination": "ACTION_SCHEDULED",
        },
        # Pattern 5: Balance / Liquidity indicators -> Bucket 1 (Insufficient Funds)
        {
            "pattern": r"(?i)(balance.*low|fund.*unavailable|insufficient|shortfall|low.*liquidity)",
            "bucket_id": 1,
            "bucket_name": "Insufficient Balance / Low Liquidity",
            "retryability": RetryabilityType.RETRYABLE_SOFT_DEBIT,
            "confidence": 0.92,
            "reasoning": "Unstructured decline parsed as account liquidity shortfall; queuing 24h statutory pre-debit alert with salary cycle snapping.",
            "recommended_action": "QUEUE_24H_PRE_DEBIT_ALERT_SCHEDULE_SALARY_RETRY",
            "dlt_stream": DLTStream.SERVICE_IMPLICIT,
            "routing_destination": "ACTION_SCHEDULED",
        },
        # Pattern 6: Authentication / Session timeouts -> Bucket 6 (3DS Authentication Failure)
        {
            "pattern": r"(?i)(otp.*expired|auth.*drop|session.*timeout|3ds.*fail|pin.*incorrect)",
            "bucket_id": 6,
            "bucket_name": "3DS OTP Authentication Failure",
            "retryability": RetryabilityType.RETRYABLE_LINK_ACTION,
            "confidence": 0.90,
            "reasoning": "Authentication drop detected; direct debit suppressed to prevent fraud lockout; dispatched 1-click dynamic session payment link.",
            "recommended_action": "DISPATCH_DYNAMIC_SESSION_RETRY_LINK",
            "dlt_stream": DLTStream.SERVICE_IMPLICIT,
            "routing_destination": "ACTION_SCHEDULED",
        },
        # Pattern 7: Corrupted / Garbage / Unresolvable crash dump -> Bucket 13 (Human Review)
        {
            "pattern": r"(?i)(corrupted.*hex|garbage.*crash|unresolvable|corrupted.*byte|raw_dump)",
            "bucket_id": 13,
            "bucket_name": "Unresolved Ambiguous Bank Decline",
            "retryability": RetryabilityType.UNMAPPED_AMBIGUOUS,
            "confidence": 0.50,
            "reasoning": "Bank error string is corrupted or unresolvable; escalating to human operator queue for manual triage.",
            "recommended_action": "ROUTE_TO_HUMAN_OPS_QUEUE",
            "dlt_stream": DLTStream.SERVICE_IMPLICIT,
            "routing_destination": "HUMAN_REVIEW",
        },
    ]

    def disambiguate_error(self, event: TransactionFailureEvent) -> LLMDisambiguationResult:
        """
        Three-tier diagnostic disambiguation:
        1. Risk/Dispute safety gate (immediate quarantine)
        2. Regex pattern matching (fast, deterministic, ~80% of ambiguous declines)
        3. OpenRouter LLM API with multi-model cascade (genuinely unresolvable declines)
        4. Human escalation fallback (when all models fail)
        """
        raw_text = event.raw_error_description or event.error_reason or ""

        # ─────────────────────────────────────────────────────────────
        # TIER 0: Risk/Dispute Safety Gate (Immediate Quarantine)
        # ─────────────────────────────────────────────────────────────
        if event.risk_flag or event.dispute_active:
            return LLMDisambiguationResult(
                txn_id=event.txn_id,
                assigned_bucket_id=0,
                assigned_bucket_name="High Risk Flagged Decline",
                retryability=RetryabilityType.UNMAPPED_AMBIGUOUS,
                confidence=0.55,
                reasoning="Decline text carries independent fraud/risk indicator; automated dunning halted and routed to Human Ops for manual audit.",
                recommended_action="ESCALATE_TO_RISK_OPS_FOR_MANUAL_TRIAGE",
                dlt_stream=DLTStream.SERVICE_IMPLICIT,
                requires_human_escalation=True,
                routing_destination="HUMAN_REVIEW",
                model_used="safety-gate-v1",
            )

        # ─────────────────────────────────────────────────────────────
        # TIER 1: Deterministic Regex Pattern Matching (Fast Path)
        # ─────────────────────────────────────────────────────────────
        for spec in self.SEMANTIC_ERROR_PATTERNS:
            if re.search(spec["pattern"], raw_text):
                return LLMDisambiguationResult(
                    txn_id=event.txn_id,
                    assigned_bucket_id=spec["bucket_id"],
                    assigned_bucket_name=spec["bucket_name"],
                    retryability=spec["retryability"],
                    confidence=spec["confidence"],
                    reasoning=spec["reasoning"],
                    recommended_action=spec["recommended_action"],
                    dlt_stream=spec["dlt_stream"],
                    requires_human_escalation=spec.get("requires_human_escalation", (spec["bucket_id"] == 13) or (spec["confidence"] < 0.70)),
                    routing_destination=spec["routing_destination"],
                    model_used="regex-pattern-engine-v1",
                )

        # ─────────────────────────────────────────────────────────────
        # TIER 2: OpenRouter LLM API with Multi-Model Cascade
        # ─────────────────────────────────────────────────────────────
        prompt = _build_classification_prompt(
            raw_text=raw_text,
            error_code=event.error_code,
            error_source=event.error_source.value,
            method=event.method.value,
        )

        llm_response, model_name = _call_openrouter(prompt)
        parsed = _parse_llm_json(llm_response) if llm_response else None

        if parsed and "bucket_id" in parsed:
            bucket_id = int(parsed["bucket_id"])
            confidence = float(parsed.get("confidence", 0.75))
            reasoning = str(parsed.get("reasoning", f"LLM classified decline to Bucket {bucket_id}"))

            # Validate bucket_id is in valid range
            if bucket_id not in BUCKET_TAXONOMY:
                bucket_id = 13
                confidence = 0.50

            # Clamp confidence to valid range
            confidence = max(0.0, min(1.0, confidence))
            if bucket_id == 13:
                confidence = min(confidence, 0.50)

            bucket_name = BUCKET_TAXONOMY.get(bucket_id, "Unresolved Ambiguous Bank Decline")
            retryability = BUCKET_RETRYABILITY.get(bucket_id, RetryabilityType.UNMAPPED_AMBIGUOUS)
            action = BUCKET_ACTIONS.get(bucket_id, "ROUTE_TO_HUMAN_OPS_QUEUE")

            is_escalation = (confidence < 0.70) or (bucket_id == 13)
            routing = "HUMAN_REVIEW" if is_escalation else "ACTION_SCHEDULED"
            if is_escalation and "human operator" not in reasoning.lower():
                reasoning = f"{reasoning} Escalating to Human Operator queue for manual triage."

            return LLMDisambiguationResult(
                txn_id=event.txn_id,
                assigned_bucket_id=bucket_id,
                assigned_bucket_name=bucket_name,
                retryability=retryability,
                confidence=confidence,
                reasoning=f"[LLM/{model_name}] {reasoning}",
                recommended_action=action,
                dlt_stream=DLTStream.SERVICE_IMPLICIT,
                requires_human_escalation=is_escalation,
                routing_destination=routing,
                model_used=f"openrouter/{model_name}",
            )

        # ─────────────────────────────────────────────────────────────
        # TIER 3: Human Escalation Fallback (All Models Exhausted)
        # ─────────────────────────────────────────────────────────────
        return LLMDisambiguationResult(
            txn_id=event.txn_id,
            assigned_bucket_id=13,
            assigned_bucket_name="Unresolved Ambiguous Bank Decline",
            retryability=RetryabilityType.UNMAPPED_AMBIGUOUS,
            confidence=0.50,
            reasoning=f"Bank error string '{raw_text[:80]}' could not be resolved by regex or LLM cascade ({model_name}); escalating to human operator queue.",
            recommended_action="ROUTE_TO_HUMAN_OPS_QUEUE",
            dlt_stream=DLTStream.SERVICE_IMPLICIT,
            requires_human_escalation=True,
            routing_destination="HUMAN_REVIEW",
            model_used=f"fallback-human/{model_name}",
        )

    def extract_ptp_entities(self, transcript: str, reference_date: Optional[datetime] = None) -> PTPExtractionResult:
        """
        Extracts Promise-to-Pay (PTP) entities from unstructured English/Hinglish transcripts.
        Uses LLM for complex cases, falls back to regex for simple patterns.
        """
        if reference_date is None:
            reference_date = datetime.now(timezone.utc)

        lower = transcript.lower()

        # ─────────────────────────────────────────────────────────────
        # Quick rejection: no PTP intent detected at all
        # ─────────────────────────────────────────────────────────────
        ptp_intent_patterns = [
            r"(?i)(pay|clear|settle|de dunga|bhej dunga|karta hu|transfer|karoonga|kar dunga)",
        ]
        has_ptp_intent = any(re.search(p, lower) for p in ptp_intent_patterns)
        if not has_ptp_intent:
            return PTPExtractionResult(
                ptp_detected=False,
                confidence=0.10,
                raw_transcript_snippet=transcript,
            )

        # ─────────────────────────────────────────────────────────────
        # Try LLM-powered PTP extraction first (if API key available)
        # ─────────────────────────────────────────────────────────────
        if OPENROUTER_API_KEY:
            ptp_prompt = _build_ptp_extraction_prompt(transcript, reference_date)
            llm_response, model_name = _call_openrouter(ptp_prompt, max_tokens=200)
            parsed = _parse_llm_json(llm_response) if llm_response else None

            if parsed and "ptp_detected" in parsed:
                ptp_detected = bool(parsed["ptp_detected"])
                if not ptp_detected:
                    return PTPExtractionResult(
                        ptp_detected=False,
                        confidence=float(parsed.get("confidence", 0.85)),
                        raw_transcript_snippet=transcript,
                    )

                # Parse extracted date
                promised_date = None
                date_str = parsed.get("date")
                if date_str:
                    try:
                        clean_date_str = str(date_str).replace("Z", "+00:00")
                        if len(clean_date_str) == 10:  # YYYY-MM-DD
                            dt = datetime.strptime(clean_date_str, "%Y-%m-%d")
                            promised_date = dt.replace(hour=10, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
                        else:
                            promised_date = datetime.fromisoformat(clean_date_str)
                    except (ValueError, TypeError):
                        # If LLM returned a relative date description, handle it
                        if "tomorrow" in str(date_str).lower() or "kal" in str(date_str).lower():
                            promised_date = reference_date + timedelta(days=1)
                        else:
                            promised_date = reference_date + timedelta(days=3)

                return PTPExtractionResult(
                    ptp_detected=True,
                    promised_date=promised_date,
                    promised_amount=parsed.get("amount"),
                    condition=parsed.get("condition"),
                    confidence=float(parsed.get("confidence", 0.88)),
                    raw_transcript_snippet=transcript,
                )

        # ─────────────────────────────────────────────────────────────
        # Regex fallback for PTP extraction (when LLM unavailable)
        # ─────────────────────────────────────────────────────────────
        amount = None
        amt_match = re.search(r"(?:₹|rs\.?|inr)?\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+)\s*(k|lakh|lac|l)?\b", lower)
        if amt_match:
            val_str = amt_match.group(1).replace(",", "")
            multiplier = 1.0
            unit = amt_match.group(2)
            if unit == "k":
                multiplier = 1000.0
            elif unit in ["lakh", "lac", "l"]:
                multiplier = 100000.0
            amount = float(val_str) * multiplier

        # Extract Date / Timing Commitment
        promised_date = None
        condition = None

        # Look for specific date mentions: "5th", "10th", "25th", "on 5 september"
        day_match = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s*(?:ko|of|\b)", lower)
        if day_match and int(day_match.group(1)) <= 31:
            target_day = int(day_match.group(1))
            year = reference_date.year
            month = reference_date.month
            if target_day < reference_date.day:
                # Next month
                month = month + 1 if month < 12 else 1
                year = year + 1 if month == 1 else year
            # Clamping to valid days in month
            max_days = 28 if month == 2 else (30 if month in [4, 6, 9, 11] else 31)
            target_day = min(target_day, max_days)
            promised_date = reference_date.replace(year=year, month=month, day=target_day, hour=10, minute=0, second=0, microsecond=0)
            condition = f"Specific day: {target_day}th of month"

        # Look for relative day mentions if no explicit date was parsed
        if promised_date is None:
            if "kal" in lower or "tomorrow" in lower:
                promised_date = reference_date + timedelta(days=1)
                condition = "Tomorrow / Kal"
            elif "salary" in lower:
                # Snap to 1st of next month
                year = reference_date.year
                month = reference_date.month + 1 if reference_date.month < 12 else 1
                year = year + 1 if month == 1 else year
                promised_date = reference_date.replace(year=year, month=month, day=1, hour=10, minute=0, second=0, microsecond=0)
                condition = "Salary credit cycle (1st of month)"
            else:
                promised_date = reference_date + timedelta(days=3)
                condition = "Default short-term grace (3 days)"

        return PTPExtractionResult(
            ptp_detected=True,
            promised_date=promised_date,
            promised_amount=amount,
            condition=condition,
            confidence=0.92,
            raw_transcript_snippet=transcript,
        )
