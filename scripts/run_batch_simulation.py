#!/usr/bin/env python3
"""
Executive CLI script to run the FULL 750-Transaction Dataset through the
AI Revenue Recovery State Machine Pipeline via the Simulated-Clock Scheduler.
Computes measured money recovered, compliance invariants enforced, and generates
exportable audit records.
"""

import sys
import json
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from src.generators.batch_generator import BatchFailureGenerator
from src.orchestrator.batch_pipeline import BatchRecoveryPipeline


def main():
    dataset_path = root_dir / "data" / "synthetic_transactions_750.json"
    if len(sys.argv) > 1:
        dataset_path = Path(sys.argv[1])

    generator = BatchFailureGenerator(seed=42)
    if not dataset_path.exists():
        print(f"Dataset not found at {dataset_path}, generating 750 transactions...")
        events = generator.generate_batch(750)
        generator.export_to_json(events, dataset_path)
    else:
        events = generator.load_from_json(dataset_path)

    print("\n" + "=" * 80)
    print("🚀 EXECUTING FULL DATASET BATCH RECOVERY SIMULATION (SIMULATED CLOCK)")
    print("=" * 80)
    print(f"• Ingesting Dataset File     : {dataset_path.name}")
    print(f"• Total Transaction Count    : {len(events):,} transactions")
    print(f"• Total Initial Volume       : ₹{sum(e.amount for e in events):,.2f}")
    print(f"• Simulated Time Horizon     : 14 Days (Fast-Forwarded in Discrete Event Loop)")
    print("-" * 80)

    pipeline = BatchRecoveryPipeline(seed=42)
    summary, fsms = pipeline.run_batch_simulation(events, simulation_days=14)

    # Export full audit trails
    audit_json_path = root_dir / "data" / "full_batch_audit_trail.json"
    audit_md_path = root_dir / "data" / "full_batch_audit_report.md"
    pipeline.audit_logger.export_to_json(audit_json_path, indent=2)
    pipeline.audit_logger.export_to_markdown_report(audit_md_path, title="750-Transaction Batch Compliance Audit Trail")

    print("\n" + "=" * 80)
    print("📊 EXECUTIVE MEASUREMENT & RECOVERY BENCHMARK RESULTS")
    print("=" * 80)
    print(f"💰 Total Ingested Revenue at Risk : ₹{summary.total_revenue_at_risk_inr:>13,.2f}")
    print(f"✅ Measured Revenue Recovered     : ₹{summary.total_recovered_revenue_inr:>13,.2f} ({summary.overall_recovery_rate_pct:.1f}% Recovery Yield)")
    print(f"❌ Unrecovered / Terminal Volume  : ₹{summary.total_unrecovered_revenue_inr:>13,.2f}")
    print("-" * 80)
    print("📈 Transaction Outcome Distribution:")
    print(f"  • Successfully Recovered (RECOVERED)      : {summary.recovered_count:>4} ({(summary.recovered_count/summary.total_transactions)*100:>5.1f}%)")
    print(f"  • Compliantly Stopped (UNRECOVERABLE)     : {summary.unrecoverable_count:>4} ({(summary.unrecoverable_count/summary.total_transactions)*100:>5.1f}%)")
    print(f"  • Risk Quarantined (HUMAN_REVIEW)         : {summary.human_review_count:>4} ({(summary.human_review_count/summary.total_transactions)*100:>5.1f}%)")
    print("-" * 80)
    print("🛡️ Statutory & Compliance Invariants Enforced (Zero Bypasses):")
    for rule, cnt in sorted(summary.statutory_rules_enforced.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {rule:<38}: {cnt:>4} events")
    print("-" * 80)
    print("🛑 Deterministic Stopping Rules Triggered (Purged Queues):")
    for s_rule, cnt in sorted(summary.stopping_rules_triggered.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {s_rule:<38}: {cnt:>4} transactions")
    print("-" * 80)
    print("📡 TRAI DLT Outbound Stream Allocation:")
    for stream, cnt in sorted(summary.dlt_streams_distributed.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {stream:<38}: {cnt:>4} messages")
    print("-" * 80)
    print(f"📜 Total Structured Audit Records Generated: {summary.total_audit_events_recorded:,} records")
    print(f"📁 Audit Exports Saved:")
    print(f"  • JSON Trail : {audit_json_path}")
    print(f"  • MD Report  : {audit_md_path}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
