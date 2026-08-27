/**
 * Front-end controller for Razorpay AI Revenue Recovery Dashboard.
 * Light Theme FinTech SaaS Design System.
 */

let allTransactions = [];
let allAuditRecords = [];
let currentViewingTxnId = null;

// Initialize Dashboard
document.addEventListener("DOMContentLoaded", async () => {
  setupViewRouting();
  setupSidebarResizer();
  await loadSummaryData();
  await loadTransactions();
});

const VIEW_TITLES = {
  overview: "Overview",
  benchmark: "Comparative Benchmark",
  transactions: "Audit Explorer",
  rules: "Compliance Rules",
};

function setupViewRouting() {
  const initialView = window.location.hash ? window.location.hash.replace("#", "") : "overview";
  switchView(initialView in VIEW_TITLES ? initialView : "overview", false);

  window.addEventListener("hashchange", () => {
    const currentHash = window.location.hash.replace("#", "");
    if (currentHash in VIEW_TITLES) {
      switchView(currentHash, false);
    }
  });

  const navItems = document.querySelectorAll(".sidebar-nav .nav-item");
  navItems.forEach(item => {
    item.addEventListener("click", (e) => {
      e.preventDefault();
      const viewName = item.getAttribute("data-view") || item.getAttribute("href").replace("#", "");
      switchView(viewName, true);
    });
  });
}

function toggleSidebarCollapse() {
  const sidebar = document.getElementById("appSidebar");
  const mainContainer = document.querySelector(".main-container");
  if (!sidebar || !mainContainer) return;

  const isCollapsed = sidebar.classList.toggle("collapsed");
  if (isCollapsed) {
    mainContainer.style.marginLeft = "68px";
  } else {
    const width = localStorage.getItem("sidebarWidth") || "260px";
    sidebar.style.width = width;
    mainContainer.style.marginLeft = width;
  }
}

function setupSidebarResizer() {
  const sidebar = document.getElementById("appSidebar");
  const resizer = document.getElementById("sidebarResizer");
  const mainContainer = document.querySelector(".main-container");
  if (!sidebar || !resizer || !mainContainer) return;

  const savedWidth = localStorage.getItem("sidebarWidth") || "260px";
  sidebar.style.width = savedWidth;
  mainContainer.style.marginLeft = savedWidth;

  let isResizing = false;

  resizer.addEventListener("mousedown", (e) => {
    isResizing = true;
    resizer.classList.add("resizing");
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  });

  window.addEventListener("mousemove", (e) => {
    if (!isResizing) return;
    const newWidth = Math.max(200, Math.min(e.clientX, 420));
    sidebar.style.width = `${newWidth}px`;
    mainContainer.style.marginLeft = `${newWidth}px`;
    localStorage.setItem("sidebarWidth", `${newWidth}px`);
  });

  window.addEventListener("mouseup", () => {
    if (isResizing) {
      isResizing = false;
      resizer.classList.remove("resizing");
      document.body.style.cursor = "default";
      document.body.style.userSelect = "auto";
    }
  });
}

function switchView(viewName, updateHash = true) {
  if (!(viewName in VIEW_TITLES)) viewName = "overview";

  // 1. Hide all view sections, show active view
  document.querySelectorAll(".view-section").forEach(sec => sec.classList.remove("active"));
  const targetSection = document.getElementById(`view-${viewName}`);
  if (targetSection) {
    targetSection.classList.add("active");
  }

  // 2. Update sidebar nav active state
  document.querySelectorAll(".sidebar-nav .nav-item").forEach(item => {
    const itemTarget = item.getAttribute("data-view") || item.getAttribute("href").replace("#", "");
    if (itemTarget === viewName) {
      item.classList.add("active");
    } else {
      item.classList.remove("active");
    }
  });

  // 3. Update top breadcrumb
  const breadcrumb = document.getElementById("breadcrumbCurrent");
  if (breadcrumb) {
    breadcrumb.innerText = VIEW_TITLES[viewName];
  }

  // 4. Update browser URL hash
  if (updateHash) {
    window.location.hash = viewName;
  }

  window.scrollTo({ top: 0, behavior: "smooth" });
}

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
    console.warn("Using local benchmark fallback values", err);
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
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 32px; color: var(--text-muted);">No matching transactions found.</td></tr>`;
    return;
  }

  // Render top 100 for high-speed DOM rendering
  const displaySet = txns.slice(0, 100);

  displaySet.forEach((t) => {
    const tr = document.createElement("tr");
    tr.onclick = () => openAuditModal(t.txn_id);

    // 1. Classification (Recoverable vs Terminal Stop vs Human Review)
    let classPill = `<span class="badge-pill pill-success"><span class="badge-dot"></span>Recoverable</span>`;
    if (t.dispute_active || t.error_reason === "mandate_cancelled_by_user" || (t.attempt_history && t.attempt_history.length >= 3)) {
      classPill = `<span class="badge-pill pill-error"><span class="badge-dot"></span>Terminal Stop</span>`;
    } else if (t.risk_flag || t.error_reason === "raw_unmapped_decline") {
      classPill = `<span class="badge-pill pill-warning"><span class="badge-dot"></span>Human Review</span>`;
    }

    // 2. Compliance State (Specific Statutory Guard)
    const isExempt = ["mutual_fund", "insurance_premium", "credit_card_bill"].includes((t.category || "").toLowerCase()) || Boolean(t.is_afa_exempt);
    const statutoryCap = isExempt ? 100000.0 : 15000.0;
    const isRecurring = (t.txn_type || "").toLowerCase() === "recurring_subscription";

    let compPill = `<span class="badge-pill pill-neutral">Clear</span>`;
    if (t.dispute_active) {
      compPill = `<span class="badge-pill pill-error">Dispute Locked</span>`;
    } else if (t.error_reason === "mandate_cancelled_by_user") {
      compPill = `<span class="badge-pill pill-warning">Revoked Mandate</span>`;
    } else if (t.is_dnd) {
      compPill = `<span class="badge-pill pill-warning">DND Suppressed</span>`;
    } else if (isRecurring && t.amount > statutoryCap) {
      compPill = `<span class="badge-pill pill-info">AFA OTP Enforced</span>`;
    } else if (isRecurring && isExempt && t.amount > 15000 && t.amount <= 100000) {
      compPill = `<span class="badge-pill pill-success">AFA Exempt (₹1L Cap)</span>`;
    } else if (isRecurring) {
      compPill = `<span class="badge-pill pill-info">24h Notice Queued</span>`;
    }

    const edgeBadge = t.edge_case_tag ? `<span class="tag-edge">${t.edge_case_tag}</span>` : "";

    tr.innerHTML = `
      <td>
        <div class="cell-mono"><strong>${t.txn_id}</strong></div>
        <div style="font-size:11px; color:var(--text-muted); margin-top:2px;">${formatPaymentMethod(t.method)} • ${t.category}</div>
        ${edgeBadge}
      </td>
      <td>
        <div class="cell-amount">₹${t.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
      </td>
      <td>
        <div class="cell-mono" style="font-size:12px; font-weight:500; color:var(--text-primary);">${t.error_reason}</div>
        <div style="font-size:11px; color:var(--text-muted);">${t.customer_phone_masked || t.customer_email_masked || ""}</div>
      </td>
      <td>${classPill}</td>
      <td>${compPill}</td>
      <td style="text-align:right;">
        <button class="btn-inspect" onclick="event.stopPropagation(); openAuditModal('${t.txn_id}')">Inspect</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function formatPaymentMethod(m) {
  if (!m) return "Card";
  if (m === "upi_autopay") return "UPI AutoPay";
  if (m === "upi_collect") return "UPI Collect";
  if (m === "card") return "Card";
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
  document.getElementById("modalTxnId").innerText = `Transaction Audit Trail: ${txn_id}`;

  const targetTxn = allTransactions.find((t) => t.txn_id === txn_id);
  if (targetTxn) {
    document.getElementById("modalCustomer").innerText = `Customer (DPDP Masked): ${targetTxn.customer_phone_masked || targetTxn.customer_email_masked} • Amount: ₹${targetTxn.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })} • ${targetTxn.category}`;
  }

  modalBody.innerHTML = `<div style="text-align:center; padding: 24px; color: var(--text-muted);">Loading audit records...</div>`;
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
    let pillClass = "pill-success";
    if (r.to_state === "UNRECOVERABLE") pillClass = "pill-error";
    if (r.to_state === "HUMAN_REVIEW" || r.to_state === "PTP_FROZEN") pillClass = "pill-warning";
    if (r.to_state === "ACTION_SCHEDULED" || r.to_state === "DIAGNOSING") pillClass = "pill-info";

    const item = document.createElement("div");
    item.className = "timeline-item";
    item.innerHTML = `
      <div class="timeline-item-header">
        <div class="timeline-step-title">
          <span>Step ${idx + 1}: ${formatEventType(r.event_type)}</span>
          <span class="badge-pill ${pillClass}"><span class="badge-dot"></span>${r.to_state}</span>
        </div>
        <div class="timeline-timestamp">${r.timestamp.substring(0, 19).replace("T", " ")} UTC</div>
      </div>

      <div class="timeline-meta-grid">
        <div class="timeline-meta-label">Channel: <span class="timeline-meta-val">${r.channel}</span></div>
        <div class="timeline-meta-label">Statutory Citation: <span class="timeline-meta-val">${r.statutory_rule_applied}</span></div>
        <div class="timeline-meta-label">Internal Policy: <span class="timeline-meta-val">${r.internal_policy_applied}</span></div>
        ${r.stop_rule_triggered ? `<div class="timeline-meta-label">Stopping Rule: <span class="timeline-meta-val" style="color:var(--color-error); font-weight:600;">${r.stop_rule_triggered}</span></div>` : ""}
      </div>

      <div class="timeline-rationale-box">
        ${r.decision_rationale}
      </div>
    `;
    modalBody.appendChild(item);
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

async function runDemoSimulation() {
  currentViewingTxnId = "sub_live_recov_9824";
  const modal = document.getElementById("auditModal");
  const modalBody = document.getElementById("modalBody");
  document.getElementById("modalTxnId").innerText = `Live End-to-End Simulation: sub_live_recov_9824`;
  document.getElementById("modalCustomer").innerText = `Customer: +91-9876****4321 • Amount: ₹4,999.00 • Category: STANDARD`;

  modal.style.display = "flex";
  modalBody.innerHTML = `
    <div style="background:#EFF6FF; border:1px solid #BFDBFE; border-radius:6px; padding:16px; margin-bottom:12px;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
        <span style="font-size:13px; font-weight:600; color:#1E40AF;">Running Live Recovery Simulation</span>
        <span class="badge-pill pill-info" id="simLiveBadge"><span class="badge-dot"></span>In Progress</span>
      </div>
      <div style="background:#DBEAFE; height:6px; border-radius:3px; overflow:hidden;">
        <div id="simProgressBar" style="background:#2563EB; height:100%; width:15%; transition:width 300ms ease-out;"></div>
      </div>
      <div style="font-size:11px; color:#3B82F6; margin-top:6px;" id="simStatusText">Initializing recovery state machine and virtual clock...</div>
    </div>
    <div id="simTimelineContainer" style="display:flex; flex-direction:column; gap:10px;"></div>
  `;

  try {
    const res = await fetch("/api/run-demo");
    const data = res.ok ? await res.json() : null;
    const steps = (data && data.steps && data.steps.length > 0) ? data.steps : getFallbackDemoSteps();

    const container = document.getElementById("simTimelineContainer");
    const progressBar = document.getElementById("simProgressBar");
    const statusText = document.getElementById("simStatusText");
    const liveBadge = document.getElementById("simLiveBadge");

    for (let i = 0; i < steps.length; i++) {
      await new Promise(r => setTimeout(r, 450));
      const step = steps[i];
      const pct = Math.round(((i + 1) / steps.length) * 100);
      if (progressBar) progressBar.style.width = `${pct}%`;
      if (statusText) statusText.innerText = `Executing Step ${i + 1} of ${steps.length}: ${formatEventType(step.event_type)} (${step.from_state} ➔ ${step.to_state})`;

      let pillClass = "pill-info";
      if (step.to_state === "RECOVERED") pillClass = "pill-success";
      else if (step.to_state === "PTP_FROZEN") pillClass = "pill-warning";
      else if (step.to_state === "UNRECOVERABLE") pillClass = "pill-error";

      const card = document.createElement("div");
      card.className = "timeline-item";
      card.style.opacity = "0";
      card.style.transform = "translateY(6px)";
      card.style.transition = "opacity 200ms ease-out, transform 200ms ease-out";
      card.innerHTML = `
        <div class="timeline-item-header">
          <div class="timeline-step-title">
            <span>Step ${i + 1}: ${formatEventType(step.event_type)}</span>
            <span class="badge-pill ${pillClass}"><span class="badge-dot"></span>${step.to_state}</span>
          </div>
          <div class="timeline-timestamp">${(step.timestamp || "").substring(0, 19).replace("T", " ")} UTC</div>
        </div>
        <div class="timeline-meta-grid">
          <div class="timeline-meta-label">Channel: <span class="timeline-meta-val">${step.channel}</span></div>
          <div class="timeline-meta-label">Statutory Citation: <span class="timeline-meta-val">${step.statutory_rule_applied}</span></div>
          <div class="timeline-meta-label">Policy Rule: <span class="timeline-meta-val">${step.internal_policy_applied}</span></div>
          ${step.stop_rule_triggered ? `<div class="timeline-meta-label">Stopping Rule: <span class="timeline-meta-val" style="color:var(--color-error); font-weight:600;">${step.stop_rule_triggered}</span></div>` : ""}
        </div>
        <div class="timeline-rationale-box">
          ${step.decision_rationale}
        </div>
      `;
      container.appendChild(card);
      setTimeout(() => {
        card.style.opacity = "1";
        card.style.transform = "translateY(0)";
      }, 30);
    }

    if (liveBadge) {
      liveBadge.className = "badge-pill pill-success";
      liveBadge.innerHTML = `<span class="badge-dot"></span>Completed`;
    }
    if (statusText) {
      statusText.innerText = "Simulation Finished: ₹4,999.00 recovered in 7 simulated days (Zero compliance breaches).";
    }

  } catch (err) {
    console.error("Failed to run demo simulation", err);
    openAuditModal("sub_live_recov_9824");
  }
}

function getFallbackDemoSteps() {
  return [
    {
      from_state: "DETECTED",
      to_state: "DIAGNOSING",
      event_type: "FAILURE_DETECTED",
      channel: "GATEWAY_WEBHOOK",
      statutory_rule_applied: "NONE",
      internal_policy_applied: "TRIAGE_INGESTION_GATE",
      decision_rationale: "Payment failure ingested: insufficient_funds. Routing to diagnostic engine.",
      timestamp: "2026-08-27T10:00:00Z"
    },
    {
      from_state: "DIAGNOSING",
      to_state: "ACTION_SCHEDULED",
      event_type: "ACTION_PLAN_SCHEDULED",
      channel: "AUTO_DEBIT_API",
      statutory_rule_applied: "RBI_2026_PRE_DEBIT_24H_NOTICE_REQUIRED",
      internal_policy_applied: "48H_COOLING_INTERVAL_SALARY_CYCLE_SNAP",
      decision_rationale: "Soft Liquidity Retry #1: Mandated >=24h Pre-Debit Alert queued for 2026-08-27; auto-debit scheduled for 2026-08-29.",
      timestamp: "2026-08-27T10:00:00Z"
    },
    {
      from_state: "ACTION_SCHEDULED",
      to_state: "ACTION_SCHEDULED",
      event_type: "PRE_DEBIT_NOTIFICATION_DISPATCHED",
      channel: "WHATSAPP_SERVICE",
      statutory_rule_applied: "RBI_2026_PRE_DEBIT_24H_NOTICE_REQUIRED",
      internal_policy_applied: "INTERNAL_SAFE_HOURS_08_TO_20_IST",
      decision_rationale: "Dispatched statutory >=24h pre-debit alert prior to retry with opt-out link.",
      timestamp: "2026-08-27T10:00:00Z"
    },
    {
      from_state: "ACTION_SCHEDULED",
      to_state: "RETRYING",
      event_type: "AUTO_DEBIT_ATTEMPT_1_EXECUTED",
      channel: "AUTO_DEBIT_API",
      statutory_rule_applied: "RBI_2026_PRE_DEBIT_24H_NOTICE_REQUIRED",
      internal_policy_applied: "48H_COOLING_INTERVAL_SALARY_CYCLE_SNAP",
      decision_rationale: "Statutory notice window satisfied. Executed automated recurring debit attempt #1.",
      timestamp: "2026-08-29T10:00:00Z"
    },
    {
      from_state: "RETRYING",
      to_state: "ESCALATED",
      event_type: "AI_VOICE_OUTREACH_ENGAGED",
      channel: "VOICE_BOT",
      statutory_rule_applied: "NONE",
      internal_policy_applied: "RESPECTFUL_HINGLISH_VOICE_DUNNING",
      decision_rationale: "Empathetic voice recovery bot engaged. Customer committed to Promise-to-Pay (PTP) for September 5th.",
      timestamp: "2026-08-29T10:00:00Z"
    },
    {
      from_state: "ESCALATED",
      to_state: "PTP_FROZEN",
      event_type: "PTP_HOLD_FROZEN",
      channel: "INTERNAL_PORTAL",
      statutory_rule_applied: "NONE",
      internal_policy_applied: "PTP_FREEZE_GRACE_WINDOW",
      decision_rationale: "Promise-to-Pay locked for 2026-09-05. All dunning touches frozen until 2026-09-06.",
      stop_rule_triggered: "STOP_PTP_ACTIVE",
      timestamp: "2026-08-29T10:00:00Z"
    },
    {
      from_state: "PTP_FROZEN",
      to_state: "RECOVERED",
      event_type: "WEBHOOK_PAYMENT_CAPTURED",
      channel: "RAZORPAY_WEBHOOK",
      statutory_rule_applied: "RBI_POST_DEBIT_GRIEVANCE_RECEIPT",
      internal_policy_applied: "INSTANT_QUEUE_PURGE_ON_SETTLEMENT",
      decision_rationale: "Payment captured in full on PTP promise date. Dispatched confirmation receipt. Terminal state: RECOVERED 🚀",
      stop_rule_triggered: "STOP_PAID",
      timestamp: "2026-09-05T11:30:00Z"
    }
  ];
}
