"""
Centralized Regulatory Rules & Unit Economic Configuration.

Consolidates all statutory compliance thresholds, legal parameters (RBI, TRAI, CPA, MSMED, DPDP),
and financial unit economics (Expected Value modeling) for the AI Revenue Recovery Agent.
"""

from __future__ import annotations
from typing import Dict, Any
from pydantic import BaseModel, Field


class StatutoryThresholds(BaseModel):
    """Statutory thresholds mandated by Indian regulatory authorities."""
    
    # RBI 2026 E-Mandate Framework
    AFA_DEFAULT_THRESHOLD_INR: float = 15000.0          # General e-mandate limit without AFA (₹15,000)
    AFA_EXEMPT_CATEGORY_THRESHOLD_INR: float = 100000.0  # Exempt categories: Mutual Funds, Insurance, Credit Card Bill (₹1,00,000)
    PRE_DEBIT_NOTICE_MIN_HOURS: float = 24.0            # Mandatory advance notice window before recurring debit (24h)
    MAX_RETRY_ATTEMPTS_DUNNING: int = 3                 # Maximum automated dunning touches before permanent ceiling
    
    # TRAI UCC / DND Regulations
    TRAI_PERMITTED_START_HOUR_IST: int = 8              # 08:00 AM IST (Earliest outbound promotional/service touch)
    TRAI_PERMITTED_END_HOUR_IST: int = 20               # 08:00 PM IST (Latest outbound touch; quiet hours 20:00-08:00)
    
    # Consumer Protection Act (CPA 2019) / RBI Fair Practices
    PTP_GRACE_WINDOW_HOURS: float = 24.0                # Grace buffer post promised payment date before resuming dunning
    
    # MSMED Act 2006 (Section 15 & 16)
    MSMED_OVERDUE_STATUTORY_DAYS: int = 45              # Maximum agreed credit period for registered MSMEs
    RBI_REPO_RATE_PCT: float = 6.50                     # Baseline RBI Repo Rate (6.50%)
    MSMED_PENAL_RATE_MULTIPLIER: float = 3.0            # Mandated statutory compound interest (3x Repo Rate = 19.5% p.a.)
    
    # DPDP Act 2023 (Digital Personal Data Protection)
    MASK_PHONE_RETAIN_DIGITS: int = 4                   # Retain only last 4 digits (+91-XXXXXX1234)
    MASK_EMAIL_USER_CHARS: int = 2                      # Retain only first 2 chars of mailbox (jo****@domain.com)


class UnitEconomicsConfig(BaseModel):
    """Unit costs and annoyance penalties for Expected Value (EV) calculation."""
    
    # Communication Channel Unit Costs (INR)
    CHANNEL_COST_WHATSAPP_INR: float = 0.15             # Meta WhatsApp Business interactive message
    CHANNEL_COST_SMS_DLT_INR: float = 0.12              # Telecom DLT registered transactional SMS
    CHANNEL_COST_VOICE_AI_INR: float = 1.50             # Hinglish Voice AI Bot (per connected minute)
    CHANNEL_COST_AUTO_DEBIT_API_INR: float = 0.00       # Direct Payment Gateway API debit attempt
    CHANNEL_COST_HUMAN_OPS_TRIAGE_INR: float = 75.00    # Manual operator review cost per ticket
    
    # Customer Annoyance / Relationship Friction Penalties (INR equivalent)
    ANNOYANCE_PENALTY_QUIET_HOURS_INR: float = 50.00    # Severe brand penalty for reaching customer outside 8AM-8PM
    ANNOYANCE_PENALTY_VOICE_CALL_INR: float = 15.00     # Voice call friction penalty
    ANNOYANCE_PENALTY_WHATSAPP_LINK_INR: float = 5.00   # Interactive message friction
    ANNOYANCE_PENALTY_AUTO_DEBIT_INR: float = 0.00      # Zero customer intervention friction
    
    # Calibrated Recovery Probabilities (Empirical Indian Recurring Rails)
    PROBABILITY_AUTO_DEBIT_SALARY: float = 0.68         # Snapped to 1st-5th / 25th-30th + 24h notice
    PROBABILITY_WHATSAPP_UPI_INTENT: float = 0.74       # WhatsApp 1-click UPI intent app-switch
    PROBABILITY_DYNAMIC_AFA_LINK: float = 0.62          # OTP link for >₹15,000 ticket
    PROBABILITY_INSTRUMENT_UPDATE: float = 0.52         # Card expired update portal
    PROBABILITY_VOICE_AI_RECOVERY: float = 0.65         # Hinglish AI Voice Outreach
    PROBABILITY_PTP_FULFILLMENT: float = 0.85           # Promised-to-pay date customer fulfillment
    PROBABILITY_HUMAN_OPS_TRIAGE: float = 0.25          # Post-quarantine manual resolution


# Global singleton instances
REGULATORY_CONFIG = StatutoryThresholds()
UNIT_ECONOMICS = UnitEconomicsConfig()


def calculate_expected_value(
    action_type_str: str,
    amount: float,
    channel_str: str = "AUTO_DEBIT_API",
    is_quiet_hours: bool = False
) -> Dict[str, Any]:
    """
    Computes Expected Value:
      EV = (P_recover * Amount) - Channel_Cost - Annoyance_Penalty
    """
    # 1. Determine P(recover)
    prob_map = {
        "AUTO_DEBIT_RETRY": UNIT_ECONOMICS.PROBABILITY_AUTO_DEBIT_SALARY,
        "WHATSAPP_UPI_INTENT": UNIT_ECONOMICS.PROBABILITY_WHATSAPP_UPI_INTENT,
        "DYNAMIC_AFA_PAYMENT_LINK": UNIT_ECONOMICS.PROBABILITY_DYNAMIC_AFA_LINK,
        "DYNAMIC_INSTRUMENT_UPDATE_LINK": UNIT_ECONOMICS.PROBABILITY_INSTRUMENT_UPDATE,
        "VOICE_RECOVERY_CALL": UNIT_ECONOMICS.PROBABILITY_VOICE_AI_RECOVERY,
        "PTP_HOLD_FREEZE": UNIT_ECONOMICS.PROBABILITY_PTP_FULFILLMENT,
        "HUMAN_OPS_REVIEW": UNIT_ECONOMICS.PROBABILITY_HUMAN_OPS_TRIAGE,
        "STOP_TERMINATION": 0.0,
    }
    p_recover = prob_map.get(action_type_str, 0.50)

    # 2. Determine Channel Cost
    cost_map = {
        "WHATSAPP_SERVICE": UNIT_ECONOMICS.CHANNEL_COST_WHATSAPP_INR,
        "SMS_DLT_TRANSACTIONAL": UNIT_ECONOMICS.CHANNEL_COST_SMS_DLT_INR,
        "VOICE_BOT_OUTREACH": UNIT_ECONOMICS.CHANNEL_COST_VOICE_AI_INR,
        "AUTO_DEBIT_API": UNIT_ECONOMICS.CHANNEL_COST_AUTO_DEBIT_API_INR,
        "INTERNAL_PORTAL": UNIT_ECONOMICS.CHANNEL_COST_HUMAN_OPS_TRIAGE_INR,
    }
    channel_cost = cost_map.get(channel_str, 0.0)

    # 3. Determine Annoyance Penalty
    annoyance = 0.0
    if is_quiet_hours:
        annoyance += UNIT_ECONOMICS.ANNOYANCE_PENALTY_QUIET_HOURS_INR
    elif "VOICE" in channel_str:
        annoyance += UNIT_ECONOMICS.ANNOYANCE_PENALTY_VOICE_CALL_INR
    elif "WHATSAPP" in channel_str or "SMS" in channel_str:
        annoyance += UNIT_ECONOMICS.ANNOYANCE_PENALTY_WHATSAPP_LINK_INR

    gross_expected_revenue = p_recover * amount
    net_expected_value = gross_expected_revenue - channel_cost - annoyance

    return {
        "amount_inr": amount,
        "p_recovery": round(p_recover, 3),
        "gross_expected_revenue_inr": round(gross_expected_revenue, 2),
        "channel_cost_inr": round(channel_cost, 2),
        "annoyance_penalty_inr": round(annoyance, 2),
        "net_expected_value_inr": round(net_expected_value, 2),
        "is_positive_ev": net_expected_value > 0.0,
        "formula": f"({p_recover:.2f} × ₹{amount:,.2f}) - ₹{channel_cost:.2f} - ₹{annoyance:.2f} = ₹{net_expected_value:,.2f}",
    }
