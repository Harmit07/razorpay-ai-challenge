# ⚡ Razorpay AI Challenge: Track 03 — AI Revenue Recovery
> **"Find revenue that’s slipping away and win it back"**

[![Test Suite](https://img.shields.io/badge/Unit%20Tests-68%20Passing%20(0.14s)-success.svg)](file:///Users/harmitjetani/Documents/GitHub/razorpay-ai-challenge/tests)
[![Regulatory Compliance](https://img.shields.io/badge/Compliance-100%25%20Invariant%20Safe-blue.svg)](file:///Users/harmitjetani/Documents/GitHub/razorpay-ai-challenge/compliance-rules.md)
[![Measured Recovery Lift](https://img.shields.io/badge/Measured%20Lift-%2B164.2%25%20vs%20Baseline-success.svg)](file:///Users/harmitjetani/Documents/GitHub/razorpay-ai-challenge/data/comparative_benchmark_results.json)
[![Dashboard](https://img.shields.io/badge/Dashboard-Live%20on%20Port%208888-orange.svg)](http://localhost:8888)

An autonomous, audit-grade **AI Revenue Recovery Agent** that detects revenue at risk across recurring payment failures, diagnoses root causes using Razorpay's 3-tier error model and semantic intent classification, routes actions through non-negotiable **RBI, TRAI, CPA 2019, and DPDP 2023 statutory invariants**, executes bounded multi-channel recovery workflows, and proves measured financial yield across a batch simulation with an immutable audit trail.

---

## ⚡ 5-Second Quickstart (For Judges & Reviewers)

```bash
# 1. Launch the Live Enterprise FinTech Dashboard
python3 app/server.py
# 👉 Open http://localhost:8888 in your browser

# 2. Run the Single Transaction End-to-End Lifecycle Demo
python3 scripts/run_single_recovery_demo.py

# 3. Run the Full 750-Transaction Batch Benchmark (14 Days Simulated in ~0.1s)
python3 scripts/run_comparative_benchmark.py

# 4. Run the Complete Automated Test Suite (68 Tests)
python3 -m unittest discover -s tests
```

---

## 📊 Executive Benchmark: Smart Agent vs. Naive Baseline

Evaluated across the exact same deterministic dataset of **750 payment failures** representing **₹2,27,71,364.25 (₹2.28 Crore)** in volume at risk over a simulated 14-day recovery window:

| Evaluation Metric | Standard 24h Fixed Retry (Baseline) | Smart AI Recovery Agent (Ours) | Measured Advantage / Impact |
| :--- | :--- | :--- | :--- |
| **Total Revenue Recovered** | **₹20,54,913.61** | **₹54,29,649.50** | **+₹33,74,735.89 (+164.2% Lift)** 🚀 |
| **Recovery Yield Rate** | **9.02%** | **23.84%** | **+14.82% Absolute Lift** |
| **Successful Recoveries** | 51 transactions | **198 transactions** | **+147 Additional Merchants/Users** |
| **Statutory Violations Committed** | **599 Violations** ⚠️ *(High Regulatory Fine Risk)* | **0 Violations** 🛡️ *(100% Invariant Safe)* | **100% Compliance Risk Elimination** |
| **RBI $\ge 24\text{h}$ Pre-Debit Alerts** | 0 sent (100% Non-Compliant) | **424 Dispatched Compliantly** | Full Statutory Pre-Debit Compliance |
| **AFA Limit Respect (>₹15k / >₹1L)** | 0 checked (Illegal debits attempted) | **114 Dynamic AFA Links Routed** | Zero Unauthorized Auto-Debits |
| **Revoked Mandates Halted** | 0 halted (Harassed cancelled users) | **32 Instantly Quarantined** | Zero Cancelled Mandate Debits |
| **TRAI Quiet Hours Suppressed** | 0 delayed (Violated night rules) | **42 DND / Quiet Numbers Held** | Zero TRAI UCC/DND Breaches |
| **Active Dispute / Fraud Freezes** | 0 frozen (Dunning continued on fraud) | **20 Immediate Freezes Enforced** | Full Consumer Protection Act (CPA 2019) Safety |
| **Promise-to-Pay (PTP) Honored** | 0 honored (Interrupted promise) | **33 Accounts Frozen in Grace Window** | Maximum Customer Trust & Goodwill |

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
    subgraph S2 ["2. Diagnostic Engine & Triage (Two-Stage)"]
        PARSE["Razorpay Error Model Parser<br/>(source / step / reason)"]
        STAGE1{"Deterministic Rule Classifier<br/>(Confidence >= 0.85)"}
        
        SOFT["Soft Liquidity Failure<br/>(insufficient_funds, bank_server_down)"]
        HARD["Hard Failure / Terminal<br/>(card_expired, mandate_revoked)"]
        
        LLM_PARSER["Semantic Intent Engine<br/>• Raw unmapped decline disambiguation<br/>• Promise-to-Pay (PTP) extraction<br/>• Fraud context isolation"]
        HUMAN_ESC["Human Ops Quarantine<br/>(Conf < 0.70 / High Risk Flag)"]
    end

    %% COMPLIANCE ROUTER
    subgraph S3 ["3. Programmatic Statutory Compliance Router (Hard Invariants)"]
        GUARD1{"Guard 1: CPA 2019 Dispute Quarantine<br/>(Is chargeback/fraud dispute active?)"}
        GUARD2{"Guard 2: Mandate Revocation Invariant<br/>(Is mandate cancelled/revoked by user?)"}
        GUARD3{"Guard 3: Zombie Retry Cap<br/>(Attempt count >= 3 or >14 days?)"}
        GUARD4{"Guard 4: RBI 2026 E-Mandate AFA Check<br/>(Amount > ₹15k standard or > ₹1L exempt?)"}
        GUARD5{"Guard 5: TRAI Quiet Hours & DND<br/>(Time in 08:00–20:00 IST?)"}
        
        HALT_QUARANTINE["HALT WORKFLOW & QUARANTINE<br/>(STOP_PAID, STOP_MANDATE_REVOKED, STOP_DISPUTE_FRAUD, STOP_MAX_RETRIES)"]
    end

    %% SCHEDULER & EXECUTION
    subgraph S4 ["4. Simulated Clock Scheduler & Multi-Channel Execution"]
        SCHED["Simulated Clock Priority Queue<br/>(Discrete-event simulation)"]
        
        ACT_NOTICE["Pre-Debit Notice Dispatch<br/>(WhatsApp DLT Service Implicit >= 24h)"]
        ACT_RETRY["Smart Salary-Cycle Auto-Debit<br/>(1st-5th / 25th-30th + 48h cooling)"]
        ACT_AFA["Dynamic AFA OTP Checkout Link<br/>(For recurring > ₹15k / > ₹1L)"]
        ACT_VOICE["Empathetic Hinglish Voice Bot<br/>(Promise-to-Pay negotiation)"]
    end

    %% AUDIT & SETTLEMENT
    subgraph S5 ["5. Immutable Audit Trail & Settlement"]
        AUDIT["Tamper-Evident Audit Trail<br/>(DPDP 2023 PII Masked, 2,548 Records)"]
        SETTLE["Outcome Settlement Webhook<br/>(payment.captured / invoice.paid)"]
        RECOVERED_STATE["Terminal State: RECOVERED 🚀<br/>(Instant queue purge + statutory receipt)"]
    end

    %% FLOW CONNECTIONS
    W1 --> PARSE
    W2 --> PARSE
    PARSE --> STAGE1
    STAGE1 -->|"High Conf Soft"| SOFT
    STAGE1 -->|"High Conf Hard"| HARD
    STAGE1 -->|"Ambiguous / Unmapped"| LLM_PARSER
    
    LLM_PARSER -->|"Resolved Intent"| SOFT
    LLM_PARSER -->|"Low Confidence"| HUMAN_ESC
    
    SOFT --> GUARD1
    HARD --> GUARD1
    HUMAN_ESC --> GUARD1
    
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
    ACT_VOICE --> AUDIT
    RECOVERED_STATE --> AUDIT
```

---

## 🔄 9-State Finite State Machine (FSM) Lifecycle

The recovery engine enforces all statutory waiting periods, cooling-off intervals, stopping rules, and escalation paths through a deterministic 9-state finite state machine:

```mermaid
stateDiagram-v2
    [*] --> DETECTED: Webhook / Telemetry Ingestion

    DETECTED --> DIAGNOSING: Ingest Payload & Classify Error
    
    DIAGNOSING --> ACTION_SCHEDULED: Soft Failure / AFA Link Scheduled
    DIAGNOSING --> HUMAN_REVIEW: Low Confidence < 0.70 / Risk Flag
    DIAGNOSING --> UNRECOVERABLE: Terminal Hard Stop (Revoked / Dispute / Opt-Out)

    HUMAN_REVIEW --> ACTION_SCHEDULED: Operator Approved
    HUMAN_REVIEW --> UNRECOVERABLE: Operator Rejected / Blocked

    ACTION_SCHEDULED --> RETRYING: 24h Notice Window & 48h Cooling Elapsed

    RETRYING --> RECOVERED: Payment Succeeded (STOP_PAID)
    RETRYING --> ACTION_SCHEDULED: Soft Failure Attempt #1 (Requeue + 48h Cooling)
    RETRYING --> RETRYING: Soft Failure Attempt #2 (Digital Nudge + Cooling)
    RETRYING --> ESCALATED: Soft Failure Attempt #3 (Debit Cap: Handoff to Voice Bot)
    RETRYING --> UNRECOVERABLE: Customer Opt-Out (STOP_OPT_OUT)

    ESCALATED --> PTP_FROZEN: Promise-to-Pay Date Locked (STOP_PTP_ACTIVE)
    ESCALATED --> RECOVERED: Paid via Call Link (STOP_PAID)
    ESCALATED --> UNRECOVERABLE: Outreach Exhausted / 14-Day Limit

    PTP_FROZEN --> RECOVERED: Paid During Grace Window (STOP_PAID)
    PTP_FROZEN --> RETRYING: Grace Window Expired Unpaid

    RECOVERED --> [*]
    UNRECOVERABLE --> [*]
```

---

## 🛡️ Programmatic Refusal Proofs (10 Edge Cases)

Every regulatory guardrail is verified by dedicated automated tests that assert the recovery router **strictly refuses** illegal operations and emits structured refusal audit records:

| Test ID | Edge Case Scenario | Statutory / Engineering Invariant | Verified Refusal Outcome |
| :--- | :--- | :--- | :--- |
| **`EDGE-01`** | Zombie Retry Cap | Max 3 auto-debits within 14-day window. | **BLOCKED:** Throws `ComplianceViolationError`; transitions to `UNRECOVERABLE`. |
| **`EDGE-02`** | ₹15,001 Standard AFA Cap | Direct auto-debit $> ₹15,000$ prohibited (RBI/DPSS/2026-27/396). | **BLOCKED:** Auto-debit refused; dynamic AFA OTP payment link dispatched. |
| **`EDGE-03`** | ₹1,00,001 Exemption Straddle | Mutual Funds / Insurance relaxed cap is ₹1,00,000. | **BLOCKED:** ₹1,00,001 auto-debit refused; converted to dynamic AFA OTP checkout link. |
| **`EDGE-04`** | Mandate Expiring in 24h | Mandate expires before cooling + retry window. | **BLOCKED:** Refuses auto-debit; dispatches instrument renewal link. |
| **`EDGE-05`** | TRAI Quiet Hours Violation | Outbound customer touch at 11:30 PM IST. | **BLOCKED:** Instant send blocked; queued for release at 08:30 AM IST next morning. |
| **`EDGE-06`** | Promise-to-Pay (PTP) Grace Window | Customer committed to pay on Sept 5th. | **FROZEN:** Dunning touches quarantined in `PTP_FROZEN` state until Sept 6th. |
| **`EDGE-07`** | Revoked Mandate Debit | Customer cancelled mandate via bank portal. | **BLOCKED:** Permanent freeze (`STOP_MANDATE_REVOKED`); zero touches dispatched. |
| **`EDGE-08`** | Active Fraud Dispute / Chargeback | Customer filed fraud dispute with issuing bank. | **BLOCKED:** Quarantined under CPA 2019 (`STOP_DISPUTE_FRAUD`); retries stopped. |
| **`EDGE-09`** | B2B MSMED 45-Day Boundary | Commercial invoice overdue approaching 45 days. | **ESCALATED:** Standard dunning halted; escalated directly to finance operations. |
| **`EDGE-10`** | Raw Ambiguous Decline String | Bank returns unmapped unstructured string. | **DISAMBIGUATED:** Resolved via semantic engine without blocking merchant flow. |

---

## 💻 Enterprise FinTech SaaS Dashboard (`http://localhost:8888`)

The web application is built as a **Light-Theme FinTech Dashboard** inspired by Stripe, Linear, and Vercel:

1. **Multi-Page Dedicated Views & URLs**:
   * **[Overview (`#overview`)](http://localhost:8888/#overview)**: Top-level KPIs, 3-step pipeline overview, and the **Interactive Merchant ROI Calculator**.
   * **[Benchmark (`#benchmark`)](http://localhost:8888/#benchmark)**: Comparative bar charts, 14-day metric tables, and safeguard breakdowns.
   * **[Audit Explorer (`#transactions`)](http://localhost:8888/#transactions)**: 6-column fluid table with instant search, test-case filters, and zero horizontal scroll.
   * **[Compliance Rules (`#rules`)](http://localhost:8888/#rules)**: The 6 programmatic statutory regulatory frameworks.
2. **Interactive Live Simulation Runner**:
   * Click **"Run Demo"** to watch the state machine ingest, diagnose, fast-forward virtual time, negotiate a Hinglish voice PTP, and compliantly settle ₹4,999.00 in real time.
3. **Draggable & Collapsible Sidebar**:
   * Drag the right border to customize sidebar width from `200px` to `420px`, or click `◀` to collapse into icon-only mode.
4. **Interactive Merchant ROI & Revenue Calculator**:
   * Slide your merchant GMV and failure rate to calculate projected annual revenue recovery and regulatory violations avoided.

---

## 📂 Project Repository Structure

```
razorpay-ai-challenge/
├── app/                              # Enterprise FinTech SaaS Dashboard
│   ├── index.html                    # 4-View multi-page application layout
│   ├── styles.css                    # FinTech design system tokens (Light theme)
│   ├── app.js                        # Frontend controller & view routing
│   ├── server.py                     # Dedicated API & dashboard HTTP server (Port 8888)
│   └── dashboard.py                  # Optional Streamlit dashboard
├── src/                              # Core Agent Architecture
│   ├── models/                       # Pydantic v2 domain schemas & computed fields
│   ├── classifiers/                  # Rule classifier & semantic intent LLM fallback
│   ├── router/                       # Dual-layer statutory compliance router
│   ├── orchestrator/                 # 9-state FSM & batch execution pipeline
│   ├── scheduler/                    # Simulated discrete-event clock scheduler
│   ├── audit/                        # Tamper-evident DPDP 2023 audit logger
│   ├── benchmarks/                   # Naive baseline & comparative evaluator
│   └── generators/                   # Deterministic 750-transaction batch generator
├── tests/                            # Comprehensive Automated Test Suite (68 Tests)
│   ├── test_schema.py                # Schema validation & PII masking
│   ├── test_generator.py             # 13-bucket distribution checks
│   ├── test_classifier.py            # Rule & semantic fallback tests
│   ├── test_compliance_router.py     # Statutory rule & stopping invariants
│   ├── test_state_machine.py         # 9-state FSM transitions
│   ├── test_simulated_clock.py       # Discrete-event calendar time tests
│   ├── test_audit_logger.py          # Tamper-evident audit trail tests
│   ├── test_edge_case_router.py      # 10 Programmatic refusal proofs
│   └── test_benchmark.py             # Comparative benchmark runner tests
├── scripts/                          # Executable Demo & Benchmark Scripts
│   ├── run_single_recovery_demo.py   # Live single transaction simulation demo
│   ├── run_comparative_benchmark.py  # Full 750-transaction benchmark runner
│   └── generate_dataset.py           # Batch dataset generator
├── data/                             # Generated Audit Trails & Benchmark JSON
├── compliance-rules.md               # Codified statutory compliance specification
├── root-cause-taxonomy.md            # 13-Bucket failure taxonomy specification
├── edge-cases.md                     # 10 Mission-critical edge cases specification
└── classifier-notes.md               # Triage precision & audit logs
```

---

## 🏆 Summary

This project delivers on Track 03 by combining:
1. **Measured Rupee Recovery** (+₹33.75 Lakhs / +164.2% lift on ₹2.28 Crore).
2. **Zero Compliance Breaches** (100% RBI, TRAI, CPA 2019, DPDP 2023 invariant-safe).
3. **Hard Invariant Refusal Proofs** (10 deliberate edge cases with automated tests).
4. **Production-Grade FinTech UI** (Stripe/Linear-grade light theme with discrete URLs).