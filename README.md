# Razorpay AI Challenge: Track 03 — AI Revenue Recovery
> **"Find revenue that’s slipping away and win it back"**

An autonomous, audit-grade AI Revenue Recovery Agent that detects revenue at risk across recurring payment failures, diagnoses root causes using Razorpay's 3-tier error model and LLM-assisted ambiguity parsing, routes actions through statutory RBI/TRAI compliance policies, executes bounded interventions, and proves measured money recovered compared against a naive baseline with an immutable audit trail.

---

## 🎯 Implementation Scope & Core Focus

* **Primary End-to-End Core:** **Razorpay-Native Payment & Mandate Recovery (Soft & Hard Failures)** — fully implemented end-to-end with the 12-bucket classifier, LLM intent parsing, RBI 2026 E-Mandate compliance checks, smart salary-cycle retry sequencer, dynamic instrument/AFA links, 7 deterministic stopping rules, and measured recovery analytics against a naive baseline.
* **Secondary Modular Extensions:** Checkout Drop-Off recovery and B2B Receivables dunning with PTP tracking are fully designed, architected, and surfaced in the decision router.

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

    %% STAGE 2: CLASSIFIER & LLM DIAGNOSTIC ENGINE
    subgraph S2 ["2. Diagnosis & Root-Cause Classifier"]
        PARSE["Razorpay Error Parser<br/>(source / step / reason)"]
        TRIAGE{"Failure Triage &<br/>Confidence Check"}
        
        SOFT["Soft / Retryable Failure<br/>(insufficient_funds, bank_server_down, timeout)"]
        HARD["Hard / Non-Retryable Failure<br/>(card_expired, mandate_revoked, mandate_expired)"]
        DROP["Drop-Off / Commercial Overdue<br/>(cart_abandoned, overdue_b2b_invoice)"]
        
        LLM_PARSER["LLM Ambiguity Resolver<br/>• Parses raw/unmapped bank strings<br/>• Extracts structured PTP dates/amounts<br/>• Evaluates fraud-adjacent context"]
        HUMAN_ESC["HUMAN_REVIEW Escalation<br/>(Low confidence / Fraud-adjacent / High risk)"]
    end

    %% STAGE 3: COMPLIANCE ROUTER (DUAL-LAYER)
    subgraph S3 ["3. Compliance & Policy Router (Dual-Layer)"]
        STOP{"Deterministic<br/>Stopping Engine"}
        STOPS_TRIGGERED["HALT WORKFLOW<br/>(STOP_PAID, STOP_MANDATE_REVOKED, STOP_MANDATE_EXPIRED,<br/>STOP_OPT_OUT, STOP_DISPUTE_FRAUD, STOP_PTP_ACTIVE, STOP_MAX_RETRIES)"]
        
        STAT_CHECK{"Statutory Checks (RBI / MSMED)"}
        AFA_CAP{"Amount <= RBI AFA Cap?<br/>(Standard: <= ₹15k | SIP/Ins/CC: <= ₹1L)"}
        
        TRAI_CHECK{"TRAI DLT Communication Router"}
        COMM_CLASS["Classify Stream:<br/>TRANSACTIONAL / SERVICE_IMPLICIT / SERVICE_EXPLICIT / PROMOTIONAL"]
    end

    %% STAGE 4: SCHEDULER & INTERVENTIONS
    subgraph S4 ["4. Intelligent Scheduler & Execution Engine"]
        TIME_FILTER{"TRAI Quiet Hours Check<br/>(08:00 AM - 08:00 PM IST)"}
        QUIET_QUEUE["Delayed Dispatch Queue<br/>(Hold until 08:05 AM IST)"]
        
        EXEC_RETRY["Smart Mandate Retry Sequencer<br/>• Queue >= 24h Pre-Debit Alert (Statutory)<br/>• Snap to Salary Window 1st-5th / 25th-30th (Heuristic)<br/>• Min 48h Cooling Interval & Max 3 Retries (Policy)"]
        
        EXEC_INSTRUMENT_LINK["Dynamic Instrument / AFA Link<br/>• reason: afa_threshold_exceeded (>₹15k / >₹1L)<br/>• reason: instrument_update_required (Expired card)"]
        
        EXEC_CHANNELS["Multi-Channel Conversational Engine<br/>• WhatsApp 1-Click UPI Deep-Links<br/>• Hinglish Voice Recovery Bot<br/>• LLM Promise-to-Pay (PTP) State Tracker"]
    end

    %% STAGE 5: AUDIT LOG
    subgraph S5 ["5. Immutable Compliance Audit Trail"]
        AUDIT_ENGINE["Tamper-Evident Audit Logger"]
        AUDIT_REC["JSON Audit Record<br/>• audit_id & ISO timestamp<br/>• Masked PII (PCI-DSS & DPDP 2023)<br/>• afa_status (NOT_REQUIRED / VALIDATED)<br/>• statutory_rule & internal_policy applied<br/>• grievance_details_included: true"]
    end

    %% STAGE 6: MEASUREMENT & ANALYTICS
    subgraph S6 ["6. Measurement & Recovery Analytics Engine"]
        BASELINE_COMPARE["Comparative Benchmark Engine<br/>Agentic Recovery vs. Naive Retry Baseline<br/>(Dumb 24h fixed retry, no AFA checks, no cooling)"]
        
        KPI_METRICS["Live Recovery Metrics Dashboard<br/>• Total Revenue at Risk (₹)<br/>• Measured Money Recovered (₹)<br/>• Net Recovery Rate (%) & Lift over Baseline<br/>• 0 Compliance-Guard Bypasses (Enforced by Design)"]
        
        SETTLE_EVENT["Outcome Webhook Ingestion<br/>(payment.captured / invoice.paid)"]
    end

    %% DATA FLOW CONNECTIONS
    W1 --> PARSE
    W2 --> PARSE
    W3 --> PARSE

    PARSE --> TRIAGE
    TRIAGE -->|Confidence >= 0.85 & Soft| SOFT
    TRIAGE -->|Confidence >= 0.85 & Hard| HARD
    TRIAGE -->|Drop-off / Invoice| DROP
    TRIAGE -->|Ambiguous / Unmapped| LLM_PARSER
    
    LLM_PARSER -->|Resolved| TRIAGE
    LLM_PARSER -->|Low Confidence < 0.70 / Fraud Flag| HUMAN_ESC
    HUMAN_ESC --> AUDIT_ENGINE

    SOFT --> STOP
    HARD --> STOP
    DROP --> STOP

    STOP -->|Boundary Hit| STOPS_TRIGGERED
    STOP -->|Active Case| STAT_CHECK

    STAT_CHECK --> AFA_CAP
    STAT_CHECK --> COMM_CLASS

    AFA_CAP -->|Amount <= Cap: afa_status = NOT_REQUIRED| COMM_CLASS
    AFA_CAP -->|Amount > Cap: afa_status = AFA_REQUIRED| COMM_CLASS

    COMM_CLASS --> TIME_FILTER
    TIME_FILTER -->|Outside 08:00-20:00| QUIET_QUEUE
    TIME_FILTER -->|Inside 08:00-20:00 & Retryable| EXEC_RETRY
    TIME_FILTER -->|Inside 08:00-20:00 & Non-Retryable/AFA| EXEC_INSTRUMENT_LINK
    TIME_FILTER -->|Inside 08:00-20:00 & Drop-off/Voice| EXEC_CHANNELS
    
    QUIET_QUEUE -->|At 08:05 AM IST| TIME_FILTER

    EXEC_RETRY --> AUDIT_ENGINE
    EXEC_INSTRUMENT_LINK --> AUDIT_ENGINE
    EXEC_CHANNELS --> AUDIT_ENGINE
    STOPS_TRIGGERED --> AUDIT_ENGINE

    AUDIT_ENGINE --> AUDIT_REC
    AUDIT_REC --> BASELINE_COMPARE
    BASELINE_COMPARE --> KPI_METRICS
    
    %% DOUBLE-DEBIT PREVENTION FEEDBACK LOOP
    SETTLE_EVENT --> STOP
    EXEC_CHANNELS -.->|Payment Completed| SETTLE_EVENT
    EXEC_RETRY -.->|Debit Succeeded| SETTLE_EVENT
    EXEC_INSTRUMENT_LINK -.->|OTP Verified / Instrument Updated| SETTLE_EVENT
    SETTLE_EVENT --> KPI_METRICS
```

---

## 🔄 Architectural Stage Breakdown

### 1. Ingestion Layer (`Revenue at Risk`)
* Ingests payment failure and revenue degradation events across core streams:
  * **Failed Subscriptions & Mandates:** `payment.failed`, `subscription.halted` on cards and UPI AutoPay.
  * **Gateway & Network Degrades:** Timeout webhooks, CBS banking 503 outages.
  * **Checkout Abandonments & Drop-offs:** Cart drop-off telemetry and UPI intent session expirations.
  * **B2B Receivables Ledger:** Overdue commercial tax invoices.

### 2. Diagnosis & Classifier (with LLM Diagnostic Engine)
* **Deterministic Classifier:** Fast regex and error-code triage mapping Razorpay's `source` / `step` / `reason` errors into **12 concrete buckets** documented in [root-cause-taxonomy.md](file:///Users/harmitjetani/Documents/GitHub/razorpay-ai-challenge/root-cause-taxonomy.md).
* **LLM Diagnostic & Intent Engine:**
  * **Unstructured Error Resolution:** Disambiguates free-form bank decline text and unknown error payloads.
  * **PTP (Promise-to-Pay) Extraction:** Parses unstructured chat/voice transcripts into structured `{ptp_date, ptp_amount, condition}` entities.
* **Human-in-the-Loop Escalation (`HUMAN_REVIEW`):**
  * If classification confidence is $< 0.70$, or if fraud/chargeback risk flags are detected, the system routes the event to manual operations instead of taking automated action.

### 3. Compliance & Policy Router (Dual-Layer Governance)
* Separates statutory law from internal engineering policies, as codified in [compliance-rules.md](file:///Users/harmitjetani/Documents/GitHub/razorpay-ai-challenge/compliance-rules.md):
  * **Deterministic Stopping Rules:** Instantly halts workflows on `STOP_PAID`, `STOP_MANDATE_REVOKED`, `STOP_MANDATE_EXPIRED`, `STOP_OPT_OUT`, `STOP_DISPUTE_FRAUD`, `STOP_PTP_ACTIVE`, and `STOP_MAX_RETRIES`.
  * **RBI 2026 E-Mandate AFA Verification (Statutory):** Checks if amount $\le ₹15,000$ (Standard) or $\le ₹1,00,000$ (Exempt categories: Mutual Funds, Insurance, Credit Card bills). Prohibits direct auto-debit if cap is exceeded.
  * **TRAI DLT Communication Router (Statutory):** Categorizes outbound messages into official DLT streams: `TRANSACTIONAL`, `SERVICE_IMPLICIT`, `SERVICE_EXPLICIT`, and `PROMOTIONAL`.
  * **MSMED Act 2006 (Statutory Boundary):** Scopes commercial invoices from registered Micro & Small Enterprise (MSE) suppliers to the 45-day statutory ceiling.

### 4. Intelligent Scheduler & Execution Engine
* **TRAI Quiet Hours Filter (Internal Policy):** All outbound proactive communications (SMS, WhatsApp, Voice, and dynamic payment links) pass through the 08:00 AM – 08:00 PM IST filter. Late-night failures are safely held in the **Delayed Dispatch Queue** for 08:05 AM release.
* **Smart Mandate Retry Sequencer:**
  * Dispatches statutory **$\ge 24$-hour Pre-Debit Notifications** with opt-out mechanisms.
  * Applies **Salary-Cycle Snapping Heuristic** (1st–5th / 25th–30th) to prevent premature retry exhaustion.
  * Enforces **$\ge 48$-hour cooling intervals** and a **hard cap of 3 retries** (Internal Safety Policy).
* **Dynamic Instrument / AFA Link (`EXEC_INSTRUMENT_LINK`):**
  * Dispatches 1-click AFA OTP checkout links when `reason: "afa_threshold_exceeded"`.
  * Dispatches secure mandate update links when `reason: "instrument_update_required"`.
* **Multi-Channel Conversational Engine:**
  * **WhatsApp 1-Click UPI Deep-Links:** Instant app-switch payment links for expired UPI collect requests.
  * **Hinglish AI Voice Recovery Agent:** Empathetic voice recovery with PTP negotiation.
  * **Promise-to-Pay (PTP) Tracker:** Automatically freezes retries until `PTP_PROMISE_DATE + 24 hours`.

### 5. Immutable Compliance Audit Trail
* Generates structured, tamper-evident audit records adhering to the compliance schema:
  * End-to-end PII masking (PCI-DSS tokenization & DPDP 2023 compliance across prompts, context, logs, and exports).
  * Auditable `afa_status` (`NOT_REQUIRED`, `EXEMPT_CATEGORY_SIP_INS_CC`, `AFA_REQUIRED_LINK_SENT`, `VALIDATED`).
  * Explicit separation of `statutory_rule_applied` vs `internal_policy_applied`.
  * Verification that post-debit receipts include statutory grievance redressal details (`grievance_details_included: true`).

### 6. Measurement & Comparative Benchmark Engine
* **Comparative Benchmark (`BASELINE_COMPARE`):**
  * Compares the **Agentic Recovery Engine** against a **Naive Retry Baseline** (standard dumb 24-hour fixed retry without liquidity heuristics, AFA threshold checks, cooling windows, or stopping rules).
* **Metrics Dashboard:**
  * **Total Revenue at Risk ($\Sigma \text{Risk}$):** Ingested volume of payment failures.
  * **Measured Money Recovered ($\Sigma \text{Recovered}$):** Confirmed rupee value recovered.
  * **Net Recovery Lift (%):** Incremental revenue recovered over naive baseline.
  * **Bank Penalty Reduction (%):** Reduction in customer bank bounce charges achieved through cooling intervals and salary-cycle snapping.
  * **Compliance Integrity:** **0 Compliance-Guard Bypasses** (enforced by design & architecture, not just observed).

---

## 📂 Project Structure & Reference Documentation

| File | Purpose & Contents |
| :--- | :--- |
| **[compliance-rules.md](file:///Users/harmitjetani/Documents/GitHub/razorpay-ai-challenge/compliance-rules.md)** | Comprehensive dual-layer regulatory specification (RBI 2026 E-Mandate Framework, ₹15k/₹1L AFA caps, 24h pre-debit alerts, TRAI DLT communication taxonomy, MSMED Act 45-day rule, DPDP Act 2023, 7 stopping rules, and audit schema). |
| **[root-cause-taxonomy.md](file:///Users/harmitjetani/Documents/GitHub/razorpay-ai-challenge/root-cause-taxonomy.md)** | Razorpay 3-tier error model taxonomy (`source` / `step` / `reason`), 12 concrete error buckets, retryability rules, 10 critical production edge cases (Zombie payments, salary cycle traps, race conditions, partial payments), and Python classifier code. |
| **[README.md](file:///Users/harmitjetani/Documents/GitHub/razorpay-ai-challenge/README.md)** | System architecture diagram (Mermaid.js), pipeline walkthrough, stage breakdown, and verification metrics. |

---

## 🎯 The Bar
> **Don’t just identify the problem. Show measured money recovered across a batch, with compliant escalation, stopping rules, and an audit trail.**