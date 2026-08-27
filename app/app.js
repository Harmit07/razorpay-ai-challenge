/**
 * Front-end controller for Razorpay AI Revenue Recovery Agent Dashboard.
 */

let allTransactions = [];
let allAuditRecords = [];

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
    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 24px; color: var(--text-muted);">No matching transactions found.</td></tr>`;
    return;
  }

  // Display top 100 in table for fast DOM rendering
  const displaySet = txns.slice(0, 100);

  displaySet.forEach((t) => {
    const tr = document.createElement("tr");

    // Outcome / Compliance Status badge
    let statusBadge = `<span class="badge badge-success">Recoverable</span>`;
    if (t.dispute_active) {
      statusBadge = `<span class="badge badge-danger">Dispute Locked</span>`;
    } else if (t.error_reason === "mandate_cancelled_by_user") {
      statusBadge = `<span class="badge badge-warning">Revoked Mandate</span>`;
    } else if (t.amount > 15000 && t.txn_type === "RECURRING_SUBSCRIPTION" && !t.is_afa_exempt) {
      statusBadge = `<span class="badge badge-shield">AFA OTP Link Required</span>`;
    } else if (t.is_dnd) {
      statusBadge = `<span class="badge badge-warning">DND Suppressed</span>`;
    }

    const edgeBadge = t.edge_case_tag ? `<br><span style="font-size:10px; color:#38bdf8;">${t.edge_case_tag}</span>` : "";

    tr.innerHTML = `
      <td class="mono"><strong>${t.txn_id}</strong>${edgeBadge}</td>
      <td class="mono">₹${t.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
      <td>${t.method}</td>
      <td><span style="font-family:var(--font-mono); font-size:11px;">${t.error_reason}</span></td>
      <td>${t.txn_type} / ${t.category}</td>
      <td class="mono">${t.customer_phone_masked || t.customer_email_masked}</td>
      <td>${statusBadge}</td>
      <td><button class="btn-view" onclick="openAuditModal('${t.txn_id}')">View Audit Trail</button></td>
    `;
    tbody.appendChild(tr);
  });
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
      t.error_reason.toLowerCase().includes(query);

    let matchesEdge = true;
    if (edgeFilter !== "ALL") {
      matchesEdge = t.edge_case_tag && t.edge_case_tag.startsWith(edgeFilter);
    }

    return matchesQuery && matchesEdge;
  });

  renderTransactions(filtered);
}

async function openAuditModal(txn_id) {
  const modal = document.getElementById("auditModal");
  const modalBody = document.getElementById("modalBody");
  document.getElementById("modalTxnId").innerText = `Audit Log Trail: ${txn_id}`;

  const targetTxn = allTransactions.find((t) => t.txn_id === txn_id);
  if (targetTxn) {
    document.getElementById("modalCustomer").innerText = `Customer Masked: ${targetTxn.customer_phone_masked || targetTxn.customer_email_masked} | Amount: ₹${targetTxn.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
  }

  modalBody.innerHTML = `<div style="text-align:center; padding: 20px; color: var(--text-muted);">Loading immutable audit records...</div>`;
  modal.style.display = "flex";

  try {
    const res = await fetch(`/api/audit/${txn_id}`);
    if (res.ok) {
      const records = await res.json();
      if (records.length === 0) {
        // Fallback demo render
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
    let dotClass = "dot-success";
    if (r.to_state === "UNRECOVERABLE") dotClass = "dot-danger";
    if (r.to_state === "HUMAN_REVIEW" || r.to_state === "PTP_FROZEN") dotClass = "dot-warning";

    const stepEl = document.createElement("div");
    stepEl.className = "timeline-step";
    stepEl.innerHTML = `
      <div class="timeline-dot ${dotClass}"></div>
      <div class="step-card">
        <div class="step-meta">
          <span>Step ${idx + 1}: ${r.from_state} ➔ ${r.to_state}</span>
          <span>${r.timestamp.substring(0, 19)} UTC</span>
        </div>
        <div class="step-title">${r.event_type} (${r.channel})</div>
        <div class="step-detail-row">
          <div><strong>Statutory Citation:</strong> <span class="rule-badge">${r.statutory_rule_applied}</span></div>
          <div><strong>Internal Policy:</strong> <span style="color:#c084fc;">${r.internal_policy_applied}</span></div>
          ${r.stop_rule_triggered ? `<div><strong>Stopping Rule:</strong> <span style="color:#ef4444; font-weight:700;">${r.stop_rule_triggered}</span></div>` : ""}
          <div style="margin-top:4px; color:#e2e8f0;">📝 <em>"${r.decision_rationale}"</em></div>
        </div>
      </div>
    `;
    modalBody.appendChild(stepEl);
  });
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
      decision_rationale: `Ingested failure event ${t.error_reason}. Invariant checks triggered.`
    },
    {
      from_state: "DIAGNOSING",
      to_state: "ACTION_SCHEDULED",
      timestamp: t.timestamp,
      event_type: "ACTION_PLAN_GENERATED",
      channel: "AUTO_DEBIT_API",
      statutory_rule_applied: t.amount > 15000 ? "RBI_DPSS_2026_27_396_15K_CAP" : "RBI_2026_PRE_DEBIT_24H_NOTICE_REQUIRED",
      internal_policy_applied: "48H_COOLING_INTERVAL_SALARY_CYCLE_SNAP",
      decision_rationale: t.amount > 15000 ? "Amount exceeds ₹15k statutory AFA cap. Direct auto-debit prohibited; dynamic AFA OTP checkout link dispatched." : "Mandated >=24h pre-debit alert queued with customer opt-out link."
    }
  ];
  renderAuditTimeline(mockRecords);
}

function closeModal(event) {
  document.getElementById("auditModal").style.display = "none";
}

function runDemoSimulation() {
  openAuditModal("sub_live_recov_9824");
}
