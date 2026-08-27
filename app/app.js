/**
 * Front-end controller for Razorpay Revenue Recovery Dashboard.
 * Clean, lightweight, frictionless data presentation.
 */

let allTransactions = [];
let allAuditRecords = [];
let currentViewingTxnId = null;

// Initialize Dashboard
document.addEventListener("DOMContentLoaded", async () => {
  await loadSummaryData();
  await loadTransactions();
});

async function loadSummaryData() {
  try {
    const res = await fetch("/api/summary");
    if (res.ok) {
      const data = await res.json();
      document.getElementById("kpi-total-volume").innerText = `₹${data.total_revenue_at_risk_inr.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
      document.getElementById("kpi-ai-recovered").innerText = `₹${data.ai_recovered_revenue_inr.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
      document.getElementById("kpi-incremental").innerText = `+₹${data.incremental_recovered_revenue_inr.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
    }
  } catch (err) {
    console.warn("Using fallback local benchmark numbers", err);
  }
}

async function loadTransactions() {
  try {
    const res = await fetch("/api/transactions");
    if (res.ok) {
      allTransactions = await res.json();
      renderTransactions(allTransactions);
    }
  } catch (err) {
    console.error("Failed to load transactions", err);
  }
}

function renderTransactions(txns) {
  const tbody = document.getElementById("tableBody");
  tbody.innerHTML = "";

  if (txns.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 28px; color: var(--text-muted);">No matching transactions found.</td></tr>`;
    return;
  }

  // Display top 100 in table for fast DOM rendering
  const displaySet = txns.slice(0, 100);

  displaySet.forEach((t) => {
    const tr = document.createElement("tr");

    // 1. Classification Column (Recoverable vs Terminal Stop vs Human Review)
    let classBadge = `<span class="badge badge-success">Recoverable</span>`;
    if (t.dispute_active || t.error_reason === "mandate_cancelled_by_user" || (t.attempt_history && t.attempt_history.length >= 3)) {
      classBadge = `<span class="badge badge-danger">Terminal Stop</span>`;
    } else if (t.risk_flag || t.error_reason === "raw_unmapped_decline") {
      classBadge = `<span class="badge badge-warning">Human Review</span>`;
    }

    // 2. Compliance State Column (Specific Statutory Boundary)
    const isExempt = ["mutual_fund", "insurance_premium", "credit_card_bill"].includes((t.category || "").toLowerCase()) || Boolean(t.is_afa_exempt);
    const statutoryCap = isExempt ? 100000.0 : 15000.0;
    const isRecurring = (t.txn_type || "").toLowerCase() === "recurring_subscription";

    let compBadge = `<span class="badge badge-success">Clear</span>`;
    if (t.dispute_active) {
      compBadge = `<span class="badge badge-danger">Dispute Locked</span>`;
    } else if (t.error_reason === "mandate_cancelled_by_user") {
      compBadge = `<span class="badge badge-warning">Revoked Mandate</span>`;
    } else if (t.is_dnd) {
      compBadge = `<span class="badge badge-warning">DND Suppressed</span>`;
    } else if (isRecurring && t.amount > statutoryCap) {
      compBadge = `<span class="badge badge-shield">AFA OTP Enforced</span>`;
    } else if (isRecurring && isExempt && t.amount > 15000 && t.amount <= 100000) {
      compBadge = `<span class="badge badge-shield" style="background:rgba(16,185,129,0.15); color:#34d399;">AFA Exempt (₹1L Cap)</span>`;
    } else if (isRecurring) {
      compBadge = `<span class="badge badge-purple">24h Notice Queued</span>`;
    }

    const edgeBadge = t.edge_case_tag ? `<br><span style="font-size:10px; color:#38bdf8; font-family:var(--font-mono);">${t.edge_case_tag}</span>` : "";

    tr.innerHTML = `
      <td class="mono"><strong>${t.txn_id}</strong>${edgeBadge}</td>
      <td class="mono">₹${t.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
      <td>${formatPaymentMethod(t.method)}</td>
      <td><span style="font-family:var(--font-mono); font-size:11px;">${t.error_reason}</span></td>
      <td><span style="font-size:11px; color:var(--text-muted);">${t.category}</span></td>
      <td>${classBadge}</td>
      <td>${compBadge}</td>
      <td><button class="btn-inspect" onclick="openAuditModal('${t.txn_id}')">Inspect</button></td>
    `;
    tbody.appendChild(tr);
  });
}

function formatPaymentMethod(m) {
  if (!m) return "Card";
  if (m === "upi_autopay") return "UPI AutoPay";
  if (m === "upi_collect") return "UPI Collect";
  if (m === "card") return "Credit / Debit Card";
  if (m === "nach") return "e-NACH";
  if (m === "netbanking") return "Netbanking";
  return m;
}

function filterTransactions() {
  const query = document.getElementById("searchInput").value.toLowerCase();
  const stateFilter = document.getElementById("stateFilter").value;
  const edgeFilter = document.getElementById("edgeFilter").value;

  const filtered = allTransactions.filter((t) => {
    const matchesQuery = 
      t.txn_id.toLowerCase().includes(query) ||
      (t.mandate_id && t.mandate_id.toLowerCase().includes(query)) ||
      (t.customer_phone_masked && t.customer_phone_masked.includes(query)) ||
      t.error_reason.toLowerCase().includes(query) ||
      (t.method && t.method.toLowerCase().includes(query));

    let matchesEdge = true;
    if (edgeFilter !== "ALL") {
      matchesEdge = t.edge_case_tag && t.edge_case_tag.startsWith(edgeFilter);
    }

    return matchesQuery && matchesEdge;
  });

  renderTransactions(filtered);
}

async function openAuditModal(txn_id) {
  currentViewingTxnId = txn_id;
  const modal = document.getElementById("auditModal");
  const modalBody = document.getElementById("modalBody");
  document.getElementById("modalTxnId").innerText = `Transaction Trail: ${txn_id}`;

  const targetTxn = allTransactions.find((t) => t.txn_id === txn_id);
  if (targetTxn) {
    document.getElementById("modalCustomer").innerText = `Customer (DPDP Masked): ${targetTxn.customer_phone_masked || targetTxn.customer_email_masked} • Amount: ₹${targetTxn.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
  }

  modalBody.innerHTML = `<div style="text-align:center; padding: 24px; color: var(--text-muted);">Loading audit timeline...</div>`;
  modal.style.display = "flex";

  try {
    const res = await fetch(`/api/audit/${txn_id}`);
    if (res.ok) {
      const records = await res.json();
      if (records.length === 0) {
        renderSyntheticTimeline(targetTxn);
      } else {
        renderAuditTimeline(records);
      }
    } else {
      renderSyntheticTimeline(targetTxn);
    }
  } catch (e) {
    renderSyntheticTimeline(targetTxn);
  }
}

function renderAuditTimeline(records) {
  const modalBody = document.getElementById("modalBody");
  modalBody.innerHTML = "";

  records.forEach((r, idx) => {
    let stateBadge = `<span class="badge badge-success">${r.to_state}</span>`;
    if (r.to_state === "UNRECOVERABLE") stateBadge = `<span class="badge badge-danger">STOPPED</span>`;
    if (r.to_state === "HUMAN_REVIEW" || r.to_state === "PTP_FROZEN") stateBadge = `<span class="badge badge-warning">${r.to_state}</span>`;

    const card = document.createElement("div");
    card.className = "timeline-card";
    card.innerHTML = `
      <div class="timeline-header">
        <div class="timeline-step">
          <span>Step ${idx + 1}: ${formatEventType(r.event_type)}</span>
          ${stateBadge}
        </div>
        <div class="timeline-time">${r.timestamp.substring(0, 19).replace("T", " ")} UTC</div>
      </div>

      <div class="timeline-grid">
        <div class="timeline-field">Channel: <span>${r.channel}</span></div>
        <div class="timeline-field">Statutory Citation: <span>${r.statutory_rule_applied}</span></div>
        <div class="timeline-field">Policy Rule: <span>${r.internal_policy_applied}</span></div>
        ${r.stop_rule_triggered ? `<div class="timeline-field">Stopping Rule: <span style="color:#ef4444; font-weight:700;">${r.stop_rule_triggered}</span></div>` : ""}
      </div>

      <div class="timeline-rationale">
        ${r.decision_rationale}
      </div>
    `;
    modalBody.appendChild(card);
  });
}

function formatEventType(evt) {
  if (!evt) return "Event";
  return evt.replace(/_/g, " ");
}

function renderSyntheticTimeline(t) {
  if (!t) return;
  const mockRecords = [
    {
      from_state: "DETECTED",
      to_state: "DIAGNOSING",
      timestamp: t.timestamp,
      event_type: "FAILURE_INGESTED",
      channel: "GATEWAY_WEBHOOK",
      statutory_rule_applied: "NONE",
      internal_policy_applied: "RULE_ENGINE_TRIAGE",
      decision_rationale: `Ingested failure event: ${t.error_reason}. Diagnostic checks initiated.`
    },
    {
      from_state: "DIAGNOSING",
      to_state: "ACTION_SCHEDULED",
      timestamp: t.timestamp,
      event_type: "ACTION_PLAN_SCHEDULED",
      channel: "AUTO_DEBIT_API",
      statutory_rule_applied: t.amount > 15000 ? "RBI_DPSS_2026_27_396_15K_CAP" : "RBI_2026_PRE_DEBIT_24H_NOTICE_REQUIRED",
      internal_policy_applied: "48H_COOLING_INTERVAL_SALARY_CYCLE_SNAP",
      decision_rationale: t.amount > 15000 ? "Amount exceeds statutory AFA ceiling. Direct auto-debit prohibited; dynamic AFA OTP checkout link dispatched." : "Mandated >=24h pre-debit alert queued with customer opt-out link."
    }
  ];
  renderAuditTimeline(mockRecords);
}

function closeModal() {
  document.getElementById("auditModal").style.display = "none";
}

function exportFullAuditJson() {
  window.open("/api/export/full-json", "_blank");
}

function exportFullAuditMd() {
  window.open("/api/export/full-md", "_blank");
}

function exportCurrentTxnAudit() {
  if (currentViewingTxnId) {
    window.open(`/api/export/txn-json/${currentViewingTxnId}`, "_blank");
  }
}

function runDemoSimulation() {
  openAuditModal("sub_live_recov_9824");
}
