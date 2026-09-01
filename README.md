# ⚡ Autonomous AI Revenue Recovery Platform
> **"Find revenue that’s slipping away and win it back — with mathematical precision and zero regulatory risk."**

[![Test Suite](https://img.shields.io/badge/Unit%20Tests-71%20Passing%20(0.18s)-success.svg)](tests/)
[![Cryptographic Ledger](https://img.shields.io/badge/Audit%20Ledger-SHA--256%20Chained%20(2%2C548%20Blocks)-blue.svg)](data/full_batch_audit_trail.json)
[![Regulatory Compliance](https://img.shields.io/badge/Compliance-100%25%20Statutory%20Safe%20(0%20Violations)-success.svg)](compliance-rules.md)
[![Measured Recovery Lift](https://img.shields.io/badge/Measured%20Lift-%2B164.2%25%20vs%20Baseline-success.svg)](data/comparative_benchmark_results.json)

---

## 🎯 Executive Summary

In Indian subscription commerce, **up to 15–25% of recurring payments fail** due to insufficient balances, expired mandates, bank server timeouts, and category limits. Most platforms respond with **naive cron-job retries** (fixed 24-hour retries) or generic spam emails that nobody reads.

This naive approach creates two fatal problems:
1. **Lost Revenue**: High churn from retrying at the wrong time (e.g. before month-end salary credit).
2. **Severe Regulatory Fines**: Violates [**RBI 2026 E-Mandate rules**](#rule-1-rbi-2026-e-mandate) (lack of 24h pre-debit notices, bypassing [₹15,000 / ₹1,00,000 AFA caps](#rule-2-statutory-afa-caps)), [**TRAI DND/Quiet Hours**](#rule-4-trai-quiet-hours) (calling customers at night), and [**Consumer Protection Act (CPA 2019)**](#rule-5-cpa-2019-dispute-lock) (dunning users with active fraud disputes).

### The Solution: Autonomous AI Revenue Recovery Agent
Our platform acts as a **smart, statutory-compliant revenue recovery orchestrator**:
* **Diagnoses Root Cause**: Two-tier classifier mapping failure codes (Razorpay source/step/reason model) + local semantic intent engine for ambiguous bank text.
* **Autonomous LLM Decision Agent (P0)**: `RecoveryDecisionAgent` evaluates candidate recovery actions, generates mathematical EV justifications, and outputs human-auditable reasoning via an OpenRouter cascade (Gemini 2.5 Flash / Llama 4 Scout / DeepSeek R1).
* **Dual-Layer Statutory Invariants**: Programmatically guarantees 100% compliance with [RBI](#rule-1-rbi-2026-e-mandate), [TRAI](#rule-4-trai-quiet-hours), [CPA 2019](#rule-5-cpa-2019-dispute-lock), and [DPDP Act 2023](#rule-7-dpdp-act-2023).
* **Multi-Rail Smart Recovery**: Coordinates 48h cooling intervals, salary-cycle snapping (1st–5th / 25th–30th), dynamic AFA OTP payment links, WhatsApp 1-click UPI intent, 3-step checkout drop-off drip recovery (WhatsApp → Email → SMS), and empathetic Hinglish voice recovery bots with [Promise-to-Pay (PTP) freezing](#rule-6-ptp-grace-window).
* **Blockchain-Grade Cryptographic Audit Ledger**: Every decision produces a tamper-evident, [SHA-256 hash-chained audit record](#rule-9-cryptographic-audit-ledger).

---

## ⚡ Quickstart

```bash
# Optional: Set OpenRouter API key for live LLM cascade evaluation (works 100% offline without key)
export OPENROUTER_API_KEY="your-openrouter-key"

# 1. Launch the Live Enterprise FinTech SaaS Dashboard
python3 app/server.py 8888
# 👉 Open http://localhost:8888 in your browser

# 2. Run the Interactive Single-Transaction Recovery Simulation Demo
python3 scripts/run_single_recovery_demo.py

# 3. Run the Full 750-Transaction Head-to-Head Comparative Benchmark
python3 scripts/run_comparative_benchmark.py

# 4. Generate Executive Regulatory PDF Audit Report
python3 scripts/generate_pdf_report.py

# 5. Run the Complete Automated Test Suite (71 Tests Passing in ~0.18s)
pytest
# or: python3 -m unittest discover -s tests
```

---

## 📊 Measured Benchmark: AI Agent vs. Naive Baseline

Evaluated across the exact same deterministic dataset of **750 payment failures** representing **₹2,27,71,364.25 (₹2.28 Crore)** in portfolio volume at risk over a simulated 14-day recovery window:

| Evaluation Metric | Naive 24h Fixed Retry (Baseline) | Smart AI Recovery Agent (Ours) | Measured Advantage / Impact |
| :--- | :--- | :--- | :--- |
| **Total Revenue Recovered** | **₹20,54,913.61** | **₹54,29,649.50** | **+₹33,74,735.89 (+164.2% Lift 🚀)** |
| **Recovery Yield Rate** | **9.02%** | **23.84%** | **+14.82% Absolute Yield Gain** |
| **Successful Recoveries** | 51 transactions | **198 transactions** | **+147 Additional Rescued Subscriptions** |
| **Statutory Violations Committed** | **599 Violations ⚠️** *(Severe Fine Risk)* | **0 Violations 🛡️** *(100% Invariant Safe)* | **100% Compliance Risk Elimination** |
| **[RBI ≥ 24h Pre-Debit Notices](#rule-1-rbi-2026-e-mandate)** | 0 sent (100% Non-Compliant) | **424 Dispatched Compliantly** | Full Statutory Notice Window Met |
| **[AFA Limit Respect (>₹15k / >₹1L)](#rule-2-statutory-afa-caps)** | 0 checked (Illegal debits attempted) | **114 Dynamic AFA Links Routed** | Zero Unauthorized Auto-Debits |
| **[Revoked Mandates Halted](#rule-3-revoked-mandates-halted)** | 0 halted (Harassed cancelled users) | **32 Instantly Quarantined** | Zero Cancelled Mandate Debits |
| **[TRAI Quiet Hours Suppressed](#rule-4-trai-quiet-hours)** | 0 delayed (Violated night rules) | **42 DND / Quiet Numbers Held** | Zero TRAI UCC/DND Breaches |
| **[Active Dispute / Fraud Freezes](#rule-5-cpa-2019-dispute-lock)** | 0 frozen (Dunning continued on fraud) | **20 Immediate Freezes Enforced** | Full CPA 2019 Anti-Harassment Safety |
| **[Promise-to-Pay (PTP) Honored](#rule-6-ptp-grace-window)** | 0 honored (Interrupted promise) | **33 Accounts Frozen in Grace Window** | Maximum Customer Goodwill & Trust |
| **[Tamper-Evident Ledger Integrity](#rule-9-cryptographic-audit-ledger)** | None (Unverifiable logs) | **2,548 SHA-256 Chained Blocks** | Verified Blockchain-Grade Auditability |

---

## 🏛️ End-to-End System Architecture

```mermaid
flowchart TD
    %% INGESTION
    subgraph S1 ["1. Ingestion Layer (Revenue at Risk)"]
        W1["Razorpay Gateway Webhooks<br/>(payment.failed, subscription.halted)"]
        W2["Drop-off Telemetry & Invoices<br/>(Cart abandonment, B2B overdue)"]
    end

    %% CLASSIFIER
    subgraph S2 ["2. Diagnostic Engine & Root Cause Triage"]
        PARSE["Razorpay Error Model Parser<br/>(source / step / reason)"]
        STAGE1{"Deterministic Rule Classifier<br/>(13-Bucket Taxonomy)"}
        
        SOFT["Soft Liquidity Failure<br/>(insufficient_funds, bank_server_down)"]
        HARD["Hard Failure / Terminal<br/>(card_expired, mandate_revoked)"]
        CART["Checkout Drop-Off<br/>(abandoned_cart, payment_dropped)"]
        
        LLM_PARSER["Semantic Intent Fallback<br/>• Raw unmapped bank decline disambiguation<br/>• PTP extraction & fraud context isolation"]
        HUMAN_ESC["Human Ops Quarantine<br/>(Conf < 0.70 / High Risk Flag)"]
    end

    %% AI DECISION AGENT
    subgraph S3 ["3. AI Recovery Decision Agent (Reasoning Layer - P0)"]
        AGENT_REASON["RecoveryDecisionAgent<br/>• Evaluates candidate compliant action menu<br/>• Computes Net Expected Value (EV) score<br/>• Generates human-auditable reasoning"]
        LLM_CASCADE["OpenRouter LLM Cascade<br/>Gemini 2.5 Flash ➔ Llama 4 ➔ DeepSeek R1"]
    end

    %% COMPLIANCE ROUTER
    subgraph S4 ["4. Programmatic Statutory Compliance Router (Hard Invariants)"]
        GUARD1{"Guard 1: CPA 2019 Dispute Quarantine<br/>(Is chargeback/fraud dispute active?)"}
        GUARD2{"Guard 2: Mandate Revocation Invariant<br/>(Is mandate cancelled/revoked by user?)"}
        GUARD3{"Guard 3: Zombie Retry Cap<br/>(Attempt count >= 3 or >14 days?)"}
        GUARD4{"Guard 4: RBI 2026 E-Mandate AFA Check<br/>(Amount > ₹15k standard or > ₹1L exempt?)"}
        GUARD5{"Guard 5: TRAI Quiet Hours & DND<br/>(Time in 08:00–20:00 IST?)"}
        
        HALT_QUARANTINE["HALT WORKFLOW & QUARANTINE<br/>(STOP_PAID, STOP_MANDATE_REVOKED, STOP_DISPUTE_FRAUD, STOP_MAX_RETRIES)"]
    end

    %% SCHEDULER & EXECUTION
    subgraph S5 ["5. Clock Scheduler & Multi-Channel Execution (P2 & P3)"]
        SCHED["Discrete-Event Clock Scheduler<br/>(Salary-cycle snapping + 48h cooling)"]
        
        ACT_NOTICE["Pre-Debit Notice Dispatch<br/>(WhatsApp DLT Service Implicit >= 24h)"]
        ACT_RETRY["Smart Salary-Cycle Auto-Debit<br/>(1st-5th / 25th-30th + 48h cooling)"]
        ACT_AFA["Dynamic AFA OTP Checkout Link<br/>(For recurring > ₹15k / > ₹1L)"]
        ACT_CART["3-Step Checkout Drip Recovery<br/>T+0 WhatsApp ➔ T+24h Email ➔ T+48h SMS"]
        ACT_VOICE["Empathetic Hinglish Voice Bot<br/>(Promise-to-Pay negotiation)"]
    end

    %% AUDIT & SETTLEMENT
    subgraph S6 ["6. Cryptographic Audit Trail & Settlement"]
        AUDIT["SHA-256 Chained Audit Ledger<br/>(DPDP 2023 PII Masked, 2,548 Blocks)"]
        SETTLE["Outcome Settlement Webhook<br/>(payment.captured / invoice.paid)"]
        RECOVERED_STATE["Terminal State: RECOVERED 🚀<br/>(Instant queue purge + statutory receipt)"]
    end

    %% FLOW CONNECTIONS
    W1 --> PARSE
    W2 --> PARSE
    PARSE --> STAGE1
    STAGE1 -->|"Soft Failure"| SOFT
    STAGE1 -->|"Hard Stop"| HARD
    STAGE1 -->|"Cart Abandonment"| CART
    STAGE1 -->|"Ambiguous / Unmapped"| LLM_PARSER
    
    LLM_PARSER -->|"Resolved"| SOFT
    LLM_PARSER -->|"Low Confidence"| HUMAN_ESC
    
    SOFT --> AGENT_REASON
    CART --> AGENT_REASON
    HARD --> AGENT_REASON
    HUMAN_ESC --> AGENT_REASON
    
    AGENT_REASON <--> LLM_CASCADE
    AGENT_REASON --> GUARD1
    
    GUARD1 -->|"Dispute Active"| HALT_QUARANTINE
    GUARD1 -->|"Clear"| GUARD2
    
    GUARD2 -->|"Revoked"| HALT_QUARANTINE
    GUARD2 -->|"Valid"| GUARD3
    
    GUARD3 -->|"Max Attempts Reached"| HALT_QUARANTINE
    GUARD3 -->|"Within Limits"| GUARD4
    
    GUARD4 -->|"Amount > Cap"| ACT_AFA
    GUARD4 -->|"Amount <= Cap"| GUARD5
    
    GUARD5 -->|"Night (20:00-08:00)"| SCHED
    GUARD5 -->|"Daytime (08:00-20:00)"| ACT_NOTICE
    
    CART --> ACT_CART
    ACT_CART --> SETTLE
    
    ACT_NOTICE --> SCHED
    SCHED --> ACT_RETRY
    ACT_RETRY -->|"Soft Failure"| ACT_VOICE
    ACT_VOICE -->|"PTP Commitment"| SCHED
    
    ACT_RETRY --> SETTLE
    ACT_AFA --> SETTLE
    SETTLE --> RECOVERED_STATE
    
    HALT_QUARANTINE --> AUDIT
    ACT_NOTICE --> AUDIT
    ACT_RETRY --> AUDIT
    ACT_AFA --> AUDIT
    ACT_CART --> AUDIT
    ACT_VOICE --> AUDIT
    RECOVERED_STATE --> AUDIT
```

---

## 🔄 9-State Finite State Machine (FSM) Lifecycle

The recovery engine enforces all statutory waiting periods, cooling-off intervals, stopping rules, and escalation paths through a deterministic 9-state finite state machine:

```mermaid
flowchart TD
    %% ─────────────────────────────────────────────────────────────
    %% STAGE 1: INGESTION & DIAGNOSTIC TRIAGE (P0 AGENT)
    %% ─────────────────────────────────────────────────────────────
    subgraph S1 ["1. Ingestion & Diagnostic Triage (P0 Agent)"]
        START(((Start))) -->|"Gateway Webhook"| S_DETECTED["1. DETECTED\nIngest Failure Payload"]
        S_DETECTED -->|"Parse Error Model"| S_DIAG["2. DIAGNOSING\nRule Triage & LLM Agent Reasoning"]
        S_DIAG -->|"Low Confidence (< 0.70)"| S_HUMAN["4. HUMAN_REVIEW\nManual Ops Quarantine Queue"]
    end

    %% ─────────────────────────────────────────────────────────────
    %% STAGE 2: SCHEDULED NOTICE & AUTOMATED RETRIES (P2 DRIP)
    %% ─────────────────────────────────────────────────────────────
    subgraph S2 ["2. Automated Recovery Ladder (P2 Drip)"]
        S_SCHED["3. ACTION_SCHEDULED\n24h Notice, Cooling, or Cart Drip"]
        S_RETRY["5. RETRYING\nSalary-Cycle Auto-Debit & Multi-Rail"]
        
        S_SCHED -->|"Notice & Cooling Elapsed"| S_RETRY
        S_RETRY -.->|"Attempt #1 Failed (Requeue)"| S_SCHED
        S_RETRY -.->|"Attempt #2 Failed (Digital Nudge / Drip)"| S_RETRY
    end

    %% ─────────────────────────────────────────────────────────────
    %% STAGE 3: VOICE ESCALATION & PROMISE-TO-PAY
    %% ─────────────────────────────────────────────────────────────
    subgraph S3 ["3. Voice Negotiation & PTP Grace Window"]
        S_ESCALATED["6. ESCALATED\nHinglish Voice Bot Outreach"]
        S_PTP["7. PTP_FROZEN\nOutreach Paused in Grace Window"]
        
        S_ESCALATED -->|"PTP Commitment Extracted"| S_PTP
        S_PTP -.->|"Grace Expired Unpaid"| S_RETRY
    end

    %% ─────────────────────────────────────────────────────────────
    %% STAGE 4: TERMINAL OUTCOMES
    %% ─────────────────────────────────────────────────────────────
    subgraph S4 ["4. Terminal Outcomes"]
        S_RECOVERED["8. RECOVERED 🚀\nPayment Succeeded (STOP_PAID)"]
        S_UNREC["9. UNRECOVERABLE 🛑\nQuarantine / Opt-Out / Debt Expiry"]
        
        S_RECOVERED --> END_REC(((End)))
        S_UNREC --> END_UNREC(((End)))
    end

    %% ─────────────────────────────────────────────────────────────
    %% INTER-STAGE TRANSITIONS
    %% ─────────────────────────────────────────────────────────────
    S_DIAG -->|"Compliant Action Approved (Agent EV)"| S_SCHED
    S_DIAG -->|"Hard Stop (Revoked / Dispute)"| S_UNREC

    S_HUMAN -->|"Operator Approved"| S_SCHED
    S_HUMAN -->|"Operator Rejected"| S_UNREC

    S_RETRY -->|"Paid via Auto-Debit / Checkout Link"| S_RECOVERED
    S_RETRY -->|"Attempt #3 Failed (Debit Cap)"| S_ESCALATED
    S_RETRY -->|"Customer Opt-Out"| S_UNREC

    S_ESCALATED -->|"Paid via Call Link"| S_RECOVERED
    S_ESCALATED -->|"Outreach Exhausted (14d)"| S_UNREC

    S_PTP -->|"Paid During Grace Window"| S_RECOVERED

    %% ─────────────────────────────────────────────────────────────
    %% UI COLOR THEMING (SaaS Light & Dark Mode Compatible)
    %% ─────────────────────────────────────────────────────────────
    classDef initial fill:#f8fafc,stroke:#64748b,stroke-width:2px,color:#0f172a;
    classDef active fill:#eff6ff,stroke:#2563eb,stroke-width:2px,color:#1e3a8a;
    classDef purple fill:#faf5ff,stroke:#7c3aed,stroke-width:2px,color:#4c1d95;
    classDef warning fill:#fffbeb,stroke:#d97706,stroke-width:2px,color:#78350f;
    classDef success fill:#f0fdf4,stroke:#16a34a,stroke-width:2px,color:#14532d;
    classDef danger fill:#fef2f2,stroke:#dc2626,stroke-width:2px,color:#7f1d1d;

    class S_DETECTED,S_DIAG initial;
    class S_SCHED,S_RETRY active;
    class S_HUMAN purple;
    class S_ESCALATED,S_PTP warning;
    class S_RECOVERED success;
    class S_UNREC danger;
```

---

## 📜 Core Compliance Rules & Indian Regulatory Guardrails

To win revenue back without causing regulatory fines, merchant churn, or harassment complaints, the agent strictly enforces 9 non-negotiable statutory & architectural guardrails:

<a id="rule-1-rbi-2026-e-mandate"></a>
### 1. 📋 RBI 2026 E-Mandate Framework (`RBI/DPSS/2026-27/396`) — ≥ 24h Pre-Debit Notice
* **What the law mandates**: Merchants must dispatch an explicit pre-debit alert to the customer at least 24 hours prior to every automated recurring charge, with the exact amount, merchant name, and an opt-out link.
* **What our agent enforces**: The scheduler automatically queues a WhatsApp/SMS alert and guarantees ≥ 24h has elapsed before executing any automated recurring debit.

<a id="rule-2-statutory-afa-caps"></a>
### 2. 💳 Statutory AFA Limit Caps (₹15,000 Standard / ₹1,00,000 Exempt Categories)
* **What the law mandates**: Auto-debit without OTP (AFA) is capped at ₹15,000 per cycle. A relaxed ceiling of ₹1,00,000 is allowed strictly for Mutual Funds (SIPs), Insurance Premiums, and Credit Card bills.
* **What our agent enforces**: Any transaction exceeding its statutory ceiling (e.g. ₹15,001 for OTT or ₹1,00,001 for SIPs) is programmatically blocked from direct auto-debit and converted into a dynamic AFA OTP checkout link.

<a id="rule-3-revoked-mandates-halted"></a>
### 3. 🚫 Customer Mandate Revocation Invariant (Instant Dunning Freeze)
* **What the law mandates**: Under RBI e-mandate guidelines, customers hold the legal right to cancel or revoke payment mandates via their issuing bank or merchant portal at any time. Debiting a revoked mandate is illegal.
* **What our agent enforces**: Webhooks or decline events signaling mandate cancellation immediately trigger Guard 2 (`STOP_MANDATE_REVOKED`), permanently purging all pending retries.

<a id="rule-4-trai-quiet-hours"></a>
### 4. 🌙 TRAI Telecom Commercial Communications Regulations (TCCCPR 2018) — Safe Contact Hours & DND
* **What the law mandates**: Commercial calls and dunning outreach are strictly prohibited during night quiet hours (08:00 PM to 08:00 AM IST) and to customers registered on the National DND Registry for marketing.
* **What our agent enforces**: Failures occurring at night are held in the Delayed Dispatch Queue for 08:30 AM release; all customer recovery messages use whitelisted DLT `SERVICE_IMPLICIT` streams.

<a id="rule-5-cpa-2019-dispute-lock"></a>
### 5. 🛑 Consumer Protection Act (CPA 2019) & CCPA Guidelines 2023 — Anti-Harassment & Dispute Lock
* **What the law mandates**: Repeated debit attempts or dunning communications while an active fraud dispute or chargeback is open constitute illegal harassment and unfair trade practices.
* **What our agent enforces**: When `dispute_active=True`, Guard 1 instantly freezes all dunning (`STOP_DISPUTE_FRAUD`), prevents further retries, and escalates the transaction for human review.

<a id="rule-6-ptp-grace-window"></a>
### 6. 🤝 Promise-to-Pay (PTP) Grace Window & Dunning Freeze Policy
* **What the operational standard mandates**: When a customer commits to pay by a specific date (e.g. during an empathetic voice bot call), further automated retries or dunning messages within that window breach customer trust.
* **What our agent enforces**: The engine transitions the transaction to `PTP_FROZEN`, halts all outreach, and sets a wake-up trigger 24 hours after the agreed date.

<a id="rule-7-dpdp-act-2023"></a>
### 7. 🔒 DPDP Act 2023 (Digital Personal Data Protection) — Complete PII Redaction
* **What the law mandates**: Customer Personally Identifiable Information (PII) must be protected, masked, and never exposed in plaintext across operational logs, telemetry, or third-party LLMs.
* **What our agent enforces**: All phone numbers (`+91-9876****4321`) and emails (`r****y@example.com`) are permanently redacted across runtime logs, JSON exports, and UI dashboards.

<a id="rule-8-msmed-act-2006"></a>
### 8. ⏱️ MSMED Act 2006 (Sections 15 & 16) — 45-Day B2B Payment Boundaries
* **What the law mandates**: Invoices from Micro and Small Enterprises must be settled within agreed periods not exceeding 45 days, after which penal compound interest applies.
* **What our agent enforces**: Overdue commercial invoices approaching 45 days bypass standard automated reminders and are immediately escalated to merchant finance operations.

<a id="rule-9-cryptographic-audit-ledger"></a>
### 9. 🛡️ Cryptographic SHA-256 Audit Trail & Ledger Integrity
* **What the engineering & audit standard mandates**: Every state transition must produce an immutable record linking back to the previous block's SHA-256 hash (`SHA-256(prev_hash : event_data)`) to guarantee zero post-hoc log tampering.
* **What our agent enforces**: All 2,548 transition events across the batch simulation form a verifiable cryptographic chain from genesis block `0000...0000` to the final settlement, with automated integrity verification on every audit export.

---

## 💥 Live Chaos & Fault Injection Sandbox

Inside the web dashboard, users can interact with the **Live Chaos Sandbox** to test how the system reacts in real time to unexpected production failures:

1. **⚡ Inject CBS Bank Outage (HDFC 503)**:
   * Simulates core banking downtime (`bank_server_down`).
   * *Engine Adaptation*: Prohibits immediate retries, schedules 48h cooling interval, and sends an alternate 1-click WhatsApp UPI intent checkout link.
   * *Expected Value*: Net EV = +₹6,374.35.
2. **🛑 Inject Active Fraud Dispute ([CPA 2019](#rule-5-cpa-2019-dispute-lock))**:
   * Simulates a chargeback dispute filed with the issuing bank (`dispute_active=True`).
   * *Engine Refusal*: Guard 1 enforces permanent quarantine (`STOP_DISPUTE_FRAUD`) → transitions immediately to `UNRECOVERABLE`. Zero customer touches sent.
3. **🌙 Inject TRAI Night Hours ([TRAI TCCCPR 2018](#rule-4-trai-quiet-hours))**:
   * Simulates a payment failure occurring at 11:30 PM.
   * *Engine Refusal*: Prohibits immediate notification dispatch; holds message in Delayed Queue for 9.0 hours and releases at 08:30 AM IST.

---

## 🧮 Expected Value (EV) Economic Scoring Engine

Every recovery action is scored by the economic decision model:

```
EV = (P_recover × Amount) - Channel Cost - Annoyance Penalty
```

* **P_recover**: Recovery probability derived from historical liquidity and mandate health (0.00 – 1.00).
* **Channel Cost**: Marginal dispatch expense (e.g. ₹0.15 for WhatsApp/SMS, ₹3.50 for Voice Bot, ₹0.00 for auto-debit).
* **Annoyance Penalty**: Quantified customer friction penalty (e.g. ₹4.00 for premature phone calls, ₹0.50 for pre-debit notices).
* **Policy Floor**: If EV ≤ 0, the action is automatically suppressed or downgraded to a cheaper digital channel.

---

## 🛡️ Programmatic Refusal Proofs (10 Edge Cases)

Every regulatory guardrail is verified by dedicated automated tests that assert the recovery router **strictly refuses** illegal operations and emits structured refusal audit records:

| Test ID | Edge Case Scenario | Statutory / Engineering Invariant | Verified Refusal Outcome |
| :--- | :--- | :--- | :--- |
| **[`EDGE-01`](edge-cases.md#1-edge-01-the-zombie-retry-trap-customer-failing-5x-in-a-row)** | [Zombie Retry Cap (3x Ceiling)](edge-cases.md#1-edge-01-the-zombie-retry-trap-customer-failing-5x-in-a-row) | Max 3 auto-debits within 14-day window. | **BLOCKED:** Throws `ComplianceViolationError`; transitions to `UNRECOVERABLE`. |
| **[`EDGE-02`](edge-cases.md#2-edge-02-the-15000-afa-straddle-1500100-standard-subscription)** | [₹15,001 Standard AFA Cap](edge-cases.md#2-edge-02-the-15000-afa-straddle-1500100-standard-subscription) | Direct auto-debit > ₹15,000 prohibited ([RBI DPSS 2026](#rule-2-statutory-afa-caps)). | **BLOCKED:** Auto-debit refused; dynamic AFA OTP payment link dispatched. |
| **[`EDGE-03`](edge-cases.md#3-edge-03-the-100000-exemption-straddle-10000100-mutual-fund-sip)** | [₹1,00,001 Exemption Straddle](edge-cases.md#3-edge-03-the-100000-exemption-straddle-10000100-mutual-fund-sip) | Mutual Funds / Insurance relaxed cap is ₹1,00,000 ([RBI Amendment 2023](#rule-2-statutory-afa-caps)). | **BLOCKED:** ₹1,00,001 auto-debit refused; converted to dynamic AFA OTP checkout link. |
| **[`EDGE-04`](edge-cases.md#4-edge-04-mandate-expiring-mid-retry)** | [Mandate Expiring in 24h](edge-cases.md#4-edge-04-mandate-expiring-mid-retry) | Mandate expires before cooling + retry window ([RBI E-Mandate](#rule-1-rbi-2026-e-mandate)). | **BLOCKED:** Refuses auto-debit; dispatches instrument renewal link. |
| **[`EDGE-05`](edge-cases.md#5-edge-05-trai-quiet-hours-sleep-trap)** | [TRAI Quiet Hours Violation](edge-cases.md#5-edge-05-trai-quiet-hours-sleep-trap) | Outbound customer touch at 11:30 PM IST ([TRAI TCCCPR 2018](#rule-4-trai-quiet-hours)). | **BLOCKED:** Instant send blocked; queued for release at 08:30 AM IST next morning. |
| **[`EDGE-06`](edge-cases.md#6-edge-06-promise-to-pay-ptp-race-condition)** | [Promise-to-Pay (PTP) Grace Window](edge-cases.md#6-edge-06-promise-to-pay-ptp-race-condition) | Customer committed to pay on Sept 5th ([PTP Policy](#rule-6-ptp-grace-window)). | **FROZEN:** Dunning touches quarantined in `PTP_FROZEN` state until Sept 6th. |
| **[`EDGE-07`](edge-cases.md#7-edge-07-post-failure-mandate-revocation)** | [Revoked Mandate Debit](edge-cases.md#7-edge-07-post-failure-mandate-revocation) | Customer cancelled mandate via bank portal ([RBI Mandate Rules](#rule-3-revoked-mandates-halted)). | **BLOCKED:** Permanent freeze (`STOP_MANDATE_REVOKED`); zero touches dispatched. |
| **[`EDGE-08`](edge-cases.md#8-edge-08-active-fraud-dispute--chargeback)** | [Active Fraud Dispute / Chargeback](edge-cases.md#8-edge-08-active-fraud-dispute--chargeback) | Customer filed fraud dispute with issuing bank ([CPA 2019](#rule-5-cpa-2019-dispute-lock)). | **BLOCKED:** Quarantined under CPA 2019 (`STOP_DISPUTE_FRAUD`); retries stopped. |
| **[`EDGE-09`](edge-cases.md#9-edge-09-msmed-45-day-statutory-clash)** | [B2B MSMED 45-Day Boundary](edge-cases.md#9-edge-09-msmed-45-day-statutory-clash) | Commercial invoice overdue approaching 45 days ([MSMED Act 2006](#rule-8-msmed-act-2006)). | **ESCALATED:** Standard dunning halted; escalated directly to finance operations. |
| **[`EDGE-10`](edge-cases.md#10-edge-10-unmapped-decline-with-risk-flag)** | [Raw Ambiguous Decline String](edge-cases.md#10-edge-10-unmapped-decline-with-risk-flag) | Bank returns unmapped unstructured string ([13-Bucket Taxonomy](root-cause-taxonomy.md)). | **DISAMBIGUATED:** Resolved via semantic engine without blocking merchant flow. |

---

## 💻 Enterprise FinTech SaaS Dashboard

The web application is built with a **Clean Light-Theme Enterprise FinTech SaaS Design System** inspired by Stripe, Linear, and Vercel:

1. **Multi-Page Dedicated Hash Routing (5 Core Views)**:
   * **Overview (`#overview`)**: Top KPIs, **Live Chaos Injection Sandbox**, and the **Interactive Merchant ROI Calculator** (GMV ₹1 Cr–₹100 Cr).
   * **Benchmark (`#benchmark`)**: **Interactive Retina/HiDPI cumulative recovery time-series chart** with crosshair hover tooltips, 14-day daily recovery curves, and statutory safeguard comparisons.
   * **Diagnostic Sandbox (`#playground`)**:
     - **Live Decline Triage & LLM Decision Agent**: Test arbitrary error text against the classifier and see live **AI Agent Reasoning**, model attribution, and EV justifications.
     - **NLU Promise-to-Pay (PTP) Extractor**: Extract conversational PTP dates, amounts, and freeze rules from English/Hinglish transcripts.
   * **Audit Explorer (`#transactions`)**: Fluid audit table with search, edge-case filters, **Decision Chain badges** (`[Bucket N] → [ACTION] → [OUTCOME]`), zero horizontal scroll, and SHA-256 block inspection drawer.
   * **Compliance Rules (`#rules`)**: Interactive codification of the 6 Indian statutory regulatory frameworks.
2. **Interactive Live Animated Simulation Runner & State Reset**:
   * Click **"Run Simulation"** to execute the live in-process FSM (`POST /api/simulate/live`) with real-time progressive state animations, live LLM agent reasoning badges, and instant metric recalculation. Click **"Reset Simulation"** to return to standby anytime.
3. **Dedicated REST API Endpoints**:
   * `POST /api/agent/decide` — Standalone AI Agent decision engine with EV justification and model cascade.
   * `POST /api/simulate/live` — In-process FSM execution with step-by-step state reporting.
   * `POST /api/diagnose/live` — Live diagnosis, compliance invariant validation, and action plan routing.
   * `GET /api/benchmark` — Complete 14-day time-series data and comparative benchmark metrics.
4. **One-Click Regulatory PDF Report Generation**:
   * Export the entire 750-transaction compliance audit trail or single-transaction records as formatted executive PDF reports directly from the UI header or via `scripts/generate_pdf_report.py`.

---

## 📂 Project Repository Structure

```
razorpay-ai-challenge/
├── app/                              # Enterprise FinTech SaaS Dashboard
│   ├── index.html                    # 5-View multi-page application layout
│   ├── styles.css                    # FinTech design system tokens (Light theme)
│   ├── app.js                        # Frontend controller, routing, & simulation runner
│   └── server.py                     # Dedicated API & dashboard HTTP server (Port 8888)
├── src/                              # Core Autonomous Agent Architecture
│   ├── agent/                        # AI Recovery Decision Agent & LLM Reasoning Engine
│   │   └── recovery_agent.py         # Multi-model cascade (Gemini 2.5 Flash, Llama 4, DeepSeek)
│   ├── config/                       # Codified regulatory rules & economic constants
│   │   └── regulatory_rules.py       # AFA caps, TRAI quiet hours, MSMED penal interest
│   ├── models/                       # Pydantic v2 domain schemas & computed fields
│   ├── classifiers/                  # Deterministic rule classifier & LLM cascade fallback
│   ├── router/                       # Dual-layer statutory compliance router & checkout drip
│   ├── orchestrator/                 # 9-state FSM & batch execution pipeline
│   ├── scheduler/                    # Simulated discrete-event clock scheduler
│   ├── audit/                        # SHA-256 hash-chained cryptographic audit logger
│   ├── benchmarks/                   # Naive baseline & comparative evaluator
│   └── generators/                   # Deterministic 750-transaction batch generator
├── tests/                            # Comprehensive Automated Test Suite (71 Tests)
│   ├── test_schema.py                # Schema validation & PII masking
│   ├── test_generator.py             # 13-bucket distribution checks
│   ├── test_classifier.py            # Rule & semantic fallback tests
│   ├── test_compliance_guards.py     # Statutory rule & stopping invariants
│   ├── test_state_machine.py         # 9-state FSM transitions
│   ├── test_scheduler.py             # Discrete-event calendar time tests
│   ├── test_audit_logger.py          # Cryptographic SHA-256 chain & EV tests
│   ├── test_edge_case_router.py      # 10 Programmatic refusal proofs
│   └── test_benchmarks.py            # Comparative benchmark runner tests
├── scripts/                          # Executable Demo & Benchmark Scripts
│   ├── run_single_recovery_demo.py   # Live single transaction simulation demo
│   ├── run_comparative_benchmark.py  # Full 750-transaction benchmark runner
│   ├── run_batch_simulation.py       # Full batch discrete-event simulation
│   ├── generate_pdf_report.py        # Executive PDF audit report generator
│   └── generate_dataset.py           # Batch dataset generator
├── data/                             # Generated Audit Trails & Benchmark JSON
│   ├── full_batch_audit_trail.json   # 2,548 SHA-256 hash-chained audit blocks
│   └── comparative_benchmark_results.json
├── compliance-rules.md               # Codified statutory compliance specification
├── root-cause-taxonomy.md            # 13-Bucket failure taxonomy specification
├── edge-cases.md                     # 10 Mission-critical edge cases specification
└── classifier-notes.md               # Triage precision & audit logs
```

---

## 🌟 Key Innovations & Architectural Strengths

1. **Three-Tier Resilient Classifier Cascade**: Tier 1 deterministic regex triage (<1ms) → Tier 2 OpenRouter LLM semantic disambiguation (Qwen / DeepSeek / Gemini) → Tier 3 Human Ops quarantine. Operates 100% self-contained offline with zero external API dependencies required.
2. **Cryptographic Tamper-Evidence**: Full **2,548-block SHA-256 chained audit ledger** linking back to genesis block `0000...0000` with automated tamper verification on every export.
3. **Statutory Refusal Invariants**: Programmatic guardrails guaranteeing 0 regulatory breaches across **RBI 2026 E-Mandate, TRAI quiet hours, CPA 2019 dispute freezes, DPDP Act 2023, and MSMED Act**.

---

## 🔒 Copyright & Contest Attribution

**Author:** Harmit Jetani  
**Submission:** Official Entry for Razorpay AI Challenge (Track 03: AI Revenue Recovery System)  

> ⚠️ **Plagiarism & Provenance Notice:** All commit histories, cryptographic SHA-256 genesis hashes, dataset generators, and state machine architectures in this repository are timestamped and digitally watermarked. Unauthorized copying, mirroring, or re-submission is strictly prohibited.