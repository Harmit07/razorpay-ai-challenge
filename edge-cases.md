# 🚨 Production Edge Cases & Graceful Failure Specification

This document catalogues **10 mission-critical production edge cases** deliberately injected into the AI Revenue Recovery Agent dataset. These edge cases test the system's boundary conditions, stopping rules, statutory compliance invariants, and graceful failure handling.

---

## 📋 Edge Case Summary Matrix

| ID | Edge Case Name | Primary Risk | Applicable Statutory Rule / Policy | Graceful Recovery Protocol |
| :--- | :--- | :--- | :--- | :--- |
| **`EDGE-01`** | **The Zombie Retry Trap** | Chronic customer failure (3+ past attempts failed). | Internal Policy: Max 3 Attempts (`STOP_MAX_RETRIES`). | Immediately halt automated auto-debit; pause subscription gracefully; route case to human operations. |
| **`EDGE-02`** | **The ₹15,000 AFA Straddle** | Amount is ₹15,001.00 (exceeds cap by ₹1). | RBI 2026 E-Mandate Framework (`RBI/DPSS/2026-27/396`). | Prohibit direct auto-debit; generate and dispatch dynamic 1-click AFA OTP checkout link. |
| **`EDGE-03`** | **The ₹1,00,000 Exemption Straddle** | Mutual Fund SIP of ₹1,00,001.00 (exceeds relaxed cap). | RBI E-Mandate Amendment (`RBI/2023-24/90`). | Exemption cap breached; bypass direct debit; require explicit AFA OTP validation. |
| **`EDGE-04`** | **Mandate Expiring Mid-Retry** | Mandate valid at failure time, but expires in +12 hours. | RBI E-Mandate Framework: Mandate Validity Boundary. | Scheduler detects impending expiration before 24h pre-debit window; transitions to instrument update link (`STOP_MANDATE_EXPIRED`). |
| **`EDGE-05`** | **TRAI Quiet Hours Sleep Trap** | Failure occurs at 23:45 IST (11:45 PM). | TRAI UCC Regulations: 08:00–20:00 IST contact window. | Ingest event; buffer in Delayed Dispatch Queue; release pre-debit notice at 08:05 AM IST next morning. |
| **`EDGE-06`** | **Promise-to-Pay (PTP) Race Condition** | Cron scheduler wakes up while customer has active PTP. | Internal Policy: PTP Freeze Rule (`STOP_PTP_ACTIVE`). | Freeze all automated auto-debits and outreach until Customer Promised Date $+ 24\text{ hours}$. |
| **`EDGE-07`** | **Post-Failure Mandate Revocation** | Customer cancels UPI AutoPay mandate after failure. | Statutory: Customer Right to Revoke Mandate at any time. | Catch `mandate_cancelled_by_user`; immediately trigger `STOP_MANDATE_REVOKED`; purge retry queues. |
| **`EDGE-08`** | **Active Fraud Dispute / Chargeback** | Open chargeback dispute on transaction. | CCPA 2023 Anti-Harassment & RBI Grievance Guidelines. | Instantly halt all dunning (`STOP_DISPUTE_FRAUD`); freeze automated touches; log for fraud ops audit. |
| **`EDGE-09`** | **MSMED 45-Day Statutory Clash** | B2B invoice from MSE supplier on Day 43. | MSMED Act 2006 (Sections 15 & 16): 45-day statutory limit. | Clamp standard 14-day dunning window to 48 hours; escalate to corporate finance before statutory deadline. |
| **`EDGE-10`** | **Unmapped Decline with Risk Flag** | Raw decline string `"U30-SWITCH_UNAVAILABLE"` + `risk_flag=True`. | Diagnostic Guardrail: Confidence $< 0.70$ / Risk Flag. | Bypass automated retry engine; route case directly to `HUMAN_ESC` with full context for manual audit. |

---

## 🔍 Detailed Edge Case Specifications

### 1. `EDGE-01`: The Zombie Retry Trap (Customer Failing 5x in a Row)
* **Tag:** `EDGE_01_ZOMBIE_RETRY_5X`
* **Scenario:** Customer has suffered consecutive debit failures across multiple cycles. The current dunning lifecycle already contains 3 recorded failures in `attempt_history`.
* **The Naive Hazard:** Dumb cron retry engines trigger endless daily auto-debits, causing repetitive customer bank bounce penalty fees (₹250–₹500/bounce) and triggering customer chargeback disputes.
* **Graceful Failure Protocol:**
  ```python
  if event.current_attempt_count >= 3:
      # Deterministic Stop Invariant
      trigger_stopping_rule("STOP_MAX_RETRIES")
      subscription.pause(status="DUNNING_EXHAUSTED")
      route_to_human_ops(event)
  ```

---

### 2. `EDGE-02`: The ₹15,000 AFA Straddle (₹15,001.00 Standard Subscription)
* **Tag:** `EDGE_02_AFA_15K_STRADDLE`
* **Scenario:** A SaaS or utility subscription charges ₹15,001.00.
* **The Naive Hazard:** Naive payment schedulers fire direct auto-debits on all subscriptions regardless of amount. Debiting ₹15,001 without AFA is an immediate RBI compliance violation (`RBI/DPSS/2026-27/396`).
* **Graceful Failure Protocol:**
  ```python
  if event.amount > event.statutory_afa_cap:  # 15001.00 > 15000.00
      # Direct auto-debit strictly prohibited
      afa_link = generate_dynamic_afa_payment_link(event.txn_id, event.amount)
      dispatch_customer_intervention(channel="WHATSAPP_AFA_LINK", link=afa_link)
  ```

---

### 3. `EDGE-03`: The ₹1,00,000 Exemption Straddle (₹1,00,001.00 Mutual Fund SIP)
* **Tag:** `EDGE_03_AFA_1L_STRADDLE`
* **Scenario:** Mutual Fund (SIP) or Insurance Premium transaction of ₹1,00,001.00.
* **The Naive Hazard:** Treating all exempt categories as unconditionally exempt without evaluating the ₹1,00,000 ceiling under `RBI/2023-24/90`.
* **Graceful Failure Protocol:**
  ```python
  # Category is MUTUAL_FUND -> Cap is 100,000.00
  if event.amount > 100000.00:  # 100001.00 > 100000.00
      afa_required = True
      dispatch_customer_intervention(channel="SMS_AFA_LINK")
  ```

---

### 4. `EDGE-04`: Mandate Expiring Mid-Retry Cycle
* **Tag:** `EDGE_04_MANDATE_EXPIRING_MID_RETRY`
* **Scenario:** Mandate is active at failure time ($T_0$), but expires in $+12\text{ hours}$. Statutory pre-debit notice requires $\ge 24\text{ hours}$, and cooling requires $\ge 48\text{ hours}$. When the scheduler is ready to execute, the mandate has expired.
* **The Naive Hazard:** Firing auto-debit against an expired mandate results in gateway error `mandate_validity_expired`, merchant fee penalties, and failed debit counts.
* **Graceful Failure Protocol:**
  ```python
  if event.mandate_valid_until and scheduled_debit_time > event.mandate_valid_until:
      trigger_stopping_rule("STOP_MANDATE_EXPIRED")
      dispatch_mandate_update_link(event)
  ```

---

### 5. `EDGE-05`: TRAI Quiet Hours Sleep Trap (Failure at 23:45 IST)
* **Tag:** `EDGE_05_TRAI_QUIET_HOURS_SLEEP`
* **Scenario:** Bank server fails at 11:45 PM IST (18:15 UTC).
* **The Naive Hazard:** Firing instant automated SMS/WhatsApp alerts or voice calls wakes up customers at midnight, violating TRAI DND regulations and generating customer churn.
* **Graceful Failure Protocol:**
  ```python
  current_hour_ist = (event.timestamp + timedelta(hours=5, minutes=30)).hour
  if current_hour_ist < 8 or current_hour_ist >= 20:
      delayed_queue.enqueue(event, release_at="08:05_AM_IST")
  ```

---

### 6. `EDGE-06`: Active Promise-to-Pay (PTP) Race Condition
* **Tag:** `EDGE_06_PTP_RACE_CONDITION`
* **Scenario:** Customer answered a voice recovery call and promised to pay on the 5th of the month. On the 3rd, an automated retry cron triggers.
* **The Naive Hazard:** Retrying debit while customer has an active PTP breaks customer trust, double-debits accounts, and breaches conversational commitments.
* **Graceful Failure Protocol:**
  ```python
  if event.ptp_record and event.ptp_record.status == "ACTIVE":
      if current_time < event.ptp_record.grace_until:
          trigger_stopping_rule("STOP_PTP_ACTIVE")
          freeze_all_dunning_outreach()
  ```

---

### 7. `EDGE-07`: Post-Failure Mandate Revocation by User
* **Tag:** `EDGE_07_MANDATE_REVOKED_POST_FAILURE`
* **Scenario:** Customer enters bank/UPI app and clicks "Revoke Mandate" after initial failure.
* **The Naive Hazard:** Subsequent retry attempt triggers bank bounce fees and customer harassment grievances.
* **Graceful Failure Protocol:**
  ```python
  if event.error_reason == "mandate_cancelled_by_user":
      trigger_stopping_rule("STOP_MANDATE_REVOKED")
      purge_retry_queue(event.txn_id)
      pause_subscription_gracefully()
  ```

---

### 8. `EDGE-08`: Fraud Chargeback / Active Dispute Straddle
* **Tag:** `EDGE_08_FRAUD_DISPUTE_STRADDLE`
* **Scenario:** Card issuer flags transaction for potential fraud/chargeback dispute (`dispute_active=True`, `risk_flag=True`).
* **The Naive Hazard:** Pursuing dunning on a disputed charge violates CCPA anti-harassment laws and risks payment gateway account suspension.
* **Graceful Failure Protocol:**
  ```python
  if event.dispute_active or event.risk_flag:
      trigger_stopping_rule("STOP_DISPUTE_FRAUD")
      halt_all_outreach()
      escalate_to_risk_operations()
  ```

---

### 9. `EDGE-09`: MSMED 45-Day Statutory Ceiling Clash (B2B Invoice on Day 43)
* **Tag:** `EDGE_09_MSMED_45_DAY_CLASH`
* **Scenario:** Commercial tax invoice from a registered Micro & Small Enterprise (MSE) supplier is on Day 43 of payment cycle.
* **The Naive Hazard:** Applying standard 14-day dunning would push payment to Day 57, violating Sections 15 & 16 of the MSMED Act 2006 (mandatory compound interest penalty at $3\times$ RBI bank rate).
* **Graceful Failure Protocol:**
  ```python
  if invoice.supplier_registered_msme and invoice.age_days >= 43:
      max_allowed_dunning_hours = (45 - invoice.age_days) * 24  # Clamped to 48 hours
      schedule_emergency_finance_escalation(deadline_hours=max_allowed_dunning_hours)
  ```

---

### 10. `EDGE-10`: Unmapped Decline with High Risk Flag
* **Tag:** `EDGE_10_AMBIGUOUS_HIGH_RISK`
* **Scenario:** Gateway returns messy unknown text `"U30-SWITCH_UNAVAILABLE_CODE_987"` with an active `risk_flag=True`.
* **The Naive Hazard:** Guessing or silently discarding unknown bank decline strings risks taking inappropriate automated action or losing high-value revenue.
* **Graceful Failure Protocol:**
  ```python
  if diagnostic_confidence < 0.70 or event.risk_flag:
      route_to_human_escalation_queue(
          case=event,
          reason="LOW_CONFIDENCE_UNMAPPED_RISK_FLAG",
          audit_context=event.raw_error_description
      )
  ```

---

## 🎯 Verification & Benchmark Testing
All 10 edge cases are programmatically verifiable via:
```bash
# Run unit tests verifying edge case injection and attributes
python3 -m unittest tests/test_generator.py

# Generate full batch with injected edge cases
python3 scripts/generate_dataset.py 750
```
