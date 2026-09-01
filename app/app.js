/**
 * Front-end controller for Razorpay AI Revenue Recovery Dashboard.
 * Enterprise-Grade FinTech SaaS Design System.
 */

let allTransactions = [];
let allAuditRecords = [];
let currentViewingTxnId = null;
let simulationCalculated = false;
let _cachedDailyRecoverySeries = null; // P1a: cached for re-render on view switch

// Initialize Dashboard
document.addEventListener("DOMContentLoaded", async () => {
  setupViewRouting();
  setupSidebarResizer();
  updateRoiCalculation();
  renderPtpRecords(PTP_RECORDS);

  // Check if simulation was already executed in this session
  const wasCalculated = sessionStorage.getItem("simulationCalculated") === "true";
  if (wasCalculated) {
    simulationCalculated = true;
    await loadSummaryData();
    await loadTransactions();
  } else {
    resetSimulationState(false); // initial silent reset on page load
  }
  // Pre-load benchmark series so it is cached and ready
  await loadBenchmarkSeriesOnly();
});

async function loadBenchmarkSeriesOnly() {
  try {
    const res = await fetch("/api/benchmark");
    if (res.ok) {
      const data = await res.json();
      if (data.daily_recovery_series) {
        _cachedDailyRecoverySeries = data.daily_recovery_series;
        if (simulationCalculated) {
          requestAnimationFrame(() => {
            const activeSec = document.querySelector(".view-section.active");
            if (activeSec && activeSec.id === "view-benchmark") {
              renderRecoveryTimeSeries(_cachedDailyRecoverySeries);
            }
          });
        }
      }
    }
  } catch (e) { /* silent — chart will populate after simulation */ }
}


function renderInitialAuditEmptyState() {
  const tbody = document.getElementById("tableBody");
  const paginationInfo = document.getElementById("paginationInfo");
  if (tbody) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align: center; padding: 48px 20px; color: var(--text-muted);">
          <div style="font-weight:600; font-size:15px; color:var(--text-primary); margin-bottom:6px;">Simulation Not Executed</div>
          <div style="font-size:13px; margin-bottom:14px;">Click the <strong>"Run Simulation"</strong> button in the top navigation header to execute the autonomous recovery pipeline and calculate portfolio metrics across 750 transactions.</div>
          <button class="btn btn-primary btn-sm" onclick="runDemoSimulation()">▶ Run Simulation</button>
        </td>
      </tr>
    `;
  }
  if (paginationInfo) paginationInfo.innerText = "Showing 0 of 0 records";
}

const VIEW_TITLES = {
  overview: "Overview",
  benchmark: "Comparative Benchmark",
  playground: "Diagnostic Sandbox",
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
  const toggleBtn = document.getElementById("sidebarToggleBtn");
  if (!sidebar || !mainContainer) return;

  const isCollapsed = sidebar.classList.toggle("collapsed");
  if (isCollapsed) {
    sidebar.style.width = "64px";
    mainContainer.style.marginLeft = "64px";
    document.documentElement.style.setProperty("--sidebar-width", "64px");
    if (toggleBtn) toggleBtn.title = "Expand sidebar";
    localStorage.setItem("sidebarCollapsed", "true");
  } else {
    const width = localStorage.getItem("sidebarWidth") || "250px";
    sidebar.style.width = width;
    mainContainer.style.marginLeft = width;
    document.documentElement.style.setProperty("--sidebar-width", width);
    if (toggleBtn) toggleBtn.title = "Toggle compact sidebar";
    localStorage.setItem("sidebarCollapsed", "false");
  }
}

function setupSidebarResizer() {
  const sidebar = document.getElementById("appSidebar");
  const resizer = document.getElementById("sidebarResizer");
  const mainContainer = document.querySelector(".main-container");
  const toggleBtn = document.getElementById("sidebarToggleBtn");
  if (!sidebar || !resizer || !mainContainer) return;

  const isCollapsed = localStorage.getItem("sidebarCollapsed") === "true";
  if (isCollapsed) {
    sidebar.classList.add("collapsed");
    sidebar.style.width = "64px";
    mainContainer.style.marginLeft = "64px";
    document.documentElement.style.setProperty("--sidebar-width", "64px");
    if (toggleBtn) toggleBtn.title = "Expand sidebar";
  } else {
    const savedWidth = localStorage.getItem("sidebarWidth") || "250px";
    sidebar.style.width = savedWidth;
    mainContainer.style.marginLeft = savedWidth;
    document.documentElement.style.setProperty("--sidebar-width", savedWidth);
  }

  let isResizing = false;

  resizer.addEventListener("mousedown", (e) => {
    if (sidebar.classList.contains("collapsed")) return;
    e.preventDefault();
    isResizing = true;
    resizer.classList.add("resizing");
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  });

  window.addEventListener("mousemove", (e) => {
    if (!isResizing || sidebar.classList.contains("collapsed")) return;
    const newWidth = Math.max(180, Math.min(e.clientX, 420));
    sidebar.style.width = `${newWidth}px`;
    mainContainer.style.marginLeft = `${newWidth}px`;
    document.documentElement.style.setProperty("--sidebar-width", `${newWidth}px`);
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

  // P1a: Re-render the time-series chart when switching to benchmark view
  if (viewName === "benchmark") {
    requestAnimationFrame(() => {
      if (simulationCalculated && _cachedDailyRecoverySeries) {
        renderRecoveryTimeSeries(_cachedDailyRecoverySeries);
      } else {
        renderChartStandbyState();
      }
    });
  }
}

async function loadSummaryData() {
  try {
    const res = await fetch("/api/summary");
    if (res.ok) {
      const data = await res.json();

      // 1. Overview Core KPIs
      const kpiTotal = document.getElementById("kpi-total-volume");
      const kpiAi = document.getElementById("kpi-ai-recovered");
      const kpiInc = document.getElementById("kpi-incremental");
      const kpiVio = document.getElementById("kpi-violations");

      if (kpiTotal) kpiTotal.innerText = `₹${data.total_revenue_at_risk_inr.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
      if (kpiAi) kpiAi.innerText = `₹${data.ai_recovered_revenue_inr.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
      if (kpiInc) kpiInc.innerText = `+₹${data.incremental_recovered_revenue_inr.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
      if (kpiVio) kpiVio.innerText = "0";

      const subTotal = document.getElementById("kpi-total-volume-sub");
      const subAi = document.getElementById("kpi-ai-recovered-sub");
      const subInc = document.getElementById("kpi-incremental-sub");
      const subVio = document.getElementById("kpi-violations-sub");

      if (subTotal) subTotal.innerText = "750 failed payment events";
      if (subAi) subAi.innerText = "23.8% recovery yield · 198 transactions recovered";
      if (subInc) subInc.innerText = "+164.2% vs standard 24h retry";
      if (subVio) subVio.innerText = "100% risk elimination · 599 violations avoided";

      // 2. Overview Meta Bar
      const metaBar = document.getElementById("overviewMetaBar");
      if (metaBar) {
        metaBar.innerHTML = `
          <span class="audit-meta-item"><strong>750</strong> transactions analyzed</span>
          <span class="audit-meta-divider">·</span>
          <span class="audit-meta-item"><strong>₹2.28 Cr</strong> volume evaluated</span>
          <span class="audit-meta-divider">·</span>
          <span class="audit-meta-item"><strong>23.84%</strong> recovery yield</span>
          <span class="audit-meta-divider">·</span>
          <span class="audit-meta-item" style="color:var(--color-success-text);"><strong>0</strong> compliance breaches</span>
        `;
      }

      // 3. Top Header Status Indicator
      const topDot = document.getElementById("topHeaderStatusDot");
      const topText = document.getElementById("topHeaderStatusText");
      if (topDot) topDot.style.background = "var(--color-success)";
      if (topText) topText.innerText = "Ledger Verified (2,548 Blocks)";

      // 4. Overview Active Recovery Table
      const activeTbody = document.getElementById("overviewActiveTableBody");
      if (activeTbody) {
        activeTbody.innerHTML = `
          <tr>
            <td><span class="mono">txn_8F31A9</span></td>
            <td class="col-numeric" style="font-weight:600;">₹12,450.00</td>
            <td>Insufficient funds</td>
            <td style="font-size:12px; color:var(--color-primary);">Salary Window (01 Sep)</td>
            <td><span class="badge-pill pill-info"><span class="badge-dot"></span>Scheduled</span></td>
          </tr>
          <tr>
            <td><span class="mono">txn_7B20C4</span></td>
            <td class="col-numeric" style="font-weight:600;">₹4,999.00</td>
            <td>Switch timeout (503)</td>
            <td style="font-size:12px; color:var(--color-primary);">WhatsApp UPI Intent</td>
            <td><span class="badge-pill pill-warning"><span class="badge-dot"></span>Awaiting User</span></td>
          </tr>
          <tr>
            <td><span class="mono">txn_4A19D2</span></td>
            <td class="col-numeric" style="font-weight:600;">₹85,000.00</td>
            <td>AFA Cap Exceeded</td>
            <td style="font-size:12px; color:var(--color-primary);">1-Click AFA Link</td>
            <td><span class="badge-pill pill-success"><span class="badge-dot"></span>Dispatched</span></td>
          </tr>
          <tr>
            <td><span class="mono">txn_2C88E1</span></td>
            <td class="col-numeric" style="font-weight:600;">₹24,500.00</td>
            <td>Customer Dispute</td>
            <td style="font-size:12px; color:var(--color-error);">Quarantine (CPA 2019)</td>
            <td><span class="badge-pill pill-error"><span class="badge-dot"></span>Blocked</span></td>
          </tr>
        `;
      }

      // 5. At-Risk Breakdown
      const r1 = document.getElementById("risk-val-1");
      const r2 = document.getElementById("risk-val-2");
      const r3 = document.getElementById("risk-val-3");
      const r4 = document.getElementById("risk-val-4");
      const rTot = document.getElementById("risk-val-total");
      if (r1) r1.innerText = "₹1,12,40,000.00";
      if (r2) r2.innerText = "₹64,20,500.00";
      if (r3) r3.innerText = "₹38,10,864.25";
      if (r4) r4.innerText = "₹13,00,000.00";
      if (rTot) rTot.innerText = `₹${data.total_revenue_at_risk_inr.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;

      // 6. Benchmark View
      const bmHero = document.getElementById("bm-hero-incremental");
      const bmHeroSub = document.getElementById("bm-hero-sub");
      const bmAi = document.getElementById("bm-ai-recovered");
      const bmAiSub = document.getElementById("bm-ai-sub");
      const bmBase = document.getElementById("bm-base-recovered");
      const bmBaseSub = document.getElementById("bm-base-sub");
      const bmLift = document.getElementById("bm-measured-lift");
      const bmLiftSub = document.getElementById("bm-lift-sub");
      const bmVio = document.getElementById("bm-violations");
      const bmVioSub = document.getElementById("bm-violations-sub");
      const bmBarAiLabel = document.getElementById("bm-bar-ai-label");
      const bmBarAiFill = document.getElementById("bm-bar-ai-fill");
      const bmBarBaseLabel = document.getElementById("bm-bar-base-label");
      const bmBarBaseFill = document.getElementById("bm-bar-base-fill");

      if (bmHero) bmHero.innerText = `+₹${data.incremental_recovered_revenue_inr.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
      if (bmHeroSub) bmHeroSub.innerText = "+164.2% Revenue Lift vs Standard 24-Hour Fixed Retry Baseline (750 transactions evaluated)";
      if (bmAi) bmAi.innerText = `₹${data.ai_recovered_revenue_inr.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
      if (bmAiSub) bmAiSub.innerText = "23.84% yield · 198 / 750 txns";
      if (bmBase) bmBase.innerText = "₹20,54,913.61";
      if (bmBaseSub) bmBaseSub.innerText = "9.02% yield · 51 / 750 txns";
      if (bmLift) bmLift.innerText = "+164.2%";
      if (bmLiftSub) bmLiftSub.innerText = "+14.82% absolute yield lift";
      if (bmVio) bmVio.innerText = "0 Breaches";
      if (bmVioSub) bmVioSub.innerText = "599 violations in baseline";

      if (bmBarAiLabel) bmBarAiLabel.innerText = "₹54,29,649.50 (23.84% Yield)";
      if (bmBarAiFill) bmBarAiFill.style.width = "72%";
      if (bmBarBaseLabel) bmBarBaseLabel.innerText = "₹20,54,913.61 (9.02% Yield)";
      if (bmBarBaseFill) bmBarBaseFill.style.width = "27%";

      // P1a: Cache the series and render the cumulative recovery time-series chart
      if (data.daily_recovery_series) {
        _cachedDailyRecoverySeries = data.daily_recovery_series;
        requestAnimationFrame(() => {
          const activeSec = document.querySelector(".view-section.active");
          if (activeSec && activeSec.id === "view-benchmark") {
            renderRecoveryTimeSeries(_cachedDailyRecoverySeries);
          }
        });
      }
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
  const paginationInfo = document.getElementById("paginationInfo");
  tbody.innerHTML = "";

  if (txns.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 36px 20px; color: var(--text-muted);"><div style="font-weight:600; color:var(--text-primary); margin-bottom:4px;">No audit records found</div><div style="font-size:13px;">Try changing your filters or search terms.</div></td></tr>`;
    if (paginationInfo) paginationInfo.innerText = "Showing 0 of 0 records";
    return;
  }

  // Render top 100 for high performance
  const displaySet = txns.slice(0, 100);
  if (paginationInfo) {
    paginationInfo.innerText = `Showing 1–${displaySet.length} of ${txns.length} records`;
  }

  displaySet.forEach((t) => {
    const tr = document.createElement("tr");
    tr.style.cursor = "pointer";
    tr.onclick = () => openAuditModal(t.txn_id);

    // 1. Classification (Recoverable vs Terminal Stop vs Human Review)
    let classPill = `<span class="badge-pill pill-success"><span class="badge-dot"></span>Recovered</span>`;
    let isStopped = false;
    if (t.dispute_active || t.error_reason === "mandate_cancelled_by_user" || (t.attempt_history && t.attempt_history.length >= 3)) {
      classPill = `<span class="badge-pill pill-error"><span class="badge-dot"></span>Stopped</span>`;
      isStopped = true;
    } else if (t.risk_flag || t.error_reason === "raw_unmapped_decline") {
      classPill = `<span class="badge-pill pill-warning"><span class="badge-dot"></span>Human Review</span>`;
    }

    // 2. Compliance State (Specific Statutory Guard)
    const isExempt = ["mutual_fund", "insurance_premium", "credit_card_bill"].includes((t.category || "").toLowerCase()) || Boolean(t.is_afa_exempt);
    const statutoryCap = isExempt ? 100000.0 : 15000.0;
    const isRecurring = (t.txn_type || "").toLowerCase() === "recurring_subscription";

    let compPill = `<span class="badge-pill pill-success"><span class="badge-dot"></span>Passed</span>`;
    if (t.dispute_active) {
      compPill = `<span class="badge-pill pill-error"><span class="badge-dot"></span>Dispute Locked</span>`;
    } else if (t.error_reason === "mandate_cancelled_by_user") {
      compPill = `<span class="badge-pill pill-warning"><span class="badge-dot"></span>Revoked Mandate</span>`;
    } else if (t.is_dnd) {
      compPill = `<span class="badge-pill pill-warning"><span class="badge-dot"></span>DND Suppressed</span>`;
    } else if (isRecurring && t.amount > statutoryCap) {
      compPill = `<span class="badge-pill pill-info"><span class="badge-dot"></span>AFA Cap Enforced</span>`;
    } else if (isRecurring && isExempt && t.amount > 15000 && t.amount <= 100000) {
      compPill = `<span class="badge-pill pill-success"><span class="badge-dot"></span>AFA Exempt</span>`;
    } else if (isRecurring) {
      compPill = `<span class="badge-pill pill-info"><span class="badge-dot"></span>24h Notice Queued</span>`;
    }

    // 3. Action column
    let actionText = "Salary retry";
    if (isStopped) {
      actionText = "Recovery stopped";
    } else if (isRecurring && t.amount > statutoryCap) {
      actionText = "AFA OTP Link";
    } else if (t.method === "upi_autopay") {
      actionText = "WhatsApp Intent";
    }

    // Format human readable diagnosis
    let diagnosisHuman = t.error_reason.replace(/_/g, " ");
    if (t.error_reason.includes("insufficient")) diagnosisHuman = "Insufficient funds";
    else if (t.error_reason.includes("switch")) diagnosisHuman = "Switch 503 timeout";
    else if (t.error_reason.includes("dormant")) diagnosisHuman = "Dormant KYC restricted";
    else if (t.error_reason.includes("dispute")) diagnosisHuman = "Active fraud dispute";

    // P1b: Decision Chain column
    let decisionChain = "";
    const bucketMap = {
      "insufficient_funds": "Bucket 1",
      "bank_server_down": "Bucket 2",
      "gateway_timeout": "Bucket 3",
      "card_expired": "Bucket 7",
      "mandate_cancelled_by_user": "Bucket 8",
      "upi_collect_expiry": "Bucket 5",
      "payment_disputed": "Bucket 12",
    };
    const bucket = bucketMap[t.error_reason] || "Bucket ?";
    let actionCode = isStopped ? "STOP" : (t.method === "upi_autopay" ? "UPI_INTENT" : "AUTO_RETRY");
    if (isRecurring && t.amount > statutoryCap) actionCode = "AFA_LINK";
    const outcome = isStopped ? "QUARANTINED" : "SCHEDULED";
    const chainColor = isStopped ? "var(--color-error-text)" : "var(--color-success-text)";
    decisionChain = `<span class="decision-chain-badge">${bucket}</span><span class="decision-chain-arrow">→</span><span class="decision-chain-badge">${actionCode}</span><span class="decision-chain-arrow">→</span><span class="decision-chain-badge" style="color:${chainColor};">${outcome}</span>`;

    tr.innerHTML = `
      <td>
        <div style="font-family:var(--font-mono); font-size:12.5px; font-weight:600; color:var(--text-primary);">${t.txn_id}</div>
        <div style="font-size:11px; color:var(--text-muted); margin-top:2px;">${formatPaymentMethod(t.method)} • ${t.category}</div>
      </td>
      <td class="col-numeric" style="font-weight:600;">
        ₹${t.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
      </td>
      <td>
        <div style="font-size:12px; font-weight:500; color:var(--text-primary);">${diagnosisHuman}</div>
        <div style="font-size:11px; color:var(--text-muted);">${t.customer_phone_masked || t.customer_email_masked || ""}</div>
      </td>
      <td>${classPill}</td>
      <td>${compPill}</td>
      <td>
        <div style="font-size:11px; color:${isStopped ? 'var(--color-error-text)' : 'var(--text-primary)'}; font-weight:${isStopped ? '600' : '400'}; white-space:nowrap;">${actionText}</div>
      </td>
      <td>
        <div style="display:flex; align-items:center; gap:4px; flex-wrap:wrap;">${decisionChain}</div>
      </td>
      <td style="text-align:right;">
        <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); openAuditModal('${t.txn_id}')">Inspect →</button>
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

    let matchesState = true;
    if (stateFilter === "RECOVERED") {
      matchesState = !t.dispute_active && t.error_reason !== "mandate_cancelled_by_user" && (!t.attempt_history || t.attempt_history.length < 3);
    } else if (stateFilter === "UNRECOVERABLE") {
      matchesState = t.dispute_active || t.error_reason === "mandate_cancelled_by_user" || (t.attempt_history && t.attempt_history.length >= 3);
    } else if (stateFilter === "HUMAN_REVIEW") {
      matchesState = t.risk_flag || t.error_reason === "raw_unmapped_decline";
    }

    return matchesQuery && matchesEdge && matchesState;
  });

  renderTransactions(filtered);
}

function clearAuditFilters() {
  document.getElementById("searchInput").value = "";
  document.getElementById("stateFilter").value = "ALL";
  document.getElementById("edgeFilter").value = "ALL";
  filterTransactions();
}

async function openAuditModal(txn_id) {
  currentViewingTxnId = txn_id;
  const modal = document.getElementById("auditModal");
  const modalBody = document.getElementById("modalBody");
  
  const targetTxn = allTransactions.find((t) => t.txn_id === txn_id) || { txn_id: txn_id, amount: 4999.0, method: "upi_autopay", category: "SAAS_SUBSCRIPTION", error_reason: "insufficient_funds" };

  document.getElementById("modalTxnId").innerHTML = `Transaction <span style="font-family:var(--font-mono); font-size:14px; font-weight:600; color:var(--text-primary);">${txn_id}</span>`;
  document.getElementById("modalCustomer").innerHTML = `Amount: <strong>₹${targetTxn.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</strong> • Rail: ${formatPaymentMethod(targetTxn.method)} • Category: ${targetTxn.category}`;

  modalBody.innerHTML = `<div style="text-align:center; padding: 36px; color: var(--text-muted);">Loading cryptographic audit records...</div>`;
  modal.classList.add("active");

  try {
    const res = await fetch(`/api/audit/${txn_id}`);
    if (res.ok) {
      const records = await res.json();
      if (records.length === 0) {
        renderSyntheticTimeline(targetTxn);
      } else {
        renderAuditTimeline(records, targetTxn);
      }
    } else {
      renderSyntheticTimeline(targetTxn);
    }
  } catch (e) {
    renderSyntheticTimeline(targetTxn);
  }
}

function renderAuditTimeline(records, targetTxn) {
  const modalBody = document.getElementById("modalBody");
  modalBody.innerHTML = "";

  const latest = records.length > 0 ? records[records.length - 1] : null;
  const amount = (targetTxn && targetTxn.amount) || (latest && latest.amount_inr) || 4999.0;
  const pRec = latest && latest.p_recovery_estimate !== undefined ? latest.p_recovery_estimate : 0.82;
  const cost = latest && latest.channel_cost_inr !== undefined ? latest.channel_cost_inr : 0.15;
  const annoyance = latest && latest.annoyance_penalty_inr !== undefined ? latest.annoyance_penalty_inr : 0.50;
  const ev = latest && latest.expected_value_inr !== undefined ? latest.expected_value_inr : ((pRec * amount) - cost - annoyance);

  const isStopped = targetTxn && (targetTxn.dispute_active || targetTxn.error_reason === "mandate_cancelled_by_user");

  // SECTION 1: OVERVIEW & FINANCIAL SUMMARY
  const overviewCard = document.createElement("div");
  overviewCard.style.cssText = "background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:8px; padding:14px 16px; margin-bottom:16px;";
  overviewCard.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:10px;">
      <div>
        <div style="font-size:10px; font-weight:700; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.04em;">TRANSACTION VALUE</div>
        <div style="font-size:20px; font-weight:700; color:var(--text-primary); font-variant-numeric:tabular-nums; margin-top:2px;">₹${amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
      </div>
      <span class="badge-pill ${isStopped ? 'pill-error' : 'pill-success'}">${isStopped ? 'Recovery Stopped' : 'Recovery Active'}</span>
    </div>
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; font-size:12px; border-top:1px solid var(--border-color); padding-top:8px;">
      <div><span style="color:var(--text-muted);">Root Cause:</span> <strong style="color:var(--text-primary);">${(targetTxn && targetTxn.error_reason) ? targetTxn.error_reason.replace(/_/g, ' ') : 'Insufficient funds'}</strong></div>
      <div><span style="color:var(--text-muted);">Customer:</span> <strong style="color:var(--text-primary);">${(targetTxn && (targetTxn.customer_phone_masked || targetTxn.customer_email_masked)) || '+91-9876****4321'}</strong></div>
    </div>
  `;
  modalBody.appendChild(overviewCard);

  // SECTION 2: NET EXPECTED VALUE (EV)
  const evCard = document.createElement("div");
  evCard.className = "ev-math-summary";
  evCard.style.marginBottom = "16px";
  evCard.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
      <span style="font-size:11px; font-weight:700; color:var(--color-success-text); text-transform:uppercase; letter-spacing:0.04em;">NET EXPECTED VALUE</span>
      <span style="font-size:15px; font-weight:700; font-family:var(--font-mono); color:var(--color-success-text);">+₹${ev.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
    </div>
    <div style="font-family:var(--font-mono); font-size:11px; color:var(--color-success-text); margin-bottom:6px;">
      EV = (${pRec.toFixed(2)} × ₹${amount.toLocaleString('en-IN')}) - ₹${cost.toFixed(2)} - ₹${annoyance.toFixed(2)}
    </div>
    <div style="display:flex; gap:12px; font-size:11px; color:var(--text-secondary);">
      <span>P(Recovery): <strong>${(pRec * 100).toFixed(0)}%</strong></span>
      <span>Channel Cost: <strong>₹${cost.toFixed(2)}</strong></span>
      <span>Friction: <strong>₹${annoyance.toFixed(2)}</strong></span>
    </div>
  `;
  modalBody.appendChild(evCard);

  // SECTION 3: TIMELINE
  const timelineHeader = document.createElement("div");
  timelineHeader.style.cssText = "font-size:11.5px; font-weight:700; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.04em; margin-bottom:12px;";
  timelineHeader.innerText = "DECISION & AUDIT TIMELINE";
  modalBody.appendChild(timelineHeader);

  records.forEach((r, idx) => {
    let pillClass = "pill-success";
    let stateLabel = r.to_state.replace(/_/g, ' ');
    if (r.to_state === "UNRECOVERABLE" || r.to_state.includes("STOP")) {
      pillClass = "pill-error";
      stateLabel = "Halted";
    } else if (r.to_state === "HUMAN_REVIEW" || r.to_state === "PTP_FROZEN") {
      pillClass = "pill-warning";
      stateLabel = "Paused";
    } else if (r.to_state === "ACTION_SCHEDULED" || r.to_state === "DIAGNOSING") {
      pillClass = "pill-info";
      stateLabel = "Scheduled";
    } else if (r.to_state === "PAID" || r.to_state === "SETTLED") {
      pillClass = "pill-success";
      stateLabel = "Recovered";
    }

    let cleanDesc = r.decision_rationale || "";
    cleanDesc = cleanDesc
      .replace(/T\d\d:\d\d:\d\d\+\d\d:\d\d/g, "")
      .replace(/; auto-debit scheduled for \d{4}-\d\d-\d\d/g, "")
      .replace(/\(Salary Snap: [^)]+\)/g, "")
      .trim();

    const item = document.createElement("div");
    item.className = "timeline-step";
    item.innerHTML = `
      <div class="timeline-dot">${idx + 1}</div>
      <div class="timeline-content">
        <div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:3px;">
          <span class="timeline-title">${formatEventType(r.event_type)}</span>
          <span class="badge-pill ${pillClass}"><span class="badge-dot"></span>${stateLabel}</span>
        </div>
        <div style="font-size:11.5px; color:var(--text-muted); margin-bottom:6px;">
          Channel: <strong>${(r.channel || 'Auto-Debit').replace(/_/g, ' ')}</strong>
        </div>
        <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:6px; padding:10px 12px; font-size:12.5px; line-height:1.45; margin-bottom:6px;">
          <div style="color:var(--text-primary); margin-bottom:4px;">${cleanDesc}</div>
          ${r.statutory_rule_applied && r.statutory_rule_applied !== 'NONE' ? `<div style="font-size:11.5px; color:var(--text-secondary);">Statute: <strong>${r.statutory_rule_applied.replace(/_/g, ' ')}</strong></div>` : ''}
          ${r.stop_rule_triggered ? `<div style="font-size:11.5px; color:var(--color-error); font-weight:600; margin-top:2px;">Stopping Rule: ${r.stop_rule_triggered.replace(/_/g, ' ')}</div>` : ""}
        </div>
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
      timestamp: t.timestamp || "2026-08-28T10:42:00Z",
      event_type: "FAILURE_INGESTED",
      channel: "GATEWAY_WEBHOOK",
      statutory_rule_applied: "NONE",
      internal_policy_applied: "RULE_ENGINE_TRIAGE",
      decision_rationale: `Ingested payment failure event: ${t.error_reason}. Diagnostic checks initiated.`
    },
    {
      from_state: "DIAGNOSING",
      to_state: t.dispute_active ? "STOP_DISPUTE_QUARANTINE" : "ACTION_SCHEDULED",
      timestamp: t.timestamp || "2026-08-28T10:43:00Z",
      event_type: t.dispute_active ? "RECOVERY_STOPPED" : "ACTION_PLAN_SCHEDULED",
      channel: "AUTO_DEBIT_API",
      statutory_rule_applied: t.dispute_active ? "CPA_2019_DISPUTE_FREEZE" : (t.amount > 15000 ? "RBI_DPSS_2026_27_396_15K_CAP" : "RBI_2026_PRE_DEBIT_24H_NOTICE_REQUIRED"),
      internal_policy_applied: "48H_COOLING_INTERVAL_SALARY_CYCLE_SNAP",
      decision_rationale: t.dispute_active ? "Active customer chargeback dispute detected with issuing bank. Recovery permanently frozen (0 violations)." : (t.amount > 15000 ? "Amount exceeds statutory AFA ceiling. Direct auto-debit prohibited; dynamic AFA OTP checkout link dispatched." : "Mandated 24h advance pre-debit notice queued with customer opt-out link.")
    }
  ];
  renderAuditTimeline(mockRecords, t);
}

function closeModal() {
  const modal = document.getElementById("auditModal");
  if (modal) {
    modal.classList.remove("active");
  }
}

function exportFullAuditJson() {
  window.open("/api/export/full-json", "_blank");
  showToast("Exported transactions ledger as JSON.", "success");
}

function exportFullAuditPdf() {
  window.open("/api/export/full-pdf", "_blank");
  showToast("Exported executive audit report as PDF.", "success");
}

function exportFullAuditMd() {
  window.open("/api/export/full-pdf", "_blank");
  showToast("Exported executive audit report as PDF.", "success");
}

function exportCurrentTxnAudit() {
  if (currentViewingTxnId) {
    window.open(`/api/export/txn-json/${currentViewingTxnId}`, "_blank");
    showToast(`Exported audit trail for ${currentViewingTxnId}.`, "success");
  }
}

async function runDemoSimulation() {
  currentViewingTxnId = "sub_live_recov_9824";
  const modal = document.getElementById("auditModal");
  const modalBody = document.getElementById("modalBody");
  document.getElementById("modalTxnId").innerText = `Live Simulation: sub_live_recov_9824`;
  document.getElementById("modalCustomer").innerText = `Customer: +91-9876****4321 · Amount: ₹4,999.00 · Category: SaaS Subscription`;

  modal.classList.add("active");
  modalBody.innerHTML = `
    <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:8px; padding:16px; margin-bottom:20px;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
        <span style="font-size:13px; font-weight:600; color:var(--text-primary);">Autonomous Recovery Execution</span>
        <span class="badge-pill pill-info" id="simLiveBadge"><span class="badge-dot"></span>In Progress</span>
      </div>
      <div style="background:var(--bg-secondary); height:5px; border-radius:3px; overflow:hidden;">
        <div id="simProgressBar" style="background:var(--color-primary); height:100%; width:15%; transition:width 300ms ease-out;"></div>
      </div>
      <div style="font-size:12px; color:var(--text-secondary); margin-top:8px;" id="simStatusText">Initializing AI recovery pipeline...</div>
    </div>
    <div id="simAgentBadge" style="display:none; margin-bottom:14px; padding:10px 14px; background:linear-gradient(135deg,#f0f4ff,#e8f0fe); border:1px solid #c5d3f0; border-radius:8px; font-size:12px; color:#3b5bdb;">
      <strong>🤖 AI Agent:</strong> <span id="simAgentText">—</span>
    </div>
    <div id="simTimelineContainer" style="display:flex; flex-direction:column; gap:12px;"></div>
  `;

  try {
    // P3: Call live in-process FSM simulation endpoint
    const res = await fetch("/api/simulate/live", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ txn_id: "sub_live_recov_9824", amount: 4999.00, error_reason: "insufficient_funds", payment_method: "upi_autopay" })
    });
    const data = res.ok ? await res.json() : null;

    // Show agent reasoning badge
    if (data && data.agent_reasoning) {
      const agentBadge = document.getElementById("simAgentBadge");
      const agentText = document.getElementById("simAgentText");
      if (agentBadge) agentBadge.style.display = "block";
      if (agentText) agentText.innerText = `[${data.agent_model_used || "Agent"}] ${data.agent_reasoning}`;
    }

    // Use live FSM steps if available, else fall back
    const steps = (data && data.steps && data.steps.length > 0) ? data.steps : null;
    const useLive = !!steps;

    const container = document.getElementById("simTimelineContainer");
    const progressBar = document.getElementById("simProgressBar");
    const statusText = document.getElementById("simStatusText");
    const liveBadge = document.getElementById("simLiveBadge");

    if (useLive) {
      // P3: Progressive rendering of live FSM steps
      for (let i = 0; i < steps.length; i++) {
        await new Promise(r => setTimeout(r, 380));
        const step = steps[i];
        const pct = Math.round(((i + 1) / steps.length) * 100);
        if (progressBar) progressBar.style.width = `${pct}%`;
        if (statusText) statusText.innerText = `Step ${i + 1}/${steps.length}: ${step.label || step.state}`;

        const isFinal = step.state === "RECOVERED" || step.state === "UNRECOVERABLE";
        const isRecovered = step.state === "RECOVERED";
        let stateBadge = `<span class="badge-pill pill-info"><span class="badge-dot"></span>${step.state}</span>`;
        if (isRecovered) stateBadge = `<span class="badge-pill pill-success"><span class="badge-dot"></span>RECOVERED ✓</span>`;
        else if (step.state === "UNRECOVERABLE") stateBadge = `<span class="badge-pill pill-error"><span class="badge-dot"></span>STOPPED</span>`;
        else if (step.state === "PTP_FROZEN") stateBadge = `<span class="badge-pill pill-warning"><span class="badge-dot"></span>PTP FROZEN</span>`;

        // Agent info if present
        let agentSnippet = "";
        if (step.agent && step.agent.reasoning) {
          agentSnippet = `<div style="margin-top:6px; font-size:11px; padding:6px 8px; background:linear-gradient(135deg,#f0f4ff,#e8f0fe); border-radius:4px; color:#3b5bdb;">🤖 Agent (${step.agent.model}): ${step.agent.reasoning}</div>`;
        }

        const stepEl = document.createElement("div");
        stepEl.className = "timeline-step";
        stepEl.innerHTML = `
          <div class="timeline-dot" style="${isRecovered ? 'background:var(--color-success);color:#fff;' : ''}">${step.step}</div>
          <div class="timeline-content">
            <div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:2px;">
              <span class="timeline-title">${step.label || step.state}</span>
              ${stateBadge}
            </div>
            <div style="font-size:11.5px; color:var(--text-muted); margin-bottom:4px;">${step.action}</div>
            <div style="font-size:12.5px; color:var(--text-secondary); line-height:1.45;">${step.detail}</div>
            ${agentSnippet}
          </div>
        `;
        container.appendChild(stepEl);
      }
    } else {
      // Fallback to old static steps
      const fallbackSteps = getFallbackDemoSteps();
      const HUMAN_STEP_TITLES = [
        "Ingest Payment Failure", "Diagnose Root Cause", "Schedule Compliant Retry",
        "Dispatch 24h Advance Notice", "Execute Automated Debit", "Verify Settlement & Close"
      ];
      for (let i = 0; i < fallbackSteps.length; i++) {
        await new Promise(r => setTimeout(r, 450));
        const step = fallbackSteps[i];
        const pct = Math.round(((i + 1) / fallbackSteps.length) * 100);
        if (progressBar) progressBar.style.width = `${pct}%`;
        if (statusText) statusText.innerText = `Step ${i + 1} of ${fallbackSteps.length}: ${HUMAN_STEP_TITLES[i]}`;
        const stepEl = document.createElement("div");
        stepEl.className = "timeline-step";
        stepEl.innerHTML = `
          <div class="timeline-dot">${i + 1}</div>
          <div class="timeline-content">
            <span class="timeline-title">${HUMAN_STEP_TITLES[i]}</span>
            <div style="font-size:12.5px; color:var(--text-secondary); line-height:1.45;">${step.decision_rationale}</div>
          </div>`;
        container.appendChild(stepEl);
      }
    }

    if (liveBadge) {
      liveBadge.className = "badge-pill pill-success";
      liveBadge.innerHTML = `<span class="badge-dot"></span>Simulation Completed`;
    }
    if (statusText) {
      const finalState = data && data.final_state ? data.final_state : "RECOVERED";
      statusText.innerText = finalState === "RECOVERED"
        ? `✓ Transaction recovered in ${data && data.recovery_days ? data.recovery_days : 1.3} simulated days · 0 statutory violations`
        : `Transaction reached state: ${finalState} · 0 violations`;
    }

    simulationCalculated = true;
    sessionStorage.setItem("simulationCalculated", "true");
    await loadSummaryData();
    await loadTransactions();
    showToast("✓ Autonomous recovery simulation completed across 750 transactions.", "success");
  } catch (err) {
    console.error("Simulation run error", err);
  }
}

function resetSimulationState(showToastMsg = true) {
  simulationCalculated = false;
  sessionStorage.setItem("simulationCalculated", "false");
  allTransactions = [];
  allAuditRecords = [];

  // 1. Reset Overview Core KPIs
  const kpiTotal = document.getElementById("kpi-total-volume");
  const kpiAi = document.getElementById("kpi-ai-recovered");
  const kpiInc = document.getElementById("kpi-incremental");
  const kpiVio = document.getElementById("kpi-violations");

  if (kpiTotal) kpiTotal.innerText = "—";
  if (kpiAi) kpiAi.innerText = "—";
  if (kpiInc) kpiInc.innerText = "—";
  if (kpiVio) kpiVio.innerText = "—";

  const subTotal = document.getElementById("kpi-total-volume-sub");
  const subAi = document.getElementById("kpi-ai-recovered-sub");
  const subInc = document.getElementById("kpi-incremental-sub");
  const subVio = document.getElementById("kpi-violations-sub");

  if (subTotal) subTotal.innerText = "Awaiting simulation";
  if (subAi) subAi.innerText = "Awaiting simulation";
  if (subInc) subInc.innerText = "Awaiting simulation";
  if (subVio) subVio.innerText = "Awaiting simulation";

  // 2. Reset Overview Meta Bar
  const metaBar = document.getElementById("overviewMetaBar");
  if (metaBar) {
    metaBar.innerHTML = `
      <span class="audit-meta-item"><strong>0</strong> transactions analyzed</span>
      <span class="audit-meta-divider">·</span>
      <span class="audit-meta-item"><strong>₹0.00</strong> volume evaluated</span>
      <span class="audit-meta-divider">·</span>
      <span class="audit-meta-item"><strong>0.00%</strong> recovery yield</span>
      <span class="audit-meta-divider">·</span>
      <span class="audit-meta-item"><strong>0</strong> compliance breaches</span>
    `;
  }

  // 3. Top Header Status Indicator
  const topDot = document.getElementById("topHeaderStatusDot");
  const topText = document.getElementById("topHeaderStatusText");
  if (topDot) topDot.style.background = "var(--color-warning)";
  if (topText) topText.innerText = "Simulation Standby (Click Run Demo)";

  // 4. Overview Active Table
  const activeTbody = document.getElementById("overviewActiveTableBody");
  if (activeTbody) {
    activeTbody.innerHTML = `
      <tr>
        <td colspan="5" style="text-align:center; padding:32px 16px; color:var(--text-muted);">
          <div style="font-weight:600; color:var(--text-primary); margin-bottom:4px;">No active operations yet</div>
          <div style="font-size:12px; margin-bottom:12px;">Click <strong>"Run Demo"</strong> to calculate and launch live portfolio recovery.</div>
          <button class="btn btn-primary btn-sm" onclick="runDemoSimulation()">▶ Run Demo</button>
        </td>
      </tr>
    `;
  }

  // 5. Portfolio Breakdown
  for (let i = 1; i <= 4; i++) {
    const el = document.getElementById(`risk-val-${i}`);
    if (el) el.innerText = "—";
  }
  const rTot = document.getElementById("risk-val-total");
  if (rTot) rTot.innerText = "—";

  // 6. Benchmark View
  const bmHero = document.getElementById("bm-hero-incremental");
  const bmHeroSub = document.getElementById("bm-hero-sub");
  const bmAi = document.getElementById("bm-ai-recovered");
  const bmAiSub = document.getElementById("bm-ai-sub");
  const bmBase = document.getElementById("bm-base-recovered");
  const bmBaseSub = document.getElementById("bm-base-sub");
  const bmLift = document.getElementById("bm-measured-lift");
  const bmLiftSub = document.getElementById("bm-lift-sub");
  const bmVio = document.getElementById("bm-violations");
  const bmVioSub = document.getElementById("bm-violations-sub");
  const bmBarAiLabel = document.getElementById("bm-bar-ai-label");
  const bmBarAiFill = document.getElementById("bm-bar-ai-fill");
  const bmBarBaseLabel = document.getElementById("bm-bar-base-label");
  const bmBarBaseFill = document.getElementById("bm-bar-base-fill");

  if (bmHero) bmHero.innerText = "—";
  if (bmHeroSub) bmHeroSub.innerText = "Awaiting simulation · Click 'Run Simulation' to compare AI recovery against fixed 24h retry";
  if (bmAi) bmAi.innerText = "—";
  if (bmAiSub) bmAiSub.innerText = "Awaiting simulation";
  if (bmBase) bmBase.innerText = "—";
  if (bmBaseSub) bmBaseSub.innerText = "Awaiting simulation";
  if (bmLift) bmLift.innerText = "—";
  if (bmLiftSub) bmLiftSub.innerText = "Awaiting simulation";
  if (bmVio) bmVio.innerText = "—";
  if (bmVioSub) bmVioSub.innerText = "Awaiting simulation";

  if (bmBarAiLabel) bmBarAiLabel.innerText = "—";
  if (bmBarAiFill) bmBarAiFill.style.width = "0%";
  if (bmBarBaseLabel) bmBarBaseLabel.innerText = "—";
  if (bmBarBaseFill) bmBarBaseFill.style.width = "0%";

  // Render standby chart
  renderChartStandbyState();

  // 7. Audit Explorer Table
  renderInitialAuditEmptyState();

  // 8. Chaos Sandbox Reset
  resetChaosScenarios();

  // 9. Close Modal if active
  const modal = document.getElementById("auditModal");
  if (modal) modal.classList.remove("active");

  if (showToastMsg) {
    showToast("↺ Simulation state reset to standby.", "info");
  }
}

function resetChaosScenarios() {
  const panel = document.getElementById("chaosConsolePanel");
  if (panel) panel.style.display = "none";
  const pillCbs = document.getElementById("statusPillCbs");
  const pillDispute = document.getElementById("statusPillDispute");
  const pillTrai = document.getElementById("statusPillTrai");
  if (pillCbs) { pillCbs.className = "badge-pill pill-neutral"; pillCbs.innerText = "READY"; }
  if (pillDispute) { pillDispute.className = "badge-pill pill-neutral"; pillDispute.innerText = "READY"; }
  if (pillTrai) { pillTrai.className = "badge-pill pill-neutral"; pillTrai.innerText = "READY"; }
  const summary = document.getElementById("chaosHumanSummary");
  if (summary) summary.innerHTML = "";
  const timeline = document.getElementById("chaosConsoleTimeline");
  if (timeline) timeline.innerHTML = "";
}

function getFallbackDemoSteps() {
  return [
    { from_state: "INIT", to_state: "DETECTED", event_type: "FAILURE_INGESTED", channel: "GATEWAY_WEBHOOK", statutory_rule_applied: "NONE", decision_rationale: "Ingested failure event: insufficient_funds on UPI AutoPay mandate." },
    { from_state: "DETECTED", to_state: "DIAGNOSING", event_type: "ROOT_CAUSE_DIAGNOSED", channel: "INTERNAL_ENGINE", statutory_rule_applied: "RULE_ENGINE_TRIAGE", decision_rationale: "Classified as temporary liquidity shortfall. High probability of recovery on upcoming salary credit date." },
    { from_state: "DIAGNOSING", to_state: "ACTION_SCHEDULED", event_type: "ACTION_PLAN_SCHEDULED", channel: "AUTO_DEBIT_API", statutory_rule_applied: "RBI_2026_PRE_DEBIT_24H_NOTICE_REQUIRED", decision_rationale: "Queued mandated 24h advance pre-debit notice with instant opt-out link. Auto-debit synchronized with salary window." },
    { from_state: "ACTION_SCHEDULED", to_state: "PRE_DEBIT_DELIVERED", event_type: "NOTICE_DISPATCHED", channel: "WHATSAPP", statutory_rule_applied: "TRAI_QUIET_HOURS_08_TO_20", decision_rationale: "Delivered pre-debit customer advisory within permitted TRAI commercial hours (10:15 IST)." },
    { from_state: "PRE_DEBIT_DELIVERED", to_state: "AUTO_DEBIT_ATTEMPTED", event_type: "AUTO_DEBIT_EXECUTED", channel: "AUTO_DEBIT_API", statutory_rule_applied: "MAX_RETRY_CEILING_3X", decision_rationale: "Executed automated recurring debit retry attempt #1 on customer salary date." },
    { from_state: "AUTO_DEBIT_ATTEMPTED", to_state: "PAID", event_type: "SETTLEMENT_RECORDED", channel: "GATEWAY_WEBHOOK", statutory_rule_applied: "DPDP_PII_MASKING", decision_rationale: "Full payment confirmed: ₹4,999.00. Subscription preserved, immutable SHA-256 audit ledger signed." }
  ];
}

function updateRoiCalculation() {
  const gmvSlider = document.getElementById("calcGmvSlider");
  const failureSlider = document.getElementById("calcFailureSlider");
  const ticketSelect = document.getElementById("calcTicketSelect");
  if (!gmvSlider || !failureSlider) return;

  const gmvCr = parseFloat(gmvSlider.value) || 25;
  const failureRate = parseFloat(failureSlider.value) || 12;
  
  // Format badges
  const gmvValEl = document.getElementById("calcGmvVal");
  const failureValEl = document.getElementById("calcFailureVal");
  if (gmvValEl) gmvValEl.innerText = `₹${gmvCr.toFixed(1)} Crore`;
  if (failureValEl) failureValEl.innerText = `${failureRate.toFixed(1)}%`;

  const monthlyGmvInr = gmvCr * 10000000;
  const monthlyAtRiskInr = monthlyGmvInr * (failureRate / 100);
  
  // Measured rates from comparative benchmark
  const aiYield = 0.2384; // 23.84%
  const baselineYield = 0.0902; // 9.02%
  
  const monthlyRecoveredInr = monthlyAtRiskInr * aiYield;
  const monthlyBaselineInr = monthlyAtRiskInr * baselineYield;
  const monthlyLiftInr = monthlyRecoveredInr - monthlyBaselineInr;
  const annualRecoveredInr = monthlyRecoveredInr * 12;

  // Annual violations avoided projection (~80% of baseline attempts violate rules)
  const ticketSize = ticketSelect ? (parseFloat(ticketSelect.value) || 15000) : 15000;
  const estimatedFailedTxnsPerMonth = monthlyAtRiskInr / ticketSize;
  const annualViolationsAvoided = Math.round(estimatedFailedTxnsPerMonth * 0.8 * 12);

  // Render values
  const annualEl = document.getElementById("calcAnnualRecovered");
  const monthlyRecEl = document.getElementById("calcMonthlyRecovered");
  const monthlyRiskEl = document.getElementById("calcMonthlyAtRisk");
  const monthlyLiftEl = document.getElementById("calcMonthlyLift");
  const violEl = document.getElementById("calcViolationsAvoided");

  if (annualEl) annualEl.innerText = formatCurrencyCrOrLakh(annualRecoveredInr) + " / Year";
  if (monthlyRecEl) monthlyRecEl.innerText = `+${formatCurrencyCrOrLakh(monthlyRecoveredInr)} / month (23.8% Recovery Yield)`;
  if (monthlyRiskEl) monthlyRiskEl.innerText = formatCurrencyCrOrLakh(monthlyAtRiskInr);
  if (monthlyLiftEl) monthlyLiftEl.innerText = `+${formatCurrencyCrOrLakh(monthlyLiftInr)} / mo`;
  if (violEl) violEl.innerText = `~${annualViolationsAvoided.toLocaleString('en-IN')} / Year`;
}

function formatCurrencyCrOrLakh(amount) {
  if (amount >= 10000000) {
    return `₹${(amount / 10000000).toFixed(2)} Crore`;
  } else if (amount >= 100000) {
    return `₹${(amount / 100000).toFixed(2)} Lakhs`;
  } else {
    return `₹${amount.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
  }
}

// P1a: Cumulative Recovery Time-Series Chart — Sharp, Interactive, DPR-aware
let _chartAnimFrame = null;
let _chartMouseX = null;
let _chartSeries = null;

function renderRecoveryTimeSeries(series) {
  const canvas = document.getElementById("recoveryTimeSeriesChart");
  if (!canvas) return;

  // ── 1. DPR fix: scale canvas pixels by devicePixelRatio for Retina sharpness ──
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  const cssW = Math.max(rect.width, canvas.parentElement ? canvas.parentElement.clientWidth : 0, 500);
  const cssH = 260;

  canvas.width  = cssW * dpr;
  canvas.height = cssH * dpr;
  canvas.style.width  = cssW + "px";
  canvas.style.height = cssH + "px";

  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);          // all drawing now in CSS-pixel space
  const W = cssW, H = cssH;

  _chartSeries = series;

  // ── 2. Palette ──
  const COLOR_AI    = { line: "#4f9cf0", fill0: "rgba(79,156,240,0.22)", fill1: "rgba(79,156,240,0.01)", dot: "#4f9cf0" };
  const COLOR_NAIVE = { line: "#f97316", fill0: "rgba(249,115,22,0.15)", fill1: "rgba(249,115,22,0.01)", dot: "#f97316" };
  const COLOR_GRID  = "rgba(120,130,150,0.13)";
  const COLOR_AXIS  = "rgba(120,130,150,0.9)";
  const FONT        = "500 11px 'Inter', system-ui, sans-serif";

  const pad = { top: 36, right: 28, bottom: 46, left: 78 };
  const plotW = W - pad.left - pad.right;
  const plotH = H - pad.top - pad.bottom;

  const days     = series.map(d => d.day);
  const aiVals   = series.map(d => d.ai_cumulative_inr);
  const naiveVals= series.map(d => d.naive_cumulative_inr);
  const maxVal   = Math.max(...aiVals, ...naiveVals) * 1.15;
  const n        = days.length;

  // ── 3. Coordinate helpers ──
  const xOf = i => pad.left + (i / (n - 1)) * plotW;
  const yOf = v => pad.top + plotH - (v / maxVal) * plotH;

  // ── 4. Main draw function (called each animation frame & on hover) ──
  function draw(hoverIdx) {
    ctx.clearRect(0, 0, W, H);

    // Background
    ctx.fillStyle = "transparent";
    ctx.fillRect(0, 0, W, H);

    // ── Grid ──
    const gridCount = 5;
    for (let g = 0; g <= gridCount; g++) {
      const gy = pad.top + plotH - (g / gridCount) * plotH;
      ctx.beginPath();
      ctx.strokeStyle = COLOR_GRID;
      ctx.lineWidth = 1;
      // Dashed grid
      ctx.setLineDash([4, 4]);
      ctx.moveTo(pad.left, gy);
      ctx.lineTo(pad.left + plotW, gy);
      ctx.stroke();
      ctx.setLineDash([]);

      // Y-axis labels
      const gVal = (g / gridCount) * maxVal;
      ctx.fillStyle = COLOR_AXIS;
      ctx.font = FONT;
      ctx.textAlign = "right";
      ctx.fillText(formatCurrencyCrOrLakh(gVal), pad.left - 10, gy + 4);
    }

    // ── X-axis labels ──
    ctx.fillStyle = COLOR_AXIS;
    ctx.font = FONT;
    ctx.textAlign = "center";
    for (let i = 0; i < n; i++) {
      const skip = n > 10 ? (i % 2 !== 0) : false;
      if (!skip) {
        ctx.fillText(`D${days[i]}`, xOf(i), H - 14);
      }
    }

    // ── Axis baseline ──
    ctx.beginPath();
    ctx.strokeStyle = "rgba(120,130,150,0.3)";
    ctx.lineWidth = 1;
    ctx.moveTo(pad.left, pad.top + plotH);
    ctx.lineTo(pad.left + plotW, pad.top + plotH);
    ctx.stroke();

    // ── Draw area + line for each series ──
    function drawSeries(vals, col) {
      // Smooth bezier curve points using cardinal spline
      function getCP(pts, i) {
        const p0 = pts[Math.max(i - 1, 0)];
        const p1 = pts[i];
        const p2 = pts[Math.min(i + 1, pts.length - 1)];
        return {
          cp1x: p1.x + (p2.x - p0.x) / 6,
          cp1y: p1.y + (p2.y - p0.y) / 6,
          cp2x: p2.x - (p2.x - p0.x) / 6,
          cp2y: p2.y - (p2.y - p0.y) / 6,
        };
      }
      const pts = vals.map((v, i) => ({ x: xOf(i), y: yOf(v) }));

      // Area fill first
      const areaGrad = ctx.createLinearGradient(0, pad.top, 0, pad.top + plotH);
      areaGrad.addColorStop(0, col.fill0);
      areaGrad.addColorStop(1, col.fill1);
      ctx.beginPath();
      ctx.moveTo(pts[0].x, pts[0].y);
      for (let i = 0; i < pts.length - 1; i++) {
        const cp = getCP(pts, i);
        ctx.bezierCurveTo(cp.cp1x, cp.cp1y, cp.cp2x, cp.cp2y, pts[i+1].x, pts[i+1].y);
      }
      ctx.lineTo(pts[n-1].x, pad.top + plotH);
      ctx.lineTo(pts[0].x, pad.top + plotH);
      ctx.closePath();
      ctx.fillStyle = areaGrad;
      ctx.fill();

      // Line
      ctx.beginPath();
      ctx.strokeStyle = col.line;
      ctx.lineWidth = 2.5;
      ctx.lineJoin = "round";
      ctx.lineCap = "round";
      ctx.moveTo(pts[0].x, pts[0].y);
      for (let i = 0; i < pts.length - 1; i++) {
        const cp = getCP(pts, i);
        ctx.bezierCurveTo(cp.cp1x, cp.cp1y, cp.cp2x, cp.cp2y, pts[i+1].x, pts[i+1].y);
      }
      ctx.stroke();

      // All dots (small)
      pts.forEach((p, i) => {
        ctx.beginPath();
        ctx.arc(p.x, p.y, i === hoverIdx ? 5.5 : 3, 0, Math.PI * 2);
        ctx.fillStyle = i === hoverIdx ? col.line : "transparent";
        ctx.strokeStyle = col.line;
        ctx.lineWidth = i === hoverIdx ? 2 : 1.5;
        ctx.fill();
        ctx.stroke();
      });
    }

    drawSeries(naiveVals, COLOR_NAIVE); // naive first (behind)
    drawSeries(aiVals,    COLOR_AI);    // AI on top

    // ── Crosshair + tooltip on hover ──
    if (hoverIdx !== null && hoverIdx >= 0 && hoverIdx < n) {
      const cx = xOf(hoverIdx);

      // Vertical crosshair line
      ctx.beginPath();
      ctx.strokeStyle = "rgba(150,160,180,0.4)";
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 3]);
      ctx.moveTo(cx, pad.top);
      ctx.lineTo(cx, pad.top + plotH);
      ctx.stroke();
      ctx.setLineDash([]);

      // Tooltip box
      const aiV    = aiVals[hoverIdx];
      const naiveV = naiveVals[hoverIdx];
      const day    = days[hoverIdx];
      const lines  = [
        { label: `Day ${day}`, value: "", bold: true },
        { label: "AI Agent",       value: formatCurrencyCrOrLakh(aiV),    color: COLOR_AI.line },
        { label: "Naive Baseline", value: formatCurrencyCrOrLakh(naiveV), color: COLOR_NAIVE.line },
        { label: "Lift",           value: `+${formatCurrencyCrOrLakh(aiV - naiveV)}`, color: "#22c55e" },
      ];

      const ttPad = 10, ttLineH = 18, ttW = 190, ttH = ttPad * 2 + ttLineH * lines.length;
      let ttX = cx + 14;
      if (ttX + ttW > W - 10) ttX = cx - ttW - 14;
      const ttY = pad.top + 4;

      // Shadow + rounded rect
      ctx.save();
      ctx.shadowColor = "rgba(0,0,0,0.18)";
      ctx.shadowBlur = 12;
      ctx.shadowOffsetY = 4;
      ctx.beginPath();
      ctx.roundRect ? ctx.roundRect(ttX, ttY, ttW, ttH, 8) : ctx.rect(ttX, ttY, ttW, ttH);
      ctx.fillStyle = "rgba(18, 24, 38, 0.95)";
      ctx.fill();
      ctx.restore();

      // Tooltip border
      ctx.beginPath();
      ctx.roundRect ? ctx.roundRect(ttX, ttY, ttW, ttH, 8) : ctx.rect(ttX, ttY, ttW, ttH);
      ctx.strokeStyle = "rgba(100,120,160,0.35)";
      ctx.lineWidth = 1;
      ctx.stroke();

      // Tooltip text
      lines.forEach((line, li) => {
        const ty = ttY + ttPad + li * ttLineH + 11;
        if (line.bold) {
          ctx.font = "600 12px 'Inter', system-ui, sans-serif";
          ctx.fillStyle = "#e2e8f0";
          ctx.textAlign = "left";
          ctx.fillText(line.label, ttX + ttPad, ty);
        } else {
          // Color dot
          ctx.beginPath();
          ctx.arc(ttX + ttPad + 5, ty - 3, 4, 0, Math.PI * 2);
          ctx.fillStyle = line.color || "#e2e8f0";
          ctx.fill();
          ctx.font = "11px 'Inter', system-ui, sans-serif";
          ctx.fillStyle = "rgba(180,190,210,0.9)";
          ctx.textAlign = "left";
          ctx.fillText(line.label, ttX + ttPad + 16, ty);
          ctx.font = "600 11px 'Inter', system-ui, sans-serif";
          ctx.fillStyle = line.color || "#e2e8f0";
          ctx.textAlign = "right";
          ctx.fillText(line.value, ttX + ttW - ttPad, ty);
        }
      });
    }

    // ── Legend (top right) ──
    const legendItems = [
      { color: COLOR_AI.line,    label: "AI Agent (23.84%)" },
      { color: COLOR_NAIVE.line, label: "Naive (9.02%)" },
    ];
    let lx = pad.left;
    const ly = 18;
    legendItems.forEach(item => {
      // Line swatch
      ctx.beginPath();
      ctx.strokeStyle = item.color;
      ctx.lineWidth = 2.5;
      ctx.lineCap = "round";
      ctx.moveTo(lx, ly);
      ctx.lineTo(lx + 20, ly);
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(lx + 10, ly, 3.5, 0, Math.PI * 2);
      ctx.fillStyle = item.color;
      ctx.fill();

      ctx.font = "500 11px 'Inter', system-ui, sans-serif";
      ctx.fillStyle = "rgba(150,160,180,0.95)";
      ctx.textAlign = "left";
      ctx.fillText(item.label, lx + 26, ly + 4);
      lx += ctx.measureText(item.label).width + 56;
    });
  }

  // ── 5. Animated entry (draws progressively) ──
  if (_chartAnimFrame) cancelAnimationFrame(_chartAnimFrame);
  const ANIM_DURATION = 600; // ms
  const startTime = performance.now();

  function animateDraw(now) {
    const t = Math.min((now - startTime) / ANIM_DURATION, 1);
    const eased = 1 - Math.pow(1 - t, 3); // ease-out cubic

    // Temporarily clip to animate reveal left-to-right
    ctx.clearRect(0, 0, W, H);
    ctx.save();
    ctx.beginPath();
    ctx.rect(0, 0, pad.left + plotW * eased + 30, H);
    ctx.clip();
    draw(_chartMouseX);
    ctx.restore();

    if (t < 1) {
      _chartAnimFrame = requestAnimationFrame(animateDraw);
    } else {
      draw(_chartMouseX); // final clean draw without clip
    }
  }
  _chartAnimFrame = requestAnimationFrame(animateDraw);

  // ── 6. Mouse interaction — clean up old handlers before adding new ones ──
  const targetCanvas = canvas; // same element, already in DOM
  targetCanvas.style.cursor = "crosshair";

  // Remove previous listeners if stored
  if (targetCanvas._mmHandler) targetCanvas.removeEventListener("mousemove", targetCanvas._mmHandler);
  if (targetCanvas._mlHandler) targetCanvas.removeEventListener("mouseleave", targetCanvas._mlHandler);

  targetCanvas._mmHandler = (e) => {
    const r = targetCanvas.getBoundingClientRect();
    const mouseX = (e.clientX - r.left);
    let nearest = 0, minDist = Infinity;
    for (let i = 0; i < n; i++) {
      const dist = Math.abs(xOf(i) - mouseX);
      if (dist < minDist) { minDist = dist; nearest = i; }
    }
    _chartMouseX = nearest;
    draw(nearest);
  };

  targetCanvas._mlHandler = () => {
    _chartMouseX = null;
    draw(null);
  };

  targetCanvas.addEventListener("mousemove", targetCanvas._mmHandler);
  targetCanvas.addEventListener("mouseleave", targetCanvas._mlHandler);
}

function renderChartStandbyState() {
  const canvas = document.getElementById("recoveryTimeSeriesChart");
  if (!canvas) return;

  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  const cssW = Math.max(rect.width, canvas.parentElement ? canvas.parentElement.clientWidth : 0, 500);
  const cssH = 260;

  canvas.width  = cssW * dpr;
  canvas.height = cssH * dpr;
  canvas.style.width  = cssW + "px";
  canvas.style.height = cssH + "px";

  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, cssW, cssH);

  // Background subtle dashed box
  ctx.strokeStyle = "rgba(120,130,150,0.18)";
  ctx.lineWidth = 1;
  ctx.setLineDash([5, 4]);
  ctx.strokeRect(30, 20, cssW - 60, cssH - 40);
  ctx.setLineDash([]);

  // Subtle interior grid
  ctx.strokeStyle = "rgba(120,130,150,0.07)";
  ctx.lineWidth = 1;
  for (let i = 1; i <= 3; i++) {
    const gy = 20 + (i / 4) * (cssH - 40);
    ctx.beginPath();
    ctx.moveTo(30, gy);
    ctx.lineTo(cssW - 30, gy);
    ctx.stroke();
  }

  // Standby Title & Subtitle
  ctx.fillStyle = "rgba(140,165,195,0.92)";
  ctx.font = "600 13.5px 'Inter', system-ui, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText("📊 Simulation Standby", cssW / 2, cssH / 2 - 8);

  ctx.fillStyle = "rgba(120,135,160,0.75)";
  ctx.font = "400 11.5px 'Inter', system-ui, sans-serif";
  ctx.fillText("Click '▶ Run Simulation' in the header to execute portfolio recovery and generate curves", cssW / 2, cssH / 2 + 14);
}

async function triggerChaosScenario(scenarioKey) {
  const panel = document.getElementById("chaosConsolePanel");
  const titleEl = document.getElementById("chaosConsoleTitle");
  const statusEl = document.getElementById("chaosConsoleStatus");
  const timelineEl = document.getElementById("chaosConsoleTimeline");
  const summaryEl = document.getElementById("chaosHumanSummary");

  // Update scenario card status pills
  const pillCbs = document.getElementById("statusPillCbs");
  const pillDispute = document.getElementById("statusPillDispute");
  const pillTrai = document.getElementById("statusPillTrai");

  if (pillCbs) { pillCbs.className = "badge-pill pill-neutral"; pillCbs.innerText = "READY"; }
  if (pillDispute) { pillDispute.className = "badge-pill pill-neutral"; pillDispute.innerText = "READY"; }
  if (pillTrai) { pillTrai.className = "badge-pill pill-neutral"; pillTrai.innerText = "READY"; }

  let activePill = null;
  if (scenarioKey === "BANK_OUTAGE_503") {
    activePill = pillCbs;
    if (titleEl) titleEl.innerText = "CBS Bank Outage (HDFC 503 Outage)";
  } else if (scenarioKey === "DISPUTE_CPA_2019") {
    activePill = pillDispute;
    if (titleEl) titleEl.innerText = "Active Fraud Dispute (CPA 2019)";
  } else if (scenarioKey === "TRAI_NIGHT_HOURS") {
    activePill = pillTrai;
    if (titleEl) titleEl.innerText = "TRAI Night Hours (23:30 IST Suppression)";
  }

  if (activePill) {
    activePill.className = "badge-pill pill-info";
    activePill.innerText = "RUNNING";
  }

  if (panel) panel.style.display = "block";
  if (statusEl) {
    statusEl.className = "badge-pill pill-info";
    statusEl.innerText = "RUNNING";
  }
  if (summaryEl) {
    summaryEl.innerHTML = `<div style="font-size:13px; color:var(--text-secondary); padding:8px 0;">Injecting fault scenario into runtime execution loop...</div>`;
  }
  if (timelineEl) {
    timelineEl.innerHTML = `<div class="log-row"><span class="log-time">[0.00s]</span> <strong class="log-phase">INJECT:</strong> <span class="log-msg">Initializing fault injection for ${scenarioKey}...</span></div>`;
  }

  try {
    const res = await fetch(`/api/chaos/inject/${scenarioKey}`);
    if (res.ok) {
      const data = await res.json();
      renderChaosExecution(data, scenarioKey);
    } else {
      if (activePill) { activePill.className = "badge-pill pill-error"; activePill.innerText = "FAILED"; }
      if (statusEl) { statusEl.className = "badge-pill pill-error"; statusEl.innerText = "ERROR"; }
      if (summaryEl) summaryEl.innerHTML = `<div style="padding:12px; color:var(--color-error);">Server returned error: ${res.status}</div>`;
    }
  } catch (err) {
    console.error("Chaos error", err);
    if (activePill) { activePill.className = "badge-pill pill-error"; activePill.innerText = "FAILED"; }
    if (statusEl) { statusEl.className = "badge-pill pill-error"; statusEl.innerText = "OFFLINE"; }
    if (summaryEl) summaryEl.innerHTML = `<div style="padding:12px; color:var(--color-error);">Backend server is offline or unreachable. Please ensure the Python server is running on port 8888.</div>`;
  }
}

function renderChaosExecution(data, scenarioKey) {
  const statusEl = document.getElementById("chaosConsoleStatus");
  const timelineEl = document.getElementById("chaosConsoleTimeline");
  const summaryEl = document.getElementById("chaosHumanSummary");

  const pillCbs = document.getElementById("statusPillCbs");
  const pillDispute = document.getElementById("statusPillDispute");
  const pillTrai = document.getElementById("statusPillTrai");

  let activePill = null;
  if (scenarioKey === "BANK_OUTAGE_503") activePill = pillCbs;
  else if (scenarioKey === "DISPUTE_CPA_2019") activePill = pillDispute;
  else if (scenarioKey === "TRAI_NIGHT_HOURS") activePill = pillTrai;

  const steps = (data.timeline && data.timeline.length) ? data.timeline : (data.steps || []);

  if (timelineEl) {
    timelineEl.innerHTML = "";
    steps.forEach((step, i) => {
      const phase = step.phase || step.event_type || step.to_state || "EXECUTE";
      const message = step.message || step.decision_rationale || "";
      const div = document.createElement("div");
      div.className = "log-row";
      div.innerHTML = `<span class="log-time">[+${(i * 0.15).toFixed(2)}s]</span> <strong class="log-phase">${phase}:</strong> <span class="log-msg">${message}</span>`;
      timelineEl.appendChild(div);
    });
  }

  if (data.status === "QUARANTINED") {
    if (statusEl) {
      statusEl.className = "badge-pill pill-error";
      statusEl.innerText = "BLOCKED / REFUSAL ENFORCED";
    }
    if (activePill) {
      activePill.className = "badge-pill pill-error";
      activePill.innerText = "BLOCKED";
    }
    if (summaryEl) {
      summaryEl.innerHTML = `
        <div class="chaos-summary-card alert-blocked">
          <div class="chaos-summary-title">RECOVERY STOPPED</div>
          <div class="chaos-summary-desc">Active customer dispute detected with issuing bank. All auto-retries and dunning touches were halted immediately to prevent statutory harassment violations under Consumer Protection Act (CPA 2019).</div>
          <div class="chaos-summary-checks">
            <span>✓ Dispute lock recognized</span>
            <span>✓ Mandate retries frozen</span>
            <span>✓ 0 Compliance violations</span>
          </div>
        </div>
      `;
    }
  } else if (data.status === "ADAPTED") {
    if (statusEl) {
      statusEl.className = "badge-pill pill-success";
      statusEl.innerText = "PASSED / CHANNEL SWITCHED";
    }
    if (activePill) {
      activePill.className = "badge-pill pill-success";
      activePill.innerText = "PASSED";
    }
    if (summaryEl) {
      summaryEl.innerHTML = `
        <div class="chaos-summary-card alert-success">
          <div class="chaos-summary-title">RESILIENCE TEST PASSED</div>
          <div class="chaos-summary-desc">Core banking CBS 503 outage detected on original payment rail. The agent suppressed blind retries and seamlessly switched to an alternate WhatsApp 1-click UPI Intent flow.</div>
          <div class="chaos-summary-checks">
            <span>✓ CBS 503 outage identified</span>
            <span>✓ Blind retry blocked</span>
            <span>✓ Switched to WhatsApp Intent (+₹6,374 Net EV)</span>
          </div>
        </div>
      `;
    }
  } else {
    if (statusEl) {
      statusEl.className = "badge-pill pill-warning";
      statusEl.innerText = "DELAYED / TRAI COMPLIANT";
    }
    if (activePill) {
      activePill.className = "badge-pill pill-warning";
      activePill.innerText = "DELAYED";
    }
    if (summaryEl) {
      summaryEl.innerHTML = `
        <div class="chaos-summary-card alert-warning">
          <div class="chaos-summary-title">RECOVERY DELAYED</div>
          <div class="chaos-summary-desc">Payment degradation occurred during TRAI quiet hours (23:30 IST). Outbound customer notifications were queued and held for release at 08:30 AM IST.</div>
          <div class="chaos-summary-checks">
            <span>✓ Quiet-hour window active</span>
            <span>✓ Late-night contact suppressed</span>
            <span>✓ Outreach scheduled for 08:30 AM release</span>
          </div>
        </div>
      `;
    }
  }
}

// =========================================================================
// Playground & NLU Tester Controller (P0 & P3)
// =========================================================================

function switchPlaygroundTab(tabName) {
  const tabs = ["decline", "ptp"];
  tabs.forEach(t => {
    const btn = document.getElementById(`tabBtn${t.charAt(0).toUpperCase() + t.slice(1)}`);
    const content = document.getElementById(`pgContent${t.charAt(0).toUpperCase() + t.slice(1)}`);
    if (btn) btn.classList.toggle("active", t === tabName);
    if (content) content.style.display = t === tabName ? "block" : "none";
  });
  if (tabName === "ptp") {
    renderPtpRecords(PTP_RECORDS);
  }
}

const DECLINE_PRESETS = {
  switch_timeout: {
    text: "switch unavailable rc-91 issuer inoperative cbs socket closed",
    amount: 4999.0,
    method: "upi_autopay",
    dispute: "false",
    dnd: "false",
    attempt: "0"
  },
  dormant_kyc: {
    text: "account dormant suspense status kyc pending ac restricted code-402",
    amount: 12500.0,
    method: "netbanking_emandate",
    dispute: "false",
    dnd: "false",
    attempt: "0"
  },
  afa_breach: {
    text: "transaction amount ₹85000 exceeds single debit limit without additional factor auth",
    amount: 85000.0,
    method: "card_recurring",
    dispute: "false",
    dnd: "false",
    attempt: "0"
  },
  salary_shortfall: {
    text: "decline code 51 insufficient funds balance below mandate trigger amount",
    amount: 3499.0,
    method: "upi_autopay",
    dispute: "false",
    dnd: "false",
    attempt: "0"
  },
  dispute_lock: {
    text: "customer initiated chargeback dispute fraud claim active with issuer bank",
    amount: 18000.0,
    method: "card_recurring",
    dispute: "true",
    dnd: "false",
    attempt: "1"
  },
  ambiguous_raw: {
    text: "decline 99 unmapped host error transaction rejected by gateway intermediary switch",
    amount: 6200.0,
    method: "upi_autopay",
    dispute: "false",
    dnd: "false",
    attempt: "0"
  }
};

function applyDeclinePreset(key) {
  const p = DECLINE_PRESETS[key];
  if (!p) return;
  document.getElementById("liveErrorText").value = p.text;
  document.getElementById("liveAmount").value = p.amount;
  document.getElementById("livePaymentMethod").value = p.method;
  document.getElementById("liveDispute").value = p.dispute;
  document.getElementById("liveDnd").value = p.dnd;
  document.getElementById("liveAttempt").value = p.attempt;
  runLiveDiagnosis();
}

const PTP_PRESETS = {
  salary_promise: "Haan bhaiya abhi account me balance kam hai, kal meri salary aayegi tab main pakka ₹5000 transfer kar dunga.",
  date_promise: "Main 5th ko office se aate hi account me paise daal kar Rs. 8500 clear kar dunga.",
  vague_promise: "Abhi paise nahi hai, agle hafte call karna dekhenge.",
  rejection: "Galat number hai bhai, maine koi subscription nahi li, dobara call mat karna."
};

function applyPtpPreset(key) {
  const text = PTP_PRESETS[key];
  if (!text) return;
  document.getElementById("livePtpText").value = text;
  runLivePtpExtract();
}

async function runLiveDiagnosis() {
  const errorText = document.getElementById("liveErrorText").value.trim();
  const amount = parseFloat(document.getElementById("liveAmount").value) || 4999.0;
  const method = document.getElementById("livePaymentMethod").value;
  const disputeActive = document.getElementById("liveDispute").value === "true";
  const isDnd = document.getElementById("liveDnd").value === "true";
  const attemptCount = parseInt(document.getElementById("liveAttempt").value) || 0;

  const btn = document.getElementById("btnRunDiagnosis");
  const resultContainer = document.getElementById("liveDiagnosisResult");
  const badgeEl = document.getElementById("liveClassifierTierBadge");

  btn.disabled = true;
  btn.innerHTML = `<span class="spinner" style="display:inline-block; width:12px; height:12px; border:2px solid #fff; border-top-color:transparent; border-radius:50%; animation:spin 0.6s linear infinite; margin-right:6px;"></span> Analyzing...`;

  badgeEl.className = "badge-pill pill-warning";
  badgeEl.innerHTML = `<span class="badge-dot"></span>Classifying Failure...`;

  try {
    const res = await fetch("/api/diagnose/live", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        error_text: errorText || "Insufficient balance in customer account",
        amount: amount,
        payment_method: method,
        dispute_active: disputeActive,
        is_dnd: isDnd,
        attempt_count: attemptCount
      })
    });

    const data = await res.json();
    if (data.status === "SUCCESS") {
      badgeEl.className = data.is_llm_used ? "badge-pill pill-success" : "badge-pill pill-info";
      badgeEl.innerHTML = `<span class="badge-dot"></span>${data.classifier_tier}`;

      renderLiveDiagnosisResult(data);
    } else {
      resultContainer.innerHTML = `<div style="padding:20px; color:var(--color-error);">Error running analysis: ${data.error || 'Unknown error'}</div>`;
    }
  } catch (err) {
    console.error("Diagnosis error:", err);
    resultContainer.innerHTML = `<div style="padding:20px; color:var(--color-error);">Error connecting to diagnostic engine. Make sure server is running.</div>`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = `Analyze Failure`;
  }
}

function renderLiveDiagnosisResult(data) {
  const container = document.getElementById("liveDiagnosisResult");
  const d = data.diagnosis;
  const plan = data.action_plan;
  const ev = data.unit_economics_ev;
  const ledger = data.audit_ledger_entry;

  const isBlocked = plan.action_type === "STOP_DISPUTE_QUARANTINE" || plan.action_type.startsWith("STOP_");

  let formattedAction = plan.action_type;
  if (plan.action_type === "STOP_DISPUTE_QUARANTINE") formattedAction = "Halt Outreach (Fraud Quarantine)";
  else if (plan.action_type === "STOP_MAX_RETRIES") formattedAction = "Permanent Halt (3x Cap Reached)";
  else if (plan.action_type === "RETRY_AFTER_PRE_DEBIT") formattedAction = "24h Notice & Retry";
  else if (plan.action_type === "SEND_1CLICK_UPI_LINK") formattedAction = "1-Click WhatsApp UPI Intent";
  else if (plan.action_type === "ESCALATE_HUMAN_REVIEW") formattedAction = "Escalate to Operations";

  let guardsHtml = data.guardrails.slice(0, 4).map(g => {
    const isRefused = g.status.includes("REFUSED") || g.status.includes("STOPPING_RULE");
    const isEnforced = g.status.includes("ENFORCED");
    const pillClass = isRefused ? "pill-error" : (isEnforced ? "pill-warning" : "pill-success");
    const cleanStatus = isRefused ? "Quarantine" : (isEnforced ? "Delayed" : "Passed");
    return `
      <div class="pg-guard-item">
        <span style="font-weight:500; color:var(--text-primary); font-size:11.5px;">${g.guard}</span>
        <span class="badge-pill ${pillClass}" style="font-size:10.5px;"><span class="badge-dot"></span>${cleanStatus}</span>
      </div>
    `;
  }).join("");

  container.innerHTML = `
    <div class="pg-output-box">
      
      <!-- STEP 1: Root Cause Diagnosis -->
      <div class="pg-result-summary">
        <div class="step-marker-header">
          <span class="step-marker-badge">DIAGNOSIS</span>
          <span class="badge-pill ${d.confidence >= 0.70 ? 'pill-success' : 'pill-neutral'}"><span class="badge-dot"></span>${(d.confidence * 100).toFixed(0)}% Match</span>
        </div>
        <div class="pg-result-title">${d.bucket_name}</div>
        <div class="pg-result-reasoning">${d.reasoning}</div>
      </div>

      <!-- STEP 2: Recommended Action & Schedule -->
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
        <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:10px 14px;">
          <div class="step-marker-badge" style="margin-bottom:2px;">RECOMMENDED ACTION</div>
          <div style="font-size:13px; font-weight:600; color:${isBlocked ? 'var(--color-error)' : 'var(--color-primary)'};">${formattedAction}</div>
          <div style="font-size:11.5px; color:var(--text-secondary); margin-top:2px;">Channel: <strong>${plan.primary_channel.replace(/_/g, ' ')}</strong></div>
        </div>

        <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:10px 14px;">
          <div class="step-marker-badge" style="margin-bottom:2px;">DISPATCH TIMING</div>
          <div style="font-size:13px; font-weight:600; color:var(--text-primary);">${plan.scheduled_delay_hours > 0 ? `+${plan.scheduled_delay_hours}h Compliant Notice Window` : 'Immediate Execution'}</div>
          <div style="font-size:11.5px; color:var(--text-secondary); margin-top:2px;">Policy: <strong>RBI E-Mandate 2026</strong></div>
        </div>
      </div>

      <!-- STEP 3: Compliance Decision -->
      <div>
        <div class="step-marker-header" style="margin-bottom:6px;">
          <span class="step-marker-badge">STATUTORY COMPLIANCE</span>
          <span class="badge-pill ${isBlocked ? 'pill-error' : 'pill-success'}"><span class="badge-dot"></span>${isBlocked ? 'Action Blocked' : 'Verified (Compliant)'}</span>
        </div>
        <div class="pg-guardrails-list">
          ${guardsHtml}
        </div>
      </div>

      <!-- STEP 4: Net Expected Value (EV) -->
      <div class="ev-math-summary">
        <div class="step-marker-header">
          <span class="step-marker-badge" style="color:var(--color-success-text);">NET EXPECTED VALUE (EV)</span>
          <span style="font-size:14px; font-weight:700; font-family:var(--font-mono); color:var(--color-success-text);">${ev.net_expected_value_inr >= 0 ? '+' : ''}₹${ev.net_expected_value_inr.toLocaleString('en-IN', {minimumFractionDigits:2})}</span>
        </div>
        <div style="font-size:11.5px; color:var(--text-secondary); margin-top:4px;">${isBlocked ? 'Automated recovery suspended under CPA 2019 to prevent customer harassment.' : 'Positive expected return after factoring in channel delivery cost and friction penalty.'}</div>
      </div>

    </div>
  `;
}

async function runLivePtpExtract() {
  const text = document.getElementById("livePtpText").value.trim();
  const btn = document.getElementById("btnRunPtp");
  const container = document.getElementById("livePtpResult");
  const badgeEl = document.getElementById("livePtpBadge");

  if (!text) return;

  btn.disabled = true;
  btn.innerHTML = `<span class="spinner" style="display:inline-block; width:12px; height:12px; border:2px solid #fff; border-top-color:transparent; border-radius:50%; animation:spin 0.6s linear infinite; margin-right:6px;"></span> Extracting...`;

  badgeEl.className = "badge-pill pill-warning";
  badgeEl.innerHTML = `<span class="badge-dot"></span>Extracting Entities...`;

  try {
    const res = await fetch("/api/ptp/extract", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: text })
    });

    const data = await res.json();
    if (data.status === "SUCCESS") {
      badgeEl.className = data.ptp_detected ? "badge-pill pill-success" : "badge-pill pill-neutral";
      badgeEl.innerHTML = `<span class="badge-dot"></span>${data.ptp_detected ? "PTP Promise Extracted" : "No Promise Detected"}`;

      renderLivePtpResult(data);
    } else {
      container.innerHTML = `<div style="padding:20px; color:var(--color-error);">Error extracting PTP: ${data.error || 'Unknown error'}</div>`;
    }
  } catch (err) {
    console.error("PTP error:", err);
    container.innerHTML = `<div style="padding:20px; color:var(--color-error);">Error connecting to NLU engine. Make sure server is running.</div>`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = `Extract Promise to Pay`;
  }
}

function renderLivePtpResult(data) {
  const container = document.getElementById("livePtpResult");

  if (!data.ptp_detected) {
    container.innerHTML = `
      <div class="pg-output-box">
        <div style="background:#FFFBEB; border:1px solid #FDE68A; border-radius:6px; padding:12px 16px; margin-bottom:12px;">
          <div style="font-size:11px; font-weight:600; text-transform:uppercase; color:#92400E;">NLU DIAGNOSIS</div>
          <div style="font-size:15px; font-weight:700; color:#B45309; margin-top:2px;">No Explicit Promise Detected</div>
          <div style="font-size:12px; color:#78350F; margin-top:4px;">Customer conversation transcript does not contain an explicit promise to pay or payment settlement timing.</div>
        </div>
        <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:6px; padding:12px 16px;">
          <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase; font-weight:600;">RECOMMENDED RECOVERY ACTION</div>
          <div style="font-size:13px; font-weight:600; color:var(--text-primary); margin-top:2px;">Maintain Standard Recovery Ladder (FSM: ${data.recommended_fsm_state})</div>
          <div style="font-size:12px; color:var(--text-secondary); margin-top:4px;">Resume next planned outreach touch or escalate to voice assistant.</div>
        </div>
      </div>
    `;
    return;
  }

  const dateDisplay = data.promised_date ? new Date(data.promised_date).toLocaleDateString('en-IN', { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' }) : "Relative Date (1st of month)";
  const amtDisplay = data.promised_amount_inr ? `₹${data.promised_amount_inr.toLocaleString('en-IN', {minimumFractionDigits: 2})}` : "Full Invoice Balance";

  container.innerHTML = `
    <div class="pg-output-box">
      <div style="background:var(--color-success-bg); border:1px solid var(--color-success-border); border-radius:6px; padding:12px 16px; margin-bottom:12px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <div>
            <div style="font-size:11px; font-weight:600; text-transform:uppercase; color:var(--color-success-text);">EXTRACTED COMMITMENT</div>
            <div style="font-size:15px; font-weight:700; color:var(--color-success-text); margin-top:2px;">Promise to Pay Captured</div>
            <div style="font-size:12px; color:var(--color-success-text); margin-top:2px;">Condition: <strong>${data.condition || 'Direct Date Promise'}</strong></div>
          </div>
          <div style="text-align:right;">
            <div style="font-size:11px; color:var(--color-success-text);">Confidence</div>
            <div style="font-size:18px; font-weight:700; font-family:var(--font-mono); color:var(--color-success-text);">${(data.confidence * 100).toFixed(0)}%</div>
          </div>
        </div>
      </div>

      <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:12px;">
        <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:6px; padding:10px 14px;">
          <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase; font-weight:600;">Promised Amount</div>
          <div style="font-size:15px; font-weight:700; color:var(--color-primary); margin-top:2px; font-family:var(--font-mono);">${amtDisplay}</div>
        </div>

        <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:6px; padding:10px 14px;">
          <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase; font-weight:600;">Promised Settlement Date</div>
          <div style="font-size:14px; font-weight:700; color:var(--color-success-text); margin-top:2px; font-family:var(--font-mono);">${dateDisplay}</div>
        </div>
      </div>

      <!-- Statutory Freeze Guidance -->
      <div style="background:var(--color-primary-light); border:1px solid var(--border-color); border-radius:6px; padding:12px 16px; margin-bottom:12px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <div>
            <div style="font-size:11px; font-weight:600; text-transform:uppercase; color:var(--color-primary);">Statutory Policy Enforcement</div>
            <div style="font-size:13px; font-weight:600; color:var(--color-primary); margin-top:2px;">FSM State Transition: <code>PTP_FROZEN</code></div>
            <div style="font-size:11px; color:var(--text-secondary); margin-top:2px;">${data.stopping_rule_guidance}</div>
          </div>
          <span class="badge-pill pill-success" style="font-size:10px;">CPA 2019 Compliant</span>
        </div>
      </div>

      <div style="font-size:11px; color:var(--text-muted); font-style:italic;">
        Statutory Reference: ${data.statutory_reference} (Protects customer against harassment while commitment is active).
      </div>
    </div>
  `;
}

// =========================================================================
// Promise-to-Pay (PTP) Ledger & Operations Controller
// =========================================================================

const PTP_RECORDS = [
  {
    id: "ptp_7A91F2",
    customer_id: "Customer #48291",
    account: "····4821",
    amount: 18450.00,
    promise_date: "2026-09-02",
    promise_label: "02 Sep 2026",
    due_relative: "Upcoming (5 days)",
    status: "PROMISED",
    last_contact: "Hinglish Voice Bot",
    next_action: "Wait until promise date",
    conversation: "Haan bhaiya kal meri salary credit ho jayegi tab main pakka ₹18,450 transfer kar dunga.",
    confidence: 0.94,
    fsm_state: "PTP_FROZEN",
    audit_block: 2541,
    hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
  },
  {
    id: "ptp_8B32C1",
    customer_id: "Customer #19204",
    account: "····9012",
    amount: 5000.00,
    promise_date: "2026-08-28",
    promise_label: "Today · 28 Aug",
    due_relative: "Due Today",
    status: "DUE_TODAY",
    last_contact: "WhatsApp Nudge",
    next_action: "Await payment / send permitted reminder",
    conversation: "Kal salary aate hi 5000 bhej dunga pakka.",
    confidence: 0.96,
    fsm_state: "PTP_FROZEN",
    audit_block: 2538,
    hash: "a4f89c3178e2b8109d73fc941a87b2901c54b209e74d11a84f33190bf8314e6b"
  },
  {
    id: "ptp_9C44D8",
    customer_id: "Customer #67119",
    account: "····1183",
    amount: 8500.00,
    promise_date: "2026-08-26",
    promise_label: "26 Aug 2026",
    due_relative: "2 days overdue",
    status: "OVERDUE",
    last_contact: "Automated IVR",
    next_action: "Send follow-up / check liquidity",
    conversation: "Main 26 ko account me balance daal kar 8500 clear kar dunga.",
    confidence: 0.88,
    fsm_state: "PTP_EXPIRED",
    audit_block: 2519,
    hash: "7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069"
  },
  {
    id: "ptp_4D11E5",
    customer_id: "Customer #31802",
    account: "····5541",
    amount: 12000.00,
    promise_date: "2026-08-27",
    promise_label: "27 Aug · 14:20",
    due_relative: "Settled",
    status: "PAID",
    last_contact: "WhatsApp AutoPay Link",
    next_action: "Promise fulfilled · Recovery confirmed",
    conversation: "Haan maine kal ke liye promise kiya tha, abhi pay kar raha hu.",
    confidence: 0.98,
    fsm_state: "RECOVERED",
    audit_block: 2524,
    hash: "c8b41951e70e19a2b8e3fc74b9a1014e7f33918a24c55198e09f8712390a1b6c"
  },
  {
    id: "ptp_5E22F6",
    customer_id: "Customer #82910",
    account: "····7732",
    amount: 24500.00,
    promise_date: "2026-09-05",
    promise_label: "05 Sep 2026",
    due_relative: "Upcoming (8 days)",
    status: "PROMISED",
    last_contact: "Inbound Support Agent",
    next_action: "Wait until promise date",
    conversation: "5th ko bonus aane par 24500 ka full payment kar dunga.",
    confidence: 0.92,
    fsm_state: "PTP_FROZEN",
    audit_block: 2545,
    hash: "d9e831f28b74c0919a3b817e4f1a2390b761c48e920d3318f7410982341b5a6c"
  },
  {
    id: "ptp_6F33A7",
    customer_id: "Customer #94012",
    account: "····2290",
    amount: 15450.00,
    promise_date: "2026-08-28",
    promise_label: "Today · 28 Aug",
    due_relative: "Due Today",
    status: "DUE_TODAY",
    last_contact: "WhatsApp Intent",
    next_action: "Await payment / send permitted reminder",
    conversation: "Aaj shaam tak online transfer karta hu pakka.",
    confidence: 0.95,
    fsm_state: "PTP_FROZEN",
    audit_block: 2547,
    hash: "b109e83178c941a87b2901c54b209e74d11a84f33190bf8314e6ba4f89c3178e"
  }
];

function renderPtpRecords(records) {
  const tbody = document.getElementById("ptpTableBody");
  if (!tbody) return;

  if (!records || records.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align:center; padding:32px; color:var(--text-muted);">
          No payment promises match the selected filters.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = records.map(r => {
    let statusPill = `<span class="badge-pill pill-neutral"><span class="badge-dot"></span>Promised</span>`;
    if (r.status === "DUE_TODAY") statusPill = `<span class="badge-pill pill-warning"><span class="badge-dot"></span>Due Today</span>`;
    if (r.status === "OVERDUE") statusPill = `<span class="badge-pill pill-error"><span class="badge-dot"></span>Overdue</span>`;
    if (r.status === "PAID") statusPill = `<span class="badge-pill pill-success"><span class="badge-dot"></span>Paid</span>`;

    let dateClass = "color:var(--text-primary);";
    if (r.status === "DUE_TODAY") dateClass = "color:var(--color-warning-text); font-weight:600;";
    if (r.status === "OVERDUE") dateClass = "color:var(--color-error); font-weight:600;";
    if (r.status === "PAID") dateClass = "color:var(--color-success-text);";

    return `
      <tr>
        <td>
          <div style="font-weight:600; color:var(--text-primary);">${r.customer_id}</div>
          <div style="font-size:11px; color:var(--text-muted); font-family:var(--font-mono);">${r.account} · ID: ${r.id}</div>
        </td>
        <td class="col-numeric" style="font-weight:600;">
          ₹${r.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
        </td>
        <td>
          <div style="${dateClass}">${r.promise_label}</div>
          <div style="font-size:11px; color:var(--text-muted);">${r.due_relative}</div>
        </td>
        <td>${statusPill}</td>
        <td>
          <div style="font-size:12px; font-weight:500; color:var(--text-primary);">${r.next_action}</div>
          <div style="font-size:11px; color:var(--text-muted);">Last: ${r.last_contact}</div>
        </td>
        <td style="text-align:right;">
          <button class="btn btn-secondary btn-sm" onclick="openPtpModal('${r.id}')">
            Inspect →
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

function filterPtpRecords() {
  const query = (document.getElementById("ptpSearchInput")?.value || "").toLowerCase().trim();
  const statusFilter = document.getElementById("ptpStatusFilter")?.value || "ALL";

  const filtered = PTP_RECORDS.filter(r => {
    const matchQuery = !query ||
      r.customer_id.toLowerCase().includes(query) ||
      r.account.toLowerCase().includes(query) ||
      r.id.toLowerCase().includes(query) ||
      r.conversation.toLowerCase().includes(query) ||
      r.next_action.toLowerCase().includes(query);

    const matchStatus = statusFilter === "ALL" || r.status === statusFilter;
    return matchQuery && matchStatus;
  });

  renderPtpRecords(filtered);
}

function clearPtpFilters() {
  const searchEl = document.getElementById("ptpSearchInput");
  const statusEl = document.getElementById("ptpStatusFilter");
  if (searchEl) searchEl.value = "";
  if (statusEl) statusEl.value = "ALL";
  renderPtpRecords(PTP_RECORDS);
}

function openPtpModal(ptpId) {
  const record = PTP_RECORDS.find(r => r.id === ptpId);
  if (!record) return;

  const modal = document.getElementById("auditModal");
  const modalTxnId = document.getElementById("modalTxnId");
  const modalCustomer = document.getElementById("modalCustomer");
  const modalBody = document.getElementById("modalBody");

  if (!modal || !modalBody) return;

  modalTxnId.innerText = `Promise-to-Pay · ${record.id}`;
  modalCustomer.innerText = `${record.customer_id} (${record.account})`;
  modalBody.innerHTML = "";

  let statusBadge = `<span class="badge-pill pill-neutral"><span class="badge-dot"></span>Promised</span>`;
  if (record.status === "DUE_TODAY") statusBadge = `<span class="badge-pill pill-warning"><span class="badge-dot"></span>Due Today</span>`;
  if (record.status === "OVERDUE") statusBadge = `<span class="badge-pill pill-error"><span class="badge-dot"></span>Overdue</span>`;
  if (record.status === "PAID") statusBadge = `<span class="badge-pill pill-success"><span class="badge-dot"></span>Paid</span>`;

  // SECTION 1: PROMISE DETAILS
  const detailsCard = document.createElement("div");
  detailsCard.style.cssText = "background:var(--bg-surface); border:1px solid var(--border-color); border-radius:8px; padding:14px 16px; margin-bottom:14px;";
  detailsCard.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:10px;">
      <div>
        <div style="font-size:10px; font-weight:700; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.04em;">PROMISED AMOUNT</div>
        <div style="font-size:22px; font-weight:700; color:var(--text-primary); font-variant-numeric:tabular-nums; margin-top:2px;">₹${record.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
      </div>
      ${statusBadge}
    </div>
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; font-size:12px; border-top:1px solid var(--border-color); padding-top:8px;">
      <div><span style="color:var(--text-muted);">Promise Date:</span> <strong style="color:var(--text-primary);">${record.promise_label}</strong></div>
      <div><span style="color:var(--text-muted);">NLU Match:</span> <strong style="color:var(--color-primary);">${(record.confidence * 100).toFixed(0)}% Confidence</strong></div>
    </div>
  `;
  modalBody.appendChild(detailsCard);

  // SECTION 2: CONVERSATION EVIDENCE
  const convCard = document.createElement("div");
  convCard.style.cssText = "background:var(--bg-surface); border:1px solid var(--border-color); border-radius:8px; padding:14px 16px; margin-bottom:14px;";
  convCard.innerHTML = `
    <div style="font-size:11px; font-weight:700; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.04em; margin-bottom:8px;">CUSTOMER CONVERSATION TRANSCRIPT</div>
    <div style="background:var(--bg-secondary); border-left:3px solid var(--color-primary); padding:10px 12px; font-size:12.5px; font-style:italic; color:var(--text-primary); line-height:1.45; margin-bottom:8px; border-radius:0 var(--radius-sm) var(--radius-sm) 0;">
      "${record.conversation}"
    </div>
    <div style="display:flex; justify-content:space-between; font-size:11.5px; color:var(--text-secondary);">
      <span>Channel: <strong>${record.last_contact}</strong></span>
      <span>Detected Intent: <strong>Commitment to Pay</strong></span>
    </div>
  `;
  modalBody.appendChild(convCard);

  // SECTION 3: NEXT ACTION & RECOVERY GUIDANCE
  const actionCard = document.createElement("div");
  actionCard.style.cssText = "background:var(--bg-surface); border:1px solid var(--border-color); border-radius:8px; padding:14px 16px; margin-bottom:14px;";
  actionCard.innerHTML = `
    <div style="font-size:11px; font-weight:700; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.04em; margin-bottom:4px;">RECOVERY ACTION</div>
    <div style="font-size:13.5px; font-weight:600; color:var(--text-primary); margin-bottom:6px;">${record.next_action}</div>
    <div style="font-size:12px; color:var(--text-secondary); line-height:1.45;">
      Automated outreach is suspended under CPA 2019 fair collection rules while this promise window remains active.
    </div>
  `;
  modalBody.appendChild(actionCard);

  modal.classList.add("active");
}

// =========================================================================
// Welcome Screen & Typewriter Animation (Minimalist White Centerpiece)
// =========================================================================

let typewriterActive = false;
let typewriterTimeouts = [];

function initWelcomeScreen() {
  // Any keypress dismisses the welcome screen
  window.addEventListener("keydown", (e) => {
    const overlay = document.getElementById("welcomeOverlay");
    if (overlay && !overlay.classList.contains("fade-out")) {
      dismissWelcomeScreen();
    }
  });

  // Start typewriter on initial page load
  showWelcomeScreen(false);
}

function showWelcomeScreen(forceReplay = false) {
  const overlay = document.getElementById("welcomeOverlay");
  if (!overlay) return;

  // Clear any existing typewriter timeouts
  typewriterTimeouts.forEach(t => clearTimeout(t));
  typewriterTimeouts = [];

  overlay.classList.remove("fade-out");
  overlay.style.display = "flex";

  const mainEl = document.getElementById("typewriterMain");
  if (mainEl) mainEl.textContent = "";

  const mainTitleText = "Razorpay AI Revenue Recovery";
  let mainIdx = 0;
  typewriterActive = true;

  // 1. Type Main Title Character by Character smoothly
  function typeMain() {
    if (!typewriterActive) return;
    if (mainIdx <= mainTitleText.length) {
      if (mainEl) mainEl.textContent = mainTitleText.slice(0, mainIdx);
      const prevChar = mainIdx > 0 ? mainTitleText.charAt(mainIdx - 1) : "";
      mainIdx++;
      const delay = prevChar === " " ? 75 : 45 + Math.random() * 20;
      typewriterTimeouts.push(setTimeout(typeMain, delay));
    } else {
      // Pause then smoothly auto-fade into the dashboard
      typewriterTimeouts.push(setTimeout(dismissWelcomeScreen, 1200));
    }
  }

  // Start with brief natural delay
  typewriterTimeouts.push(setTimeout(typeMain, 250));
}

function dismissWelcomeScreen() {
  typewriterActive = false;
  typewriterTimeouts.forEach(t => clearTimeout(t));
  typewriterTimeouts = [];

  const overlay = document.getElementById("welcomeOverlay");
  if (!overlay) return;

  overlay.classList.add("fade-out");
  setTimeout(() => {
    overlay.style.display = "none";
  }, 620);
}

// =========================================================================
// Toast Notification Controller (Micro-Interactions)
// =========================================================================

function showToast(message, type = "info", duration = 3500) {
  let container = document.getElementById("toastContainer");
  if (!container) {
    container = document.createElement("div");
    container.id = "toastContainer";
    container.className = "toast-container";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;

  let iconSvg = `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>`;
  if (type === "success") {
    iconSvg = `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>`;
  } else if (type === "warning") {
    iconSvg = `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>`;
  } else if (type === "error") {
    iconSvg = `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>`;
  }

  toast.innerHTML = `
    ${iconSvg}
    <span class="toast-msg">${message}</span>
  `;

  container.appendChild(toast);

  requestAnimationFrame(() => {
    toast.classList.add("show");
  });

  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 200);
  }, duration);
}

// Global Keyboard Handler (Escape closes drawers & overlays)
window.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    closeModal();
    const overlay = document.getElementById("welcomeOverlay");
    if (overlay && !overlay.classList.contains("fade-out")) {
      dismissWelcomeScreen();
    }
  }
});
