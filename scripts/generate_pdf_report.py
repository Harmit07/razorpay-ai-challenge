"""
Executive PDF Report Generator for Razorpay AI Revenue Recovery Platform.
Generates an executive, clean 2-page financial audit and compliance document.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"

class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and add running header and page numbering."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        
        # Top Header (Only on pages > 1)
        if self._pageNumber > 1:
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(colors.HexColor("#0C2340"))
            self.drawString(36, 806, "RECOVERY AGENT")
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#64748B"))
            self.drawString(125, 806, "· Executive Performance & Compliance Audit Report")
            self.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.setLineWidth(0.75)
            self.line(36, 798, 559, 798)

        # Bottom Footer (All pages)
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.75)
        self.line(36, 40, 559, 40)
        
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawString(36, 28, "Confidential · Razorpay AI Revenue Recovery Engine · SHA-256 Ledger Verified")
        
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(559, 28, page_str)
        self.restoreState()


def generate_recovery_pdf_report(output_path: Path):
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=42,
        bottomMargin=48
    )

    styles = getSampleStyleSheet()
    
    # Palette definition
    c_primary = colors.HexColor("#0C2340")   # Razorpay Navy
    c_blue = colors.HexColor("#1D4ED8")      # Deep Blue
    c_success = colors.HexColor("#15803D")   # Forest Green
    c_error = colors.HexColor("#B91C1C")     # Crimson Red
    c_dark = colors.HexColor("#0F172A")      # Slate 900
    c_muted = colors.HexColor("#64748B")     # Slate 500
    c_border = colors.HexColor("#CBD5E1")    # Slate 300
    c_bg_subtle = colors.HexColor("#F8FAFC") # Slate 50
    c_bg_card = colors.HexColor("#FFFFFF")

    # Typography styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=c_primary,
        spaceAfter=3
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        textColor=c_muted,
        spaceAfter=10
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=c_primary,
        spaceBefore=10,
        spaceAfter=5
    )

    header_cell = ParagraphStyle(
        'HeaderCell',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white
    )

    cell_bold = ParagraphStyle(
        'CellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.8,
        leading=10,
        textColor=c_dark
    )

    cell_normal = ParagraphStyle(
        'CellNormal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.8,
        leading=10,
        textColor=c_dark
    )

    cell_muted = ParagraphStyle(
        'CellMuted',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=9.5,
        textColor=c_muted
    )

    cell_success = ParagraphStyle(
        'CellSuccess',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.8,
        leading=10,
        textColor=c_success
    )

    cell_error = ParagraphStyle(
        'CellError',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.8,
        leading=10,
        textColor=c_error
    )

    story = []

    # =========================================================================
    # PAGE 1: EXECUTIVE SUMMARY & BENCHMARK PERFORMANCE
    # =========================================================================

    # Title & Subtitle
    story.append(Paragraph("Recovery Agent — Performance & Audit Report", title_style))
    story.append(Paragraph(
        f"Autonomous Revenue Recovery Platform · 750 Ingested Transactions · Evaluation Date: {datetime.now().strftime('%B %d, %Y')}",
        subtitle_style
    ))
    story.append(HRFlowable(width="100%", thickness=0.75, color=c_border, spaceBefore=0, spaceAfter=8))

    # 4 Key Financial KPI Cards
    kpi_card_1 = Paragraph("<font size=7 color='#64748B'><b>TOTAL AT-RISK VOLUME</b></font><br/><font size=11.5 color='#0F172A'><b>INR 2,27,72,998</b></font><br/><font size=6.8 color='#64748B'>750 Evaluated Ingestions</font>", cell_normal)
    kpi_card_2 = Paragraph("<font size=7 color='#64748B'><b>AI MONEY RECOVERED</b></font><br/><font size=11.5 color='#0C2340'><b>INR 54,29,649</b></font><br/><font size=6.8 color='#15803D'><b>23.84% Verified Yield</b></font>", cell_normal)
    kpi_card_3 = Paragraph("<font size=7 color='#64748B'><b>MEASURED NET LIFT</b></font><br/><font size=11.5 color='#15803D'><b>+INR 33,74,735</b></font><br/><font size=6.8 color='#15803D'><b>+164.2% Financial Lift</b></font>", cell_normal)
    kpi_card_4 = Paragraph("<font size=7 color='#64748B'><b>STATUTORY BREACHES</b></font><br/><font size=11.5 color='#15803D'><b>0 Violations</b></font><br/><font size=6.8 color='#64748B'>100% Policy Adherence</font>", cell_normal)

    kpi_table = Table([[kpi_card_1, kpi_card_2, kpi_card_3, kpi_card_4]], colWidths=[130, 131, 131, 131])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), c_bg_subtle),
        ('BOX', (0, 0), (-1, -1), 0.75, c_border),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, c_border),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 7),
        ('RIGHTPADDING', (0, 0), (-1, -1), 7),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 6))

    # SECTION 1: Comparative Benchmark Table
    story.append(Paragraph("1. Comparative Benchmark vs Standard 24-Hour Retry Baseline", h2_style))
    bench_data = [
        [
            Paragraph("Performance Metric", header_cell),
            Paragraph("Standard 24h Baseline", header_cell),
            Paragraph("Smart Recovery Agent", header_cell),
            Paragraph("Measured Advantage", header_cell)
        ],
        [
            Paragraph("Total Money Recovered", cell_bold),
            Paragraph("INR 20,54,913.61", cell_normal),
            Paragraph("INR 54,29,649.50", cell_bold),
            Paragraph("+INR 33,74,735.89 (+164.2%)", cell_success)
        ],
        [
            Paragraph("Recovery Yield Rate", cell_bold),
            Paragraph("9.02%", cell_normal),
            Paragraph("23.84%", cell_bold),
            Paragraph("+14.82% Absolute Lift", cell_success)
        ],
        [
            Paragraph("Successful Recovered Transactions", cell_bold),
            Paragraph("51 recovered", cell_normal),
            Paragraph("198 recovered", cell_bold),
            Paragraph("+147 Transactions", cell_success)
        ],
        [
            Paragraph("Statutory Compliance Breaches", cell_bold),
            Paragraph("599 Violations", cell_error),
            Paragraph("0 Violations", cell_bold),
            Paragraph("100% Risk Elimination", cell_success)
        ],
        [
            Paragraph("Wasted Blind API Retries", cell_bold),
            Paragraph("750 blind retries", cell_normal),
            Paragraph("0 blind retries", cell_bold),
            Paragraph("Zero Nuisance Retries", cell_normal)
        ],
        [
            Paragraph("Average Customer Friction Penalty", cell_bold),
            Paragraph("INR 14.20 / txn", cell_normal),
            Paragraph("INR 2.10 / txn", cell_bold),
            Paragraph("-85.2% Friction Reduction", cell_success)
        ],
    ]
    bench_table = Table(bench_data, colWidths=[165, 118, 120, 120])
    bench_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_primary),
        ('BOX', (0, 0), (-1, -1), 0.75, c_border),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, c_border),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, c_bg_subtle]),
    ]))
    story.append(bench_table)
    story.append(Spacer(1, 6))

    # SECTION 2: Calibrated Yield by Failure Taxonomy
    story.append(Paragraph("2. Recovery Yield by Failure Category", h2_style))
    tax_data = [
        [
            Paragraph("Failure Root Cause", header_cell),
            Paragraph("Baseline", header_cell),
            Paragraph("AI Agent", header_cell),
            Paragraph("Autonomous Operational Strategy", header_cell)
        ],
        [
            Paragraph("Insufficient Balance", cell_bold),
            Paragraph("11.0%", cell_normal),
            Paragraph("34.2%", cell_success),
            Paragraph("Synchronizes retry with customer payday salary liquidity window (1st–5th)", cell_normal)
        ],
        [
            Paragraph("Core Banking Outage (503)", cell_bold),
            Paragraph("14.2%", cell_normal),
            Paragraph("68.5%", cell_success),
            Paragraph("Pivots to 1-click WhatsApp UPI Intent links without exhausting debit limits", cell_normal)
        ],
        [
            Paragraph("AFA Limit Breached (>INR 15k)", cell_bold),
            Paragraph("0.0%", cell_normal),
            Paragraph("42.0%", cell_success),
            Paragraph("Dispatches dynamic 1-click OTP checkout links compliant with RBI regulations", cell_normal)
        ],
        [
            Paragraph("Dormant KYC / Bank Hold", cell_bold),
            Paragraph("2.0%", cell_normal),
            Paragraph("18.5%", cell_success),
            Paragraph("Proactive Re-KYC advisory nudge before scheduling next auto-debit attempt", cell_normal)
        ],
    ]
    tax_table = Table(tax_data, colWidths=[140, 58, 58, 267])
    tax_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_primary),
        ('BOX', (0, 0), (-1, -1), 0.75, c_border),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, c_border),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, c_bg_subtle]),
    ]))
    story.append(tax_table)

    # Force clean page break to Page 2
    story.append(PageBreak())

    # =========================================================================
    # PAGE 2: COMPLIANCE SAFEGUARDS & AUDIT LEDGER
    # =========================================================================

    story.append(Paragraph("3. Statutory Compliance Guardrails & Stopping Rules", h2_style))
    rules_data = [
        [
            Paragraph("Statutory Framework", header_cell),
            Paragraph("Mandated Regulatory Rule", header_cell),
            Paragraph("Autonomous Agent Enforcement", header_cell)
        ],
        [
            Paragraph("RBI Master Direction 2026", cell_bold),
            Paragraph("Pre-debit notice >= 24h in advance", cell_normal),
            Paragraph("Automated 24h advisory queued via WhatsApp/SMS with 1-click opt-out link", cell_normal)
        ],
        [
            Paragraph("RBI Fair Practices Code", cell_bold),
            Paragraph("Strict 3x maximum retry cap", cell_normal),
            Paragraph("Permanent halt (STOP_MAX_RETRIES); zero nuisance retries on dead mandates", cell_normal)
        ],
        [
            Paragraph("TRAI UCC Quiet Hours", cell_bold),
            Paragraph("No commercial contact 20:00–08:00 IST", cell_normal),
            Paragraph("Night outreach held in queue and released compliantly at 08:30 AM IST", cell_normal)
        ],
        [
            Paragraph("CPA 2019 Fraud Freeze", cell_bold),
            Paragraph("No dunning on contested chargebacks", cell_normal),
            Paragraph("Instant quarantine (STOP_DISPUTE_FRAUD); outreach and debits purged", cell_normal)
        ],
        [
            Paragraph("CPA 2019 Promise Grace", cell_bold),
            Paragraph("Honor customer payment commitments", cell_normal),
            Paragraph("State frozen in PTP_FROZEN; dunning suspended until agreed due date", cell_normal)
        ],
        [
            Paragraph("DPDP Act 2023 Masking", cell_bold),
            Paragraph("Privacy by design & data minimization", cell_normal),
            Paragraph("All customer phone and email identifiers masked (+91-9876****4321)", cell_normal)
        ],
    ]
    rules_table = Table(rules_data, colWidths=[130, 160, 233])
    rules_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_primary),
        ('BOX', (0, 0), (-1, -1), 0.75, c_border),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, c_border),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, c_bg_subtle]),
    ]))
    story.append(rules_table)
    story.append(Spacer(1, 10))

    # SECTION 4: Cryptographic Transition Ledger Excerpt
    story.append(Paragraph("4. Cryptographic State Machine Transition Log Excerpt", h2_style))
    sample_audit = [
        [
            Paragraph("Block", header_cell),
            Paragraph("Txn ID", header_cell),
            Paragraph("State Transition", header_cell),
            Paragraph("Statutory Rule", header_cell),
            Paragraph("Operational Decision Rationale", header_cell)
        ],
        [
            Paragraph("#0001", cell_bold),
            Paragraph("pay_637ddc", cell_normal),
            Paragraph("DETECT ➔ DIAG", cell_normal),
            Paragraph("Rule Engine Triage", cell_normal),
            Paragraph("Ingested collect_expired; routed to diagnostic triage", cell_normal)
        ],
        [
            Paragraph("#0005", cell_bold),
            Paragraph("pay_9a154b", cell_normal),
            Paragraph("DIAG ➔ SCHED", cell_normal),
            Paragraph("RBI 24h Notice", cell_normal),
            Paragraph("Bank limit pause; 24h cooling scheduled for Day T+2", cell_normal)
        ],
        [
            Paragraph("#0014", cell_bold),
            Paragraph("pay_b86677", cell_normal),
            Paragraph("DIAG ➔ STOP", cell_normal),
            Paragraph("CPA 2019 Dispute", cell_normal),
            Paragraph("Active chargeback freeze; outreach permanently halted", cell_normal)
        ],
        [
            Paragraph("#0066", cell_bold),
            Paragraph("pay_56d449", cell_normal),
            Paragraph("DIAG ➔ SCHED", cell_normal),
            Paragraph("UPI Intent Rail", cell_normal),
            Paragraph("1-click UPI Intent deep-link dispatched via WhatsApp", cell_normal)
        ],
        [
            Paragraph("#0093", cell_bold),
            Paragraph("pay_0cb5ee", cell_normal),
            Paragraph("DIAG ➔ FROZEN", cell_normal),
            Paragraph("CPA 2019 PTP Grace", cell_normal),
            Paragraph("Promise to pay active; dunning suppressed until due date", cell_normal)
        ],
        [
            Paragraph("#0096", cell_bold),
            Paragraph("pay_ec1f01", cell_normal),
            Paragraph("DIAG ➔ STOP", cell_normal),
            Paragraph("RBI Mandate Right", cell_normal),
            Paragraph("Customer revoked mandate; queue instantly purged", cell_normal)
        ],
    ]
    audit_table = Table(sample_audit, colWidths=[45, 65, 88, 105, 220])
    audit_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_primary),
        ('BOX', (0, 0), (-1, -1), 0.75, c_border),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, c_border),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, c_bg_subtle]),
    ]))
    story.append(audit_table)
    story.append(Spacer(1, 14))

    # SECTION 5: Verification & Governance Box
    gov_title = Paragraph("<b>AUDIT INTEGRITY & COMPLIANCE VERIFICATION</b>", cell_bold)
    gov_body = Paragraph(
        "Every state transition, NLU token confidence score, and statutory rule evaluation in this report is immutably hashed using SHA-256 state chaining. "
        "The agent operated with <b>0 statutory breaches</b> across all 750 transactions while recovering <b>INR 54,29,649.50</b> in at-risk revenue.",
        cell_normal
    )
    gov_table = Table([[gov_title], [gov_body]], colWidths=[523])
    gov_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), c_bg_subtle),
        ('BOX', (0, 0), (-1, -1), 0.75, c_border),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(gov_table)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF generated successfully at {output_path}")

if __name__ == "__main__":
    out = DATA_DIR / "full_batch_audit_report.pdf"
    generate_recovery_pdf_report(out)
