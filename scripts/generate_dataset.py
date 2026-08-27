#!/usr/bin/env python3
"""
CLI script to generate a realistic synthetic dataset of 600-800 payment failure transactions.
"""

import sys
import json
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from src.generators.batch_generator import BatchFailureGenerator


def main():
    count = 750
    if len(sys.argv) > 1:
        count = int(sys.argv[1])

    print(f"🚀 Generating realistic synthetic payment failure dataset ({count} transactions)...")
    generator = BatchFailureGenerator(seed=42)
    events = generator.generate_batch(count=count)

    output_path = root_dir / "data" / f"synthetic_transactions_{count}.json"
    generator.export_to_json(events, output_path)
    print(f"💾 Dataset exported successfully to: {output_path}")

    # Compute and print metrics
    summary = generator.print_batch_summary(events)
    print("\n" + "=" * 60)
    print("📊 BATCH REVENUE & COMPLIANCE SUMMARY REPORT")
    print("=" * 60)
    print(f"• Total Transactions Generated : {summary['total_transactions']:,}")
    print(f"• Total Revenue at Risk        : ₹{summary['total_revenue_at_risk_inr']:,.2f}")
    print(f"• Average Ticket Size          : ₹{summary['average_ticket_size_inr']:,.2f}")
    print("-" * 60)
    print("📈 Transaction Type Breakdown:")
    for t_type, cnt in summary["transaction_type_breakdown"].items():
        pct = (cnt / summary["total_transactions"]) * 100
        print(f"  - {t_type:<25}: {cnt:>4} ({pct:>5.1f}%)")
    print("-" * 60)
    print("🛡️ Compliance, Risk & Edge Case Markers:")
    print(f"  - Risk Flagged (Human Review Required) : {summary['risk_flagged_count']:>4} ({(summary['risk_flagged_count']/count)*100:.1f}%)")
    print(f"  - Ambiguous / Unmapped Raw Declines    : {summary['ambiguous_raw_decline_count']:>4} ({(summary['ambiguous_raw_decline_count']/count)*100:.1f}%)")
    print(f"  - Statutory AFA Required (>₹15k/₹1L)   : {summary['afa_required_count']:>4} ({(summary['afa_required_count']/count)*100:.1f}%)")
    print(f"  - Active Promise-to-Pay (PTP Frozen)   : {summary['active_ptp_count']:>4} ({(summary['active_ptp_count']/count)*100:.1f}%)")
    print(f"  - TRAI DND Registered                  : {summary['dnd_registered_count']:>4} ({(summary['dnd_registered_count']/count)*100:.1f}%)")
    print(f"  - Active Fraud Dispute / Chargeback    : {summary['dispute_active_count']:>4} ({(summary['dispute_active_count']/count)*100:.1f}%)")
    print("-" * 60)
    print("🔍 Error Reason Distribution (All 13 Buckets):")
    for reason, cnt in summary["top_error_reasons"]:
        pct = (cnt / summary["total_transactions"]) * 100
        print(f"  - {reason:<35}: {cnt:>4} ({pct:>5.1f}%)")
    print("=" * 60)


if __name__ == "__main__":
    main()
