"""
AI Recovery Decision Agent — P0 Track 3 Enhancement.

This module implements the LLM-powered agent reasoning layer that sits BETWEEN
the diagnostic classifier and the compliance router.

Architecture:
  1. Classifier diagnoses the ROOT CAUSE (which bucket + retryability).
  2. THIS AGENT reasons about WHICH recovery action to take, given context.
  3. ComplianceRouter validates the agent's choice against hard statutory guards.
  4. ComplianceEnforcer enforces invariants — the agent can NEVER bypass them.

The agent is given a menu of compliant action options (derived from the bucket)
and uses structured LLM output to select the best one with full reasoning.

Gracefully degrades to deterministic router if LLM is unavailable (100% offline safe).
"""

from __future__ import annotations

import os
import re
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from pydantic import BaseModel, Field

from src.models.schema import TransactionFailureEvent, TransactionType
from src.classifiers.rule_classifier import ClassificationResult, RetryabilityType

logger = logging.getLogger(__name__)

from dotenv import load_dotenv
load_dotenv()

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

AGENT_MODEL_CASCADE = [
    {"id": "google/gemini-2.5-flash", "name": "Gemini 2.5 Flash"},
    {"id": "meta-llama/llama-4-scout:free", "name": "Llama 4 Scout"},
    {"id": "deepseek/deepseek-r1:free", "name": "DeepSeek R1"},
    {"id": "nvidia/llama-3.1-nemotron-70b-instruct:free", "name": "Nemotron 70B"},
]

# Available compliant actions per bucket — agent chooses among these
BUCKET_ACTION_MENU = {
    1:  ["AUTO_DEBIT_RETRY", "WHATSAPP_UPI_INTENT", "VOICE_RECOVERY_CALL"],
    2:  ["AUTO_DEBIT_RETRY", "WHATSAPP_UPI_INTENT"],
    3:  ["AUTO_DEBIT_RETRY", "WHATSAPP_UPI_INTENT"],
    4:  ["AUTO_DEBIT_RETRY", "DYNAMIC_AFA_PAYMENT_LINK"],
    5:  ["WHATSAPP_UPI_INTENT", "DYNAMIC_AFA_PAYMENT_LINK"],
    6:  ["DYNAMIC_AFA_PAYMENT_LINK", "WHATSAPP_UPI_INTENT"],
    7:  ["DYNAMIC_INSTRUMENT_UPDATE_LINK"],
    8:  ["STOP_TERMINATION"],
    9:  ["DYNAMIC_INSTRUMENT_UPDATE_LINK"],
    10: ["DYNAMIC_AFA_PAYMENT_LINK", "WHATSAPP_UPI_INTENT", "VOICE_RECOVERY_CALL"],
    11: ["DYNAMIC_AFA_PAYMENT_LINK"],
    12: ["DYNAMIC_AFA_PAYMENT_LINK", "WHATSAPP_UPI_INTENT"],
    13: ["HUMAN_OPS_REVIEW"],
}

CHANNEL_MAP = {
    "AUTO_DEBIT_RETRY": "AUTO_DEBIT_API",
    "DYNAMIC_AFA_PAYMENT_LINK": "WHATSAPP",
    "DYNAMIC_INSTRUMENT_UPDATE_LINK": "WHATSAPP",
    "WHATSAPP_UPI_INTENT": "WHATSAPP",
    "VOICE_RECOVERY_CALL": "VOICE_BOT",
    "STOP_TERMINATION": "INTERNAL_PORTAL",
    "HUMAN_OPS_REVIEW": "INTERNAL_PORTAL",
    "CHECKOUT_DROP_OFF_RECOVERY": "WHATSAPP",
    "MSMED_FINANCE_ESCALATION": "EMAIL",
    "PTP_HOLD_FREEZE": "INTERNAL_PORTAL",
}

# Buckets for which the agent reasons (multi-option ambiguous cases)
AGENT_ELIGIBLE_BUCKETS = {1, 5, 6, 10, 12}


class AgentDecision(BaseModel):
    """Structured output from the AI Recovery Decision Agent."""
    txn_id: str
    chosen_action: str
    chosen_channel: str
    reasoning: str = Field(..., description="One-sentence agent rationale for audit log")
    confidence: float = Field(..., ge=0.0, le=1.0)
    agent_model_used: str = "deterministic-fallback"
    agent_used: bool = False
    alternatives_considered: List[str] = Field(default_factory=list)
    ev_justification: Optional[str] = None


def _build_agent_prompt(
    event: TransactionFailureEvent,
    diag: ClassificationResult,
    action_menu: List[str],
) -> str:
    """Constructs the structured agent reasoning prompt."""
    amount = event.amount
    method = event.method.value
    bucket_name = diag.bucket_name
    attempt_no = event.current_attempt_count + 1
    is_dnd = event.is_dnd
    amount_str = f"₹{amount:,.2f}"

    menu_str = "\n".join([f"  - {a}" for a in action_menu])
    ev_hints = []
    if "AUTO_DEBIT_RETRY" in action_menu:
        ev_hints.append("AUTO_DEBIT_RETRY: 68% recovery prob, ₹0 cost, best for salary-day retries")
    if "WHATSAPP_UPI_INTENT" in action_menu:
        ev_hints.append("WHATSAPP_UPI_INTENT: 74% recovery prob, ₹0.15 cost, best for UPI-enabled customers")
    if "VOICE_RECOVERY_CALL" in action_menu:
        ev_hints.append("VOICE_RECOVERY_CALL: 65% recovery prob, ₹3.50 cost, best for repeated failures needing human touch")
    if "DYNAMIC_AFA_PAYMENT_LINK" in action_menu:
        ev_hints.append("DYNAMIC_AFA_PAYMENT_LINK: 62% recovery prob, ₹0.15 cost, required for amounts above AFA cap")
    if "DYNAMIC_INSTRUMENT_UPDATE_LINK" in action_menu:
        ev_hints.append("DYNAMIC_INSTRUMENT_UPDATE_LINK: 52% recovery prob, ₹0.15 cost, for expired cards/mandates")

    ev_str = "\n".join([f"  - {h}" for h in ev_hints]) if ev_hints else "  - See action list"

    return f"""You are an AI Revenue Recovery Agent for Razorpay, deciding the optimal recovery action for a failed payment.

TRANSACTION CONTEXT:
- Transaction ID: {event.txn_id}
- Amount: {amount_str}
- Payment Method: {method}
- Failure Bucket: {diag.bucket_id} — {bucket_name}
- Attempt Number: #{attempt_no}
- Customer DND Registered: {is_dnd}
- Transaction Type: {event.txn_type.value}

AVAILABLE RECOVERY ACTIONS (all are compliance-validated):
{menu_str}

EXPECTED VALUE (EV) REFERENCE — EV = (P_recover × Amount) - Channel_Cost:
{ev_str}

YOUR TASK:
Select the single BEST recovery action from the available options above.
Consider: (1) highest net EV, (2) lowest customer annoyance, (3) regulatory constraints (DND if true = no voice), (4) payment method fit.

Respond ONLY with valid JSON (no markdown, no explanation outside JSON):
{{"chosen_action": "<ACTION_NAME>", "confidence": <float 0.0-1.0>, "reasoning": "<one sentence audit rationale>", "ev_justification": "<brief EV math>"}}"""


def _call_agent_openrouter(prompt: str) -> Tuple[Optional[Dict], str]:
    """Calls OpenRouter with agent model cascade. Returns (parsed_json, model_used)."""
    if not OPENROUTER_API_KEY:
        return None, "no-api-key"

    try:
        import requests
    except ImportError:
        return None, "requests-not-installed"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/razorpay-ai-challenge",
        "X-Title": "Razorpay AI Recovery Agent",
    }

    for model in AGENT_MODEL_CASCADE:
        try:
            payload = {
                "model": model["id"],
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 300,
                "temperature": 0.1,
            }
            resp = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=12)
            if resp.status_code != 200:
                logger.warning(f"[AgentLLM] {model['name']} HTTP {resp.status_code}, trying next model.")
                continue

            raw = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()

            # Strip markdown fences if present
            raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
            raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE)

            parsed = json.loads(raw)
            logger.info(f"[AgentLLM] {model['name']} responded: chosen_action={parsed.get('chosen_action')}")
            return parsed, model["name"]

        except json.JSONDecodeError as e:
            logger.warning(f"[AgentLLM] {model['name']} JSON parse error: {e}")
            continue
        except Exception as e:
            logger.warning(f"[AgentLLM] {model['name']} error: {e}")
            continue

    return None, "all-models-failed"


class RecoveryDecisionAgent:
    """
    LLM-powered AI agent that selects the optimal recovery action for a failed payment.

    Sits between the classifier (root cause) and the compliance router (hard invariants).
    Only reasons about WHICH compliant action to take — never bypasses statutory guards.
    Falls back to deterministic routing if LLM is unavailable.
    """

    def decide(
        self,
        event: TransactionFailureEvent,
        diag: ClassificationResult,
    ) -> AgentDecision:
        """
        Decides the optimal recovery action given the classified failure and transaction context.

        Args:
            event: The full transaction failure event.
            diag: Classification result from rule/LLM classifier.

        Returns:
            AgentDecision with chosen_action, reasoning, confidence, and model attribution.
        """
        bucket_id = diag.bucket_id
        action_menu = BUCKET_ACTION_MENU.get(bucket_id, ["HUMAN_OPS_REVIEW"])

        # If only one option, no need for agent reasoning
        if len(action_menu) == 1:
            chosen = action_menu[0]
            return AgentDecision(
                txn_id=event.txn_id,
                chosen_action=chosen,
                chosen_channel=CHANNEL_MAP.get(chosen, "INTERNAL_PORTAL"),
                reasoning=f"Single compliant action available for Bucket {bucket_id}: {chosen}. No agent reasoning required.",
                confidence=1.0,
                agent_model_used="single-option-deterministic",
                agent_used=False,
                alternatives_considered=[],
            )

        # Apply DND constraint — remove voice if DND customer
        if event.is_dnd and "VOICE_RECOVERY_CALL" in action_menu:
            action_menu = [a for a in action_menu if a != "VOICE_RECOVERY_CALL"]

        # If bucket not in agent-eligible set, return deterministic best
        if bucket_id not in AGENT_ELIGIBLE_BUCKETS or not action_menu:
            chosen = action_menu[0] if action_menu else "HUMAN_OPS_REVIEW"
            return AgentDecision(
                txn_id=event.txn_id,
                chosen_action=chosen,
                chosen_channel=CHANNEL_MAP.get(chosen, "INTERNAL_PORTAL"),
                reasoning=f"Deterministic selection for Bucket {bucket_id}: {chosen} (highest conversion rate for this failure class).",
                confidence=0.92,
                agent_model_used="deterministic-rule-fallback",
                agent_used=False,
                alternatives_considered=action_menu[1:],
            )

        # Call LLM agent
        prompt = _build_agent_prompt(event, diag, action_menu)
        parsed, model_name = _call_agent_openrouter(prompt)

        if parsed and "chosen_action" in parsed:
            raw_action = parsed["chosen_action"].upper().strip()
            # Validate the LLM chose a valid action from the menu
            if raw_action not in action_menu:
                logger.warning(f"[AgentLLM] LLM chose {raw_action} not in menu {action_menu}. Fallback to first option.")
                raw_action = action_menu[0]
                model_name = "deterministic-fallback-invalid-choice"
                agent_used = False
            else:
                agent_used = True

            return AgentDecision(
                txn_id=event.txn_id,
                chosen_action=raw_action,
                chosen_channel=CHANNEL_MAP.get(raw_action, "WHATSAPP"),
                reasoning=parsed.get("reasoning", f"Agent selected {raw_action} for Bucket {bucket_id}."),
                confidence=float(parsed.get("confidence", 0.85)),
                agent_model_used=model_name,
                agent_used=agent_used,
                alternatives_considered=[a for a in action_menu if a != raw_action],
                ev_justification=parsed.get("ev_justification"),
            )

        # LLM failed — deterministic fallback: pick highest-EV action
        FALLBACK_PRIORITY = [
            "WHATSAPP_UPI_INTENT",       # 74% p_recover
            "AUTO_DEBIT_RETRY",          # 68%
            "VOICE_RECOVERY_CALL",       # 65%
            "DYNAMIC_AFA_PAYMENT_LINK",  # 62%
            "DYNAMIC_INSTRUMENT_UPDATE_LINK",  # 52%
            "HUMAN_OPS_REVIEW",          # 25%
            "STOP_TERMINATION",          # 0%
        ]
        chosen = next((a for a in FALLBACK_PRIORITY if a in action_menu), action_menu[0])

        return AgentDecision(
            txn_id=event.txn_id,
            chosen_action=chosen,
            chosen_channel=CHANNEL_MAP.get(chosen, "WHATSAPP"),
            reasoning=f"LLM unavailable ({model_name}); deterministic EV-priority fallback selected {chosen} for Bucket {bucket_id}.",
            confidence=0.80,
            agent_model_used=f"deterministic-ev-fallback ({model_name})",
            agent_used=False,
            alternatives_considered=[a for a in action_menu if a != chosen],
        )
