# Razorpay AI Challenge: Track 03 — AI Revenue Recovery
> **"Find revenue that’s slipping away and win it back"**

An autonomous, audit-grade AI Revenue Recovery Agent that detects revenue at risk across recurring payment failures, checkout abandonments, and overdue B2B receivables, diagnoses root causes using Razorpay's 3-tier error model, routes actions through statutory RBI/TRAI compliance policies, executes bounded interventions, and proves measured money recovered with an immutable audit trail.

---

## 🏛️ End-to-End System Architecture

```mermaid
flowchart TD
    %% STAGE 1: INGESTION
    subgraph S1 ["1. Ingestion Layer (Revenue at Risk)"]
        W1["Razorpay Webhook Stream<br/>(payment.failed, subscription.halted)"]
        W2["Checkout Drop-Off Telemetry<br/>(Cart abandonment, UPI intent timeout)"]
        W3["B2B Receivables Ledger Feed<br/>(Overdue commercial invoices)"]
    end

    %% STAGE 2: CLASSIFIER
    subgraph S2 ["2. Diagnosis & Root-Cause Classifier"]
        PARSE["Razorpay Error Parser<br/>(source / step / reason)"]
        TRIAGE{"Failure Triage<br/>(12 Error Buckets)"}
        SOFT["Soft / Retryable Failure<br/>(insufficient_funds, bank_server_down, timeout)"]
        HARD["Hard / Non-Retryable Failure<br/>(card_expired, mandate_revoked, mandate_expired)"]
        DROP["Drop-Off / Commercial Overdue<br/>(cart_abandoned, overdue_b2b_invoice)"]
    end

    %% STAGE 3: COMPLIANCE ROUTER
    subgraph S3 ["3. Compliance & Policy Router (Dual-Layer)"]
        STOP{"Deterministic<br/>Stopping Engine"}
        STOPS_TRIGGERED["HALT WORKFLOW<br/>(STOP_PAID, STOP_REVOKED, STOP_EXPIRED,<br/>STOP_OPT_OUT, STOP_DISPUTE, STOP_PTP)"]
        
        STAT_CHECK{"Statutory Checks (RBI / MSMED)"}
        AFA_CAP{"Amount <= RBI AFA Cap?<br/>(Standard: <= ₹15k | SIP/Ins/CC: <= ₹1L)"}
        
        TRAI_CHECK{"TRAI / Communication Router"}
        COMM_CLASS["Classify Stream:<br/>TRANSACTIONAL / SERVICE / RECOVERY / PROMOTIONAL"]
    end

    %% STAGE 4: SCHEDULER & INTERVENTIONS
    subgraph S4 ["4. Intelligent Scheduler & Execution Engine"]
        TIME_FILTER{"TRAI Quiet Hours?<br/>(08:00 AM - 08:00 PM IST)"}
        QUIET_QUEUE["Delayed Dispatch Queue<br/>(Hold until 08:05 AM IST)"]
        
        EXEC_RETRY["Smart Mandate Retry Sequencer<br/>• Queue >= 24h Pre-Debit Alert<br/>• Snap to Salary Window (1st-5th / 25th-30th)<br/>• Min 48h Cooling Interval (Max 3 Retries)"]
        
        EXEC_AFA_LINK["Dynamic AFA Payment Link<br/>• 1-Click OTP Checkout (> ₹15k / > ₹1L)<br/>• Expired Card / Mandate Update Link"]
        
        EXEC_CHANNELS["Multi-Channel Conversational Engine<br/>• WhatsApp 1-Click UPI Deep-Links<br/>• Interactive Hinglish Voice Recovery Bot<br/>• Promise-to-Pay (PTP) State Tracker"]
    end

    %% STAGE 5: AUDIT LOG
    subgraph S5 ["5. Immutable Compliance Audit Trail"]
        AUDIT_ENGINE["Cryptographic Audit Logger"]
        AUDIT_REC["JSON Audit Record<br/>• audit_id & ISO timestamp<br/>• Masked PII (PCI-DSS / DPDP 2023)<br/>• afa_status (NOT_REQUIRED / VALIDATED)<br/>• statutory_rule & internal_policy applied<br/>• grievance_details_included: true"]
    end

    %% STAGE 6: MEASUREMENT & ANALYTICS
    subgraph S6 ["6. Measurement & Recovery Analytics Engine"]
        KPI_METRICS["Live Recovery Metrics Dashboard<br/>• Total Revenue at Risk (₹)<br/>• Measured Money Recovered (₹)<br/>• Recovery Rate (%)<br/>• Channel & Rail Attribution<br/>• 100% Compliance Pass Rate"]
        SETTLE_EVENT["Outcome Ingestion<br/>(payment.captured / invoice.paid)"]
    end

    %% DATA FLOW CONNECTIONS
    W1 --> PARSE
    W2 --> PARSE
    W3 --> PARSE

    PARSE --> TRIAGE
    TRIAGE -->|Soft / Liquidity| SOFT
    TRIAGE -->|Hard / Revoked| HARD
    TRIAGE -->|Drop-off / Invoice| DROP

    SOFT --> STOP
    HARD --> STOP
    DROP --> STOP

    STOP -->|Boundary Hit| STOPS_TRIGGERED
    STOP -->|Active Case| STAT_CHECK

    STAT_CHECK --> AFA_CAP
    STAT_CHECK --> COMM_CLASS

    AFA_CAP -->|Amount <= Cap: afa_status = NOT_REQUIRED| TIME_FILTER
    AFA_CAP -->|Amount > Cap: afa_status = AFA_REQUIRED| EXEC_AFA_LINK
    HARD -->|Instrument Update / Re-auth| EXEC_AFA_LINK

    COMM_CLASS --> TIME_FILTER
    TIME_FILTER -->|Outside 08:00-20:00| QUIET_QUEUE
    TIME_FILTER -->|Inside 08:00-20:00| EXEC_RETRY
    TIME_FILTER -->|Inside 08:00-20:00| EXEC_CHANNELS
    QUIET_QUEUE -->|At 08:05 AM| EXEC_CHANNELS

    EXEC_RETRY --> AUDIT_ENGINE
    EXEC_AFA_LINK --> AUDIT_ENGINE
    EXEC_CHANNELS --> AUDIT_ENGINE
    STOPS_TRIGGERED --> AUDIT_ENGINE

    AUDIT_ENGINE --> AUDIT_REC
    AUDIT_REC --> KPI_METRICS
    SETTLE_EVENT --> STOP
    EXEC_CHANNELS -.->|Payment Completed| SETTLE_EVENT
    EXEC_RETRY -.->|Debit Succeeded| SETTLE_EVENT
    EXEC_AFA_LINK -.->|OTP Verified| SETTLE_EVENT
    SETTLE_EVENT --> KPI_METRICS
```

---

## 🔄 Architectural Stage Breakdown

### 1. Ingestion Layer (`Revenue at Risk`)
* Ingests real-time payment degradation, webhook failures, and telemetry across 4 core streams:
  * **Failed Subscriptions:** `payment.failed`, `subscription.halted` on cards and UPI AutoPay.
  * **Network & Gateway Degrades:** Timeout webhooks, CBS banking 503 outages.
  * **Checkout Abandonments:** Cart drop-off telemetry and UPI intent session expirations.
  * **B2B Receivables Ledger:** Overdue commercial tax invoices.

### 2. Diagnosis & Root-Cause Classifier
* Analyzes Razorpay's native 3-tier error hierarchy: **`source`** (`customer`, `gateway`, `bank`, `business`, `network`), **`step`**, and **`reason`**.
* Deterministically maps events into **12 concrete error buckets** documented in [root-cause-taxonomy.md](file:///Users/harmitjetani/Documents/GitHub/razorpay-ai-challenge/root-cause-taxonomy.md).
* Classifies failures into:
  * **Soft / Retryable:** Temporary liquidity shortfalls (`insufficient_funds`), bank server outages (`bank_server_down`), network timeouts.
  * **Hard / Non-Retryable:** Expired instruments (`card_expired`), revoked mandates (`mandate_cancelled_by_user`), expired validity (`mandate_validity_expired`).
  * **Drop-offs & Receivables:** Abandoned checkouts and overdue B2B invoices.

### 3. Compliance & Policy Router (Dual-Layer Governance)
* Enforces strict regulatory boundaries documented in [compliance-rules.md](file:///Users/harmitjetani/Documents/GitHub/razorpay-ai-challenge/compliance-rules.md):
  * **Deterministic Stopping Rules:** Instantly halts workflows on `STOP_PAID`, `STOP_MANDATE_REVOKED`, `STOP_MANDATE_EXPIRED`, `STOP_OPT_OUT`, `STOP_DISPUTE_FRAUD`, `STOP_PTP_ACTIVE`, and `STOP_MAX_RETRIES`.
  * **RBI 2026 E-Mandate AFA Verification:** Checks if amount $\le ₹15,000$ (Standard) or $\le ₹1,00,000$ (Exempt categories: Mutual Funds, Insurance, Credit Card bills). Prohibits direct auto-debit if cap is exceeded.
  * **Communication Classification (TRAI TCCCPR):** Tags messages as `TRANSACTIONAL`, `SERVICE`, `RECOVERY`, or `PROMOTIONAL` and applies DND filters.
  * **MSMED Act 2006 (Sections 15 & 16):** Scopes commercial invoices from registered Micro & Small Enterprise (MSE) suppliers to the 45-day statutory ceiling.

### 4. Intelligent Scheduler & Execution Engine
* **TRAI Quiet Hours Filter:** Restricts automated interactions to **08:00 AM – 08:00 PM IST**. Late-night failures are safely held in the **Delayed Dispatch Queue** for 08:05 AM release.
* **Smart Mandate Retry Sequencer:**
  * Dispatches mandatory **$\ge 24$-hour Pre-Debit Notifications** with opt-out mechanisms.
  * Snaps retries to predicted salary/liquidity cycles (1st–5th / 25th–30th).
  * Enforces **$\ge 48$-hour cooling intervals** and a **hard cap of 3 retries**.
* **Dynamic AFA Payment Link Generator:** Dispatches 1-click OTP checkout links for charges $> ₹15\text{k} / ₹1\text{L}$ and mandate instrument update links.
* **Multi-Channel Conversational Engine:**
  * **WhatsApp 1-Click UPI Deep-Links:** Instant app-switch payment links for expired UPI collect requests.
  * **Hinglish AI Voice Recovery Agent:** Empathetic, respectful voice recovery with Promise-to-Pay (PTP) negotiation.
  * **Promise-to-Pay (PTP) Tracker:** Automatically freezes retries until `PTP_PROMISE_DATE + 24 hours`.

### 5. Immutable Compliance Audit Trail
* Generates structured, tamper-evident audit logs adhering to the compliance schema:
  * End-to-end PII masking (PCI-DSS tokenization & DPDP 2023 compliance).
  * Auditable `afa_status` (`NOT_REQUIRED`, `EXEMPT_CATEGORY_SIP_INS_CC`, `AFA_REQUIRED_LINK_SENT`, `VALIDATED`).
  * Explicit logging of `statutory_rule_applied` and `internal_policy_applied`.
  * Verification that post-debit receipts include statutory grievance redressal details.

### 6. Measurement & Recovery Analytics Engine
* Aggregates real-time business and compliance KPIs:
  * **Total Revenue at Risk ($\Sigma \text{Risk}$):** Ingested rupee volume of payment failures and drop-offs.
  * **Measured Money Recovered ($\Sigma \text{Recovered}$):** Confirmed rupee value recovered via retries, links, voice bots, and PTP fulfillment.
  * **Net Recovery Rate (%):** $\frac{\Sigma \text{Recovered}}{\Sigma \text{Risk}} \times 100$.
  * **Compliance Health:** Zero regulatory violations across AFA caps, pre-debit notices, calling hours, and stopping rules.

---

## 📂 Project Structure & Reference Documentation

| File | Purpose & Contents |
| :--- | :--- |
| **[compliance-rules.md](file:///Users/harmitjetani/Documents/GitHub/razorpay-ai-challenge/compliance-rules.md)** | Comprehensive dual-layer regulatory specification (RBI 2026 E-Mandate Framework, ₹15k/₹1L AFA caps, 24h pre-debit alerts, TRAI communication taxonomy, MSMED Act 45-day rule, DPDP Act 2023, 7 stopping rules, and audit schema). |
| **[root-cause-taxonomy.md](file:///Users/harmitjetani/Documents/GitHub/razorpay-ai-challenge/root-cause-taxonomy.md)** | Razorpay 3-tier error model taxonomy (`source` / `step` / `reason`), 12 concrete error buckets, retryability rules, 10 critical production edge cases (Zombie payments, salary cycle traps, race conditions, partial payments), and Python classifier code. |
| **[README.md](file:///Users/harmitjetani/Documents/GitHub/razorpay-ai-challenge/README.md)** | System architecture diagram (Mermaid.js), pipeline walkthrough, stage breakdown, and verification metrics. |

---

## 🎯 The Bar
> **Don’t just identify the problem. Show measured money recovered across a batch, with compliant escalation, stopping rules, and an audit trail.**