# 📜 Audit Trail for Recovered Transaction sub_live_recov_9824
**Total Transition Events Recorded:** 7
**Generated At:** 2026-08-27T12:10:02.671491+00:00

| Audit ID | Timestamp (UTC) | Txn ID | Transition | Statutory Rule | Internal Policy | AFA Status | Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| `aud_e98424` | 2026-08-27T10:00:00 | `sub_live_recov_9824` | `DETECTED` ➔ `DIAGNOSING` | `NONE` | `TRIAGE_INGESTION_GATE` | `NOT_REQUIRED` | Payment failure ingested: insufficient_funds. Routing to diagnostic engine. |
| `aud_a05224` | 2026-08-27T10:00:00 | `sub_live_recov_9824` | `DIAGNOSING` ➔ `ACTION_SCHEDULED` | `RBI_2026_PRE_DEBIT_24H_NOTICE_REQUIRED` | `48H_COOLING_INTERVAL_SALARY_CYCLE_SNAP` | `NOT_REQUIRED` | Soft Liquidity Retry #1: Mandated >=24h Pre-Debit Alert queued for 2026-08-27T10:00:00+00:00; auto-debit scheduled for 2026-08-29T10:00:00+00:00 (Salary Snap: False). |
| `aud_70fe87` | 2026-08-27T10:00:00 | `sub_live_recov_9824` | `ACTION_SCHEDULED` ➔ `ACTION_SCHEDULED` | `RBI_2026_PRE_DEBIT_24H_NOTICE_REQUIRED` | `INTERNAL_SAFE_HOURS_08_TO_20_IST` | `NOT_REQUIRED` | Dispatched statutory >=24h pre-debit alert prior to retry. Opt-out link included. |
| `aud_dcff22` | 2026-08-29T10:00:00 | `sub_live_recov_9824` | `ACTION_SCHEDULED` ➔ `RETRYING` | `RBI_2026_PRE_DEBIT_24H_NOTICE_REQUIRED` | `48H_COOLING_INTERVAL_SALARY_CYCLE_SNAP` | `NOT_REQUIRED` | Statutory notice window satisfied. Executed automated recurring debit attempt #1. |
| `aud_4a81f0` | 2026-08-29T10:00:00 | `sub_live_recov_9824` | `RETRYING` ➔ `ESCALATED` | `NONE` | `RESPECTFUL_HINGLISH_VOICE_DUNNING` | `NOT_REQUIRED` | Empathetic voice recovery bot engaged. Customer committed to Promise-to-Pay (PTP). |
| `aud_3458cf` | 2026-08-29T10:00:00 | `sub_live_recov_9824` | `ESCALATED` ➔ `PTP_FROZEN` | `NONE` | `PTP_FREEZE_GRACE_WINDOW` | `NOT_REQUIRED` | Promise-to-Pay locked for 2026-09-05. All dunning touches frozen until 2026-09-06. |
| `aud_6ef3c1` | 2026-09-05T11:30:00 | `sub_live_recov_9824` | `PTP_FROZEN` ➔ `RECOVERED` | `RBI_POST_DEBIT_GRIEVANCE_RECEIPT` | `INSTANT_QUEUE_PURGE_ON_SETTLEMENT` | `NOT_REQUIRED` | Payment captured in full on PTP promise date. Dispatched confirmation receipt with grievance redressal officer details. |
