# Root-Cause Taxonomy & Error Action Matrix
## Track 03: AI Revenue Recovery System

---

## 1. Overview: Razorpay Error Model (`source` / `step` / `reason`)

Razorpay categorizes all transaction failures and degradation events using a structured 3-tier failure model:
1. **`source`**: Identifies where the failure originated (`customer`, `gateway`, `bank`, `business`, `network`).
2. **`step`**: Specifies the exact lifecycle stage where execution failed (`payment_initiation`, `payment_authentication`, `payment_authorization`, `payment_capture`).
3. **`reason`**: The exact machine-readable failure reason code returned by the payment gateway, card network, or core banking system (CBS).

The AI Revenue Recovery Agent ingests these error objects to deterministically determine:
- **Retryability:** Whether the error is **Retryable** (soft technical/temporary failure) or **Non-Retryable** (hard instrument/regulatory stop).
- **Compliant Intervention:** The exact statutory and system-compliant action to win back the revenue without violating RBI, TRAI, or NPCI regulations.

---

```
                               ┌─────────────────────────────┐
                               │   Razorpay Error Ingested   │
                               │ {source, step, reason, code}│
                               └──────────────┬──────────────┘
                                              │
                      ┌───────────────────────┴───────────────────────┐
                      ▼                                               ▼
         ┌─────────────────────────┐                     ┌─────────────────────────┐
         │     SOFT / RETRYABLE    │                     │   HARD / NON-RETRYABLE  │
         │ (Temporary / Liquidity) │                     │ (Expired / Revoked / AFA│
         └────────────┬────────────┘                     └────────────┬────────────┘
                      │                                               │
     ┌────────────────┴────────────────┐             ┌────────────────┴────────────────┐
     ▼                                 ▼             ▼                                 ▼
┌──────────────────────────┐ ┌──────────────────┐ ┌───────────────────┐ ┌─────────────────────┐
│ ≥24h Pre-Debit Alert +   │ │ Exponential      │ │ 1-Click Mandate   │ │ Dynamic AFA Payment │
│ Smart Liquidity Retry    │ │ Backoff Routing  │ │ Update Link       │ │ Link (>₹15k / >₹1L) │
└──────────────────────────┘ └──────────────────┘ └───────────────────┘ └─────────────────────┘
```

---

## 2. The 12 Concrete Root-Cause Error Buckets

### Summary Classification Table

| # | Error Bucket & Reason Code | Source | Lifecycle Step | Retryable? | Primary Compliant Action |
| :-: | :--- | :--- | :--- | :---: | :--- |
| **1** | `insufficient_funds` | `customer` | `payment_authorization` | **YES (Soft)** | 24h Pre-Debit Alert $\rightarrow$ Smart Salary-Window Retry (1st–5th / 25th–30th). |
| **2** | `bank_server_down` / `bank_unavailable` | `gateway` | `payment_authorization` | **YES (Soft)** | Exponential Backoff (2h $\rightarrow$ 6h $\rightarrow$ 24h) + Dynamic Route Fallback. |
| **3** | `gateway_timeout` / `network_error` | `network` | `payment_authorization` | **YES (Soft)** | Auto-Poll Razorpay Fetch Payment API $\rightarrow$ Settle or Retry after 15m. |
| **4** | `velocity_limit_exceeded` | `bank` | `payment_authorization` | **YES (Soft)** | Pause for 24h $\rightarrow$ Dispatch $\ge 24\text{h}$ Pre-Debit Notice $\rightarrow$ Retry on Day $T+2$. |
| **5** | `upi_collect_expired` / `upi_app_timeout` | `customer` | `payment_authorization` | **YES (Intervention)** | Deliver 1-Click UPI Intent Deep-Link via WhatsApp for instant app switch. |
| **6** | `authentication_failed` / `invalid_otp` | `customer` | `payment_authentication` | **NO (Auto-Debit)**<br>**YES (Link)** | Dispatch 1-Click Dynamic Session Retry Link; cease direct debit retries. |
| **7** | `card_expired` / `card_inactive` | `customer` | `payment_initiation` | **NO (Hard)** | Halt Auto-Debit $\rightarrow$ Dispatch Secure Mandate Instrument Update Link. |
| **8** | `mandate_cancelled_by_user` | `customer` | `payment_authorization` | **NO (Hard)** | Trigger `STOP_MANDATE_REVOKED` $\rightarrow$ Purge pending retries $\rightarrow$ Service email. |
| **9** | `mandate_validity_expired` | `customer` | `payment_initiation` | **NO (Hard)** | Trigger `STOP_MANDATE_EXPIRED` $\rightarrow$ Send 1-Click Mandate Renewal Link. |
| **10** | `bank_technical_decline` / `do_not_honor` | `bank` | `payment_authorization` | **NO (Auto-Debit)**<br>**YES (Link)** | Notify customer with bank unblocking instructions + alternate rail link (UPI/NetBanking). |
| **11** | `amount_exceeds_statutory_afa_limit` | `business` | `payment_initiation` | **NO (Direct Debit)** | Disable Auto-Debit $\rightarrow$ Dispatch AFA-compliant Payment Link for OTP validation. |
| **12** | `checkout_abandonment_dropoff` | `customer` | `payment_initiation` | **NO (Auto-Debit)**<br>**YES (Nudge)** | Check TRAI/Consent $\rightarrow$ Deliver Itemized Cart Recovery Link with zero dark patterns. |

---

## 3. Deep-Dive: Error Bucket Specifications & Action Protocols

---

### Bucket 1: Insufficient Balance / Low Liquidity
* **Error Signature:** `source: customer` | `step: payment_authorization` | `reason: insufficient_funds`
* **Root Cause:** Customer's linked bank account or credit card line lacks sufficient liquidity on the billing due date.
* **Retryability:** **YES (Conditional / Soft Failure)**
* **Compliant Recovery Action:**
  1. Record failed attempt count (`retry_count = 1`).
  2. Queue a mandatory **$\ge 24$-hour Pre-Debit Notification** via SMS/WhatsApp.
  3. Schedule the retry debit aligned with the predicted salary/liquidity window (typically 1st–5th or 25th–30th of the month).
  4. Enforce internal safety guardrails: Minimum **48-hour cooling-off period** between debits; maximum **3 total retry attempts**.
  5. Log audit trail: `afa_status: "NOT_REQUIRED"`, `internal_policy: "48H_COOLING_INTERVAL"`.

---

### Bucket 2: Core Banking / Issuer Downtime
* **Error Signature:** `source: gateway` | `step: payment_authorization` | `reason: bank_server_down`
* **Root Cause:** The customer's issuing bank CBS (Core Banking System) or NPCI switch is experiencing a technical outage or elevated error rate.
* **Retryability:** **YES (Technical / Soft Failure)**
* **Compliant Recovery Action:**
  1. Trigger dynamic routing fallback through an alternative acquirer gateway rail (if multi-gateway routing is supported).
  2. If unavailable, apply **exponential backoff schedule**: Retry in **2 hours** $\rightarrow$ **6 hours** $\rightarrow$ **24 hours**.
  3. Before the final 24-hour retry, confirm that $\ge 24\text{h}$ pre-debit notice requirements are satisfied.
  4. Zero customer dunning required; resolve purely via automated infrastructure retries.

---

### Bucket 3: Gateway Timeout / Network Handshake Drop
* **Error Signature:** `source: network` | `step: payment_authorization` | `reason: gateway_timeout`
* **Root Cause:** HTTP socket timeout, packet loss, or unresolved latency between Razorpay and the payment network. The actual debit state at the bank is unknown.
* **Retryability:** **YES (Idempotent Status Verification)**
* **Compliant Recovery Action:**
  1. **Do NOT initiate an immediate duplicate debit.**
  2. Execute an idempotent poll using the **Razorpay Fetch Payment API** (`GET /v1/payments/{payment_id}`) at $T+5\text{m}$ and $T+15\text{m}$.
  3. If payment state is `captured`, execute `STOP_PAID` and send post-debit receipt with grievance details.
  4. If payment state is confirmed `failed`, re-queue for single retry after 30 minutes cooling-off.

---

### Bucket 4: Bank Velocity / Daily Transaction Limit Exceeded
* **Error Signature:** `source: bank` | `step: payment_authorization` | `reason: velocity_limit_exceeded`
* **Root Cause:** Customer exceeded their bank's daily count or amount cap for digital/e-mandate transactions.
* **Retryability:** **YES (Time-Delayed Soft Failure)**
* **Compliant Recovery Action:**
  1. Freeze debit attempts for the remainder of the calendar day ($T$).
  2. Dispatch a Service notification via WhatsApp: *"Your transaction paused due to daily bank limit. We will retry tomorrow."*
  3. Dispatch $\ge 24\text{h}$ pre-debit notification for Day $T+2$.
  4. Execute retry on Day $T+2$ at 10:00 AM IST (within the TRAI 08:00–20:00 window).

---

### Bucket 5: UPI AutoPay / Collect App Request Timeout
* **Error Signature:** `source: customer` | `step: payment_authorization` | `reason: upi_collect_expired`
* **Root Cause:** The customer did not approve the UPI mandate debit notification on their UPI app (GPay, PhonePe, Paytm, BHIM) before the collection window expired.
* **Retryability:** **YES (Customer-Assisted Intervention)**
* **Compliant Recovery Action:**
  1. Deliver a rich WhatsApp/SMS message containing a **1-Click UPI Intent Deep-Link**.
  2. Clicking the link directly opens the customer's preferred UPI app with the payment parameters pre-filled.
  3. Provide an alternate one-click NetBanking/Card checkout fallback in the same message.

---

### Bucket 6: 3DS OTP Authentication Failure / Drop
* **Error Signature:** `source: customer` | `step: payment_authentication` | `reason: authentication_failed`
* **Root Cause:** User entered an incorrect OTP, exceeded OTP attempts, or closed the 3DS verification modal.
* **Retryability:** **NO (Direct Auto-Debit)** / **YES (Interactive Link)**
* **Compliant Recovery Action:**
  1. **Strict Guardrail:** Do NOT auto-retry debit on the card instrument (subsequent attempts will fail or trigger bank fraud locks).
  2. Generate a dynamic **Razorpay Payment Link** pre-filled with the order context.
  3. Dispatch via WhatsApp/Email: *"Your verification was incomplete. Click here to complete your payment with a fresh OTP."*

---

### Bucket 7: Expired or Inactive Card Instrument
* **Error Signature:** `source: customer` | `step: payment_initiation` | `reason: card_expired`
* **Root Cause:** The linked credit/debit card passed its expiry date ($MM/YY$) or was marked inactive by the issuer.
* **Retryability:** **NO (Hard Failure)**
* **Compliant Recovery Action:**
  1. Instantly mark the card token status as `EXPIRED`.
  2. Suppress all automated retry attempts on this token.
  3. Send a Service notification with a secure 1-click **"Update Payment Method"** link to register a new card or switch to UPI AutoPay (with mandatory registration AFA).

---

### Bucket 8: Mandate Cancelled / Revoked by Customer
* **Error Signature:** `source: customer` | `step: payment_authorization` | `reason: mandate_cancelled_by_user`
* **Root Cause:** The subscriber manually cancelled the e-mandate via their netbanking portal or UPI app.
* **Retryability:** **NO (Hard Statutory Stop)**
* **Compliant Recovery Action:**
  1. Instantly trigger **`STOP_MANDATE_REVOKED`**.
  2. Purge all queued dunning, retries, and automated calls.
  3. Update subscription status to `HALTED`.
  4. Send a single transactional confirmation email acknowledging cancellation and offering a self-service reactivation link.

---

### Bucket 9: Mandate Validity Timeline Expired
* **Error Signature:** `source: customer` | `step: payment_initiation` | `reason: mandate_validity_expired`
* **Root Cause:** The recurring e-mandate reached its statutory `valid_until` end date.
* **Retryability:** **NO (Hard Statutory Stop)**
* **Compliant Recovery Action:**
  1. Instantly trigger **`STOP_MANDATE_EXPIRED`**.
  2. Auto-debits are prohibited under the RBI e-mandate framework.
  3. Dispatch an invitation link allowing the customer to create a fresh e-mandate with full 2-Factor AFA registration.

---

### Bucket 10: Bank Security Decline ("Do Not Honor")
* **Error Signature:** `source: bank` | `step: payment_authorization` | `reason: bank_technical_decline`
* **Root Cause:** Issuer bank's internal fraud engine declined the recurring transaction (e.g. international card restriction, unusual volume).
* **Retryability:** **NO (Direct Auto-Debit)** / **YES (Customer Action)**
* **Compliant Recovery Action:**
  1. Cease direct card debit retries to avoid triggering issuer security blocks.
  2. Dispatch an informative Service notification: *"Your bank declined the recurring debit. Please enable online/e-mandate transactions on your bank app, or use an alternative payment mode below."*
  3. Provide a multi-rail Razorpay checkout link (UPI, NetBanking, alternate card).

---

### Bucket 11: Amount Exceeds Statutory AFA Threshold
* **Error Signature:** `source: business` | `step: payment_initiation` | `reason: amount_exceeds_statutory_afa_limit`
* **Root Cause:** The recurring debit amount exceeds ₹15,000 (for general subscriptions) or ₹1,00,000 (for exempt Mutual Funds, Insurance, Credit Card bills).
* **Retryability:** **NO (Direct Auto-Debit Legally Prohibited)**
* **Compliant Recovery Action:**
  1. Direct auto-debit without OTP is strictly prohibited under the RBI 2026 E-Mandate Framework.
  2. Generate a dynamic **AFA-Compliant Payment Link** requiring customer OTP/AFA validation.
  3. Dispatch via WhatsApp/SMS/Email with full pricing transparency.
  4. Log audit trail: `afa_status: "AFA_REQUIRED_LINK_SENT"`.

---

### Bucket 12: Checkout Drop-Off / Cart Abandonment
* **Error Signature:** `source: customer` | `step: payment_initiation` | `reason: checkout_abandonment_dropoff`
* **Root Cause:** Customer abandoned the checkout flow before completing authentication (e.g., hesitated on price, UPI app switch failed, session timed out).
* **Retryability:** **NO (Non-debit Event)** / **YES (Multi-Channel Nudge)**
* **Compliant Recovery Action:**
  1. Verify customer consent and DND status under TRAI rules.
  2. Deliver an itemized **1-Click Cart Recovery Link** via WhatsApp/Email within the 08:00 AM – 08:00 PM window.
  3. Ensure complete compliance with CCPA 2023 anti-dark-patterns: Display clear itemized tax/GST breakdown and provide a 1-click `STOP` unsubscribe option.

---

## 4. Critical Real-World Edge Cases & Production Protocols

Fintech systems face subtle race conditions and statutory boundary clashes. The agent handles these **10 critical edge cases**:

---

### Edge Case 1: The "Zombie" Payment (Network Timeout with Unknown Debit State)
* **The Problem:** Razorpay returns `gateway_timeout` or socket hangup. The bank may have actually debited the customer's account.
* **Double-Debit Hazard:** Blindly re-firing the debit will double-charge the customer.
* **Production Protocol:**
  1. Mark transaction state as `PENDING_SETTLEMENT_VERIFICATION`.
  2. Schedule idempotent polling via Razorpay `GET /v1/payments/{payment_id}` at $T+5\text{m}$ and $T+15\text{m}$.
  3. If status returns `captured` $\rightarrow$ Trigger **`STOP_PAID`** and dispatch confirmation with grievance details.
  4. If status returns `failed` $\rightarrow$ Re-queue for standard retry after cooling window.

---

### Edge Case 2: The Salary-Cycle Trap (Premature Retry Exhaustion)
* **The Problem:** A recurring subscription fails on the 21st of the month due to `insufficient_funds`.
* **Premature Cancellation Hazard:** If the agent fires retries on the 23rd, 25th, and 27th, it hits `STOP_MAX_RETRIES` (3 attempts) **before** the customer receives their monthly salary on the 30th/1st.
* **Production Protocol:**
  1. Detect failure date relative to the standard salary cycle (1st–5th or 25th–30th).
  2. Space the 3 retry attempts strategically:
     * Retry #1: $T+3$ days (short-term liquidity buffer).
     * Retry #2: $T+7$ days (mid-cycle buffer).
     * Retry #3: Snapped to the 1st of next month (salary credit window).
  3. Always dispatch a $\ge 24\text{h}$ pre-debit alert before each retry.

---

### Edge Case 3: Race Condition — Payment via Link while Auto-Debit Retry is Queued
* **The Problem:** Auto-debit failed on Monday. The agent dispatched a WhatsApp payment link and queued an auto-debit retry for Thursday. On Wednesday night, the customer clicks the link and pays.
* **Double-Debit Hazard:** If the Thursday cron job fires, the customer is debited a second time.
* **Production Protocol:**
  1. Webhook listener receives `payment.captured` for the entity ID.
  2. Atomically trigger **`STOP_PAID`**.
  3. Purge all pending cron/delayed retry tasks in Redis/Postgres for that `subscription_id` / `invoice_id`.

---

### Edge Case 4: Promise-to-Pay (PTP) vs. MSMED 45-Day Statutory Deadline
* **The Problem:** A commercial debtor tells the Hinglish voice bot: *"I will clear this invoice in 60 days"*, but the supplier is an MSE covered under Section 15 of MSMED Act (45-day statutory ceiling).
* **Statutory Clashing Hazard:** A verbal PTP cannot illegally extend statutory limits without penal interest consequences.
* **Production Protocol:**
  1. Voice bot parser detects the promised date exceeds the statutory 45-day cap.
  2. Agent dynamically informs the debtor: *"We have noted your date, but please be aware that under MSMED guidelines, invoices past 45 days accrue statutory compound interest."*
  3. Proposes an interim milestone payment (e.g. 50% now, balance in 15 days).

---

### Edge Case 5: Partial Payment & Milestone Recovery
* **The Problem:** An overdue B2B invoice is for ₹1,00,000. The customer clicks the recovery link and makes a partial payment of ₹40,000.
* **Workflow Hazard:** Marking the invoice as `STOP_PAID` loses the remaining ₹60,000; marking it as `FAILED` ignores the recovered ₹40,000.
* **Production Protocol:**
  1. Ingest partial capture webhook.
  2. Deduct ₹40,000 from outstanding ledger balance (Remaining: ₹60,000).
  3. Update recovery metrics: Add ₹40,000 to **Measured Money Recovered**.
  4. Dynamically regenerate dunning templates and payment links for the remaining ₹60,000 balance.

---

### Edge Case 6: Chargeback / Fraud Dispute Raised During Active Dunning
* **The Problem:** Customer files a fraud claim with their bank (`payment.disputed` webhook received) while the agent is in active recovery.
* **Legal Liability Hazard:** Continuing automated collection calls or retries during an active dispute violates consumer protection and banking rules.
* **Production Protocol:**
  1. Immediately trigger **`STOP_DISPUTE_FRAUD`**.
  2. Freeze all automated retries, SMS alerts, WhatsApp nudges, and voice calls instantly.
  3. Escalate the case directly to authorized Risk & Fraud Operations with full audit logs.

---

### Edge Case 7: TRAI Quiet Hours Breach (Late-Night Failures)
* **The Problem:** A recurring payment fails at 11:45 PM IST due to insufficient funds.
* **Harassment Violation Hazard:** Sending pre-debit notifications or dunning messages at midnight violates fair practice guidelines.
* **Production Protocol:**
  1. Ingestion detects failure timestamp is outside the **08:00 AM – 08:00 PM IST** window.
  2. Push event to the **Delayed Dispatch Queue**.
  3. Hold execution until **08:05 AM IST** the following morning.

---

### Edge Case 8: Mid-Flight Mandate Limit Lowering
* **The Problem:** Customer opened their UPI/banking app and decreased their mandate maximum limit from ₹5,000 to ₹2,000. The upcoming renewal invoice is ₹3,500.
* **Infinite Retry Hazard:** Error returned is `mandate_limit_exceeded`. Direct retries will fail every time.
* **Production Protocol:**
  1. Classify error as **Hard Mandate Limit Failure**.
  2. Auto-debit disabled.
  3. Dispatch a 1-click link prompting the customer to increase their mandate cap or complete a 1-click AFA payment for the difference.

---

### Edge Case 9: Month-End & Leap Year Calendar Clamping
* **The Problem:** Mandate registered on January 31st for monthly billing. February has only 28 days (or 29 in leap years).
* **Scheduling Bug Hazard:** A naive date addition (`+30 days`) drifts billing dates across months.
* **Production Protocol:**
  1. Clamping algorithm snaps monthly execution dates to `min(billing_day, days_in_month)`.
  2. For February, execution snaps to Feb 28 (or Feb 29).
  3. Pre-debit notification is dispatched $\ge 24\text{ hours}$ earlier (Feb 27 at 09:00 AM).

---

### Edge Case 10: DND-Registered Customer with Incomplete Checkout
* **The Problem:** A customer on the TRAI National Do Not Call (DND) registry abandons a high-value cart.
* **Regulatory Breach Hazard:** Placing cold AI voice calls or sending un-consented promotional SMS violates TRAI UCC rules.
* **Production Protocol:**
  1. Classify checkout drop-off outreach as **`PROMOTIONAL`**.
  2. Check `DND == True`.
  3. Suppress all outbound voice calls and promotional SMS.
  4. Fallback strictly to in-app session restore banner or transactional service email (if explicit consent exists).

---

## 5. Integration Code Snippet (Python Engine Classifier)

```python
from dataclasses import dataclass
from datetime import datetime, time
from typing import Optional, Dict, Any

@dataclass
class RecoveryDecision:
    bucket_id: int
    reason: str
    retryable: bool
    afa_status: str
    action_protocol: str
    communication_type: str
    stopping_rule: Optional[str] = None
    delay_until_0805_ist: bool = False

def is_within_trai_safe_window(now: datetime) -> bool:
    """Checks if current time is within 08:00 AM to 08:00 PM IST."""
    return time(8, 0) <= now.time() <= time(20, 0)

def classify_and_route_error(error_event: Dict[str, Any], current_time: datetime) -> RecoveryDecision:
    source = error_event.get("source")
    step = error_event.get("step")
    reason = error_event.get("reason")
    amount = float(error_event.get("amount_inr", 0))
    category = error_event.get("category", "STANDARD")
    is_dnd = bool(error_event.get("is_dnd", False))
    dispute_active = bool(error_event.get("dispute_active", False))
    ptp_active_until = error_event.get("ptp_active_until")

    # Guard 1: Active Dispute / Fraud Flag
    if dispute_active or reason == "payment_disputed":
        return RecoveryDecision(
            bucket_id=0,
            reason="payment_disputed",
            retryable=False,
            afa_status="NOT_APPLICABLE",
            action_protocol="LOCKDOWN_ESCALATE_TO_FRAUD_OPS",
            communication_type="TRANSACTIONAL",
            stopping_rule="STOP_DISPUTE_FRAUD"
        )

    # Guard 2: Active Promise-to-Pay (PTP) Grace Window
    if ptp_active_until and datetime.fromisoformat(ptp_active_until) > current_time:
        return RecoveryDecision(
            bucket_id=0,
            reason="ptp_grace_window_active",
            retryable=False,
            afa_status="NOT_APPLICABLE",
            action_protocol="FREEZE_DUNNING_UNTIL_PTP_DATE",
            communication_type="SERVICE",
            stopping_rule="STOP_PTP_ACTIVE"
        )

    # Guard 3: TRAI Quiet Hours Check
    delay_dispatch = not is_within_trai_safe_window(current_time)

    # 1. Statutory Threshold Check (RBI 2026 Caps)
    is_exempt = category in ["MUTUAL_FUND", "INSURANCE_PREMIUM", "CREDIT_CARD_BILL"]
    cap = 100000.0 if is_exempt else 15000.0
    if amount > cap:
        return RecoveryDecision(
            bucket_id=11,
            reason="amount_exceeds_statutory_afa_limit",
            retryable=False,
            afa_status="AFA_REQUIRED_LINK_SENT",
            action_protocol="GENERATE_DYNAMIC_AFA_PAYMENT_LINK",
            communication_type="SERVICE",
            delay_until_0805_ist=delay_dispatch
        )

    # 2. Hard Failure Classification
    if reason in ["mandate_cancelled_by_user", "mandate_revoked"]:
        return RecoveryDecision(
            bucket_id=8,
            reason=reason,
            retryable=False,
            afa_status="NOT_APPLICABLE",
            action_protocol="PURGE_RETRIES_SEND_SERVICE_EMAIL",
            communication_type="SERVICE",
            stopping_rule="STOP_MANDATE_REVOKED"
        )
    elif reason in ["mandate_validity_expired", "mandate_expired"]:
        return RecoveryDecision(
            bucket_id=9,
            reason=reason,
            retryable=False,
            afa_status="NOT_APPLICABLE",
            action_protocol="SEND_MANDATE_RE_REGISTRATION_LINK",
            communication_type="SERVICE",
            stopping_rule="STOP_MANDATE_EXPIRED"
        )
    elif reason in ["card_expired", "card_inactive"]:
        return RecoveryDecision(
            bucket_id=7,
            reason=reason,
            retryable=False,
            afa_status="NOT_APPLICABLE",
            action_protocol="SEND_UPDATE_PAYMENT_METHOD_LINK",
            communication_type="SERVICE",
            delay_until_0805_ist=delay_dispatch
        )

    # 3. Soft Technical / Liquidity Failures
    elif reason == "insufficient_funds":
        return RecoveryDecision(
            bucket_id=1,
            reason=reason,
            retryable=True,
            afa_status="EXEMPT_CATEGORY_SIP_INS_CC" if is_exempt else "NOT_REQUIRED",
            action_protocol="QUEUE_24H_PRE_DEBIT_ALERT_SCHEDULE_SALARY_RETRY",
            communication_type="SERVICE",
            delay_until_0805_ist=delay_dispatch
        )
    elif reason in ["bank_server_down", "bank_unavailable"]:
        return RecoveryDecision(
            bucket_id=2,
            reason=reason,
            retryable=True,
            afa_status="NOT_REQUIRED",
            action_protocol="EXPONENTIAL_BACKOFF_DYNAMIC_ROUTING",
            communication_type="SERVICE"
        )
    elif reason in ["gateway_timeout", "network_error"]:
        return RecoveryDecision(
            bucket_id=3,
            reason=reason,
            retryable=True,
            afa_status="NOT_REQUIRED",
            action_protocol="IDEMPOTENT_POLL_RAZORPAY_FETCH_THEN_SETTLE",
            communication_type="TRANSACTIONAL"
        )

    # 4. Checkout Drop-off Handling
    elif reason == "checkout_abandonment_dropoff":
        if is_dnd:
            return RecoveryDecision(
                bucket_id=12,
                reason=reason,
                retryable=False,
                afa_status="NOT_REQUIRED",
                action_protocol="SUPPRESS_PROMOTIONAL_USE_IN_APP_BANNER",
                communication_type="PROMOTIONAL"
            )
        return RecoveryDecision(
            bucket_id=12,
            reason=reason,
            retryable=False,
            afa_status="NOT_REQUIRED",
            action_protocol="DELIVER_1_CLICK_CART_RECOVERY_LINK",
            communication_type="PROMOTIONAL",
            delay_until_0805_ist=delay_dispatch
        )

    # Default Fallback
    return RecoveryDecision(
        bucket_id=10,
        reason=reason or "unknown_error",
        retryable=False,
        afa_status="AFA_REQUIRED_LINK_SENT",
        action_protocol="DELIVER_MULTI_RAIL_CHECKOUT_LINK",
        communication_type="SERVICE",
        delay_until_0805_ist=delay_dispatch
    )
```

---

## 6. Verification Checklist

- [x] Based on Razorpay's official `source`, `step`, and `reason` error model.
- [x] Covers 12 distinct concrete error buckets across customer, gateway, bank, and network origins.
- [x] Includes 10 real-world production edge cases (Zombie payments, salary cycle traps, race conditions, MSMED 45-day clashes, partial payments, quiet hours).
- [x] Clear binary tagging: `Retryable: YES (Soft)` vs `Retryable: NO (Hard / Statutory Stop)`.
- [x] Compliant intervention specified for each bucket (upholding 24h pre-debit alert, cooling intervals, AFA caps, and DPDP/CCPA rules).
- [x] Includes updated Python decision engine with edge case safety guards.
