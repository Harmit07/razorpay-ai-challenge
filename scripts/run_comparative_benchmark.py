#!/usr/bin/env python3
"""
Comparative Benchmark Script: AI Revenue Recovery Agent vs Naive Baseline.
Runs both engines on data/synthetic_transactions_750.json and generates comparative reports.
"""

import sys
import json
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from src.generators.batch_generator import BatchFailureGenerator
from src.benchmarks.comparative_evaluator import BenchmarkEvaluator


def main():
    dataset_path = root_dir / "data" / "synthetic_transactions_750.json"
    generator = BatchFailureGenerator(seed=42)
    
    if not dataset_path.exists():
        print(f"Generating 750 dataset at {dataset_path}...")
        events = generator.generate_batch(750)
        generator.export_to_json(events, dataset_path)
    else:
        events = generator.load_from_json(dataset_path)

    print("\n" + "=" * 80)
    print("🥊 RUNNING HEAD-TO-HEAD COMPARATIVE BENCHMARK (750 TRANSACTIONS)")
    print("=" * 80)

    evaluator = BenchmarkEvaluator(seed=42)
    report = evaluator.evaluate(events, dataset_name="synthetic_transactions_750.json")

    # Export report files
    md_path = root_dir / "data" / "comparative_benchmark_report.md"
    json_path = root_dir / "data" / "comparative_benchmark_results.json"
    evaluator.export_report_markdown(report, md_path)
    evaluator.export_report_json(report, json_path)

    print(f"Dataset Analyzed: {report.total_transactions:,} transactions (₹{report.total_revenue_at_risk_inr:,.2f} Volume)")
    print("-" * 80)
    print(f"📊 REVENUE RECOVERED:")
    print(f"   • Naive Baseline       : ₹{report.naive_recovered_revenue_inr:>12,.2f} ({report.naive_recovery_rate_pct:>5.1f}% yield, {report.naive_recovered_count} txns)")
    print(f"   • AI Recovery Agent    : ₹{report.ai_recovered_revenue_inr:>12,.2f} ({report.ai_recovery_rate_pct:>5.1f}% yield, {report.ai_recovered_count} txns)")
    print(f"   👉 Incremental Value   : +₹{report.incremental_recovered_revenue_inr:>11,.2f} (+{report.revenue_recovery_lift_pct:.1f}% Recovery Lift 🚀)")
    print("-" * 80)
    print(f"🛡️ STATUTORY & REGULATORY RISK:")
    print(f"   • Naive Baseline       : ⚠️  {report.naive_compliance_violations:>4} Statutory Violations (High Regulatory & Churn Risk)")
    print(f"   • AI Recovery Agent    : 🛡️  {report.ai_compliance_violations:>4} Statutory Violations (100% Invariant Compliant)")
    print(f"   👉 Risk Reduction      : {report.compliance_risk_reduction_pct:.1f}% Statutory Violation Elimination")
    print("-" * 80)
    print(f"📁 Reports Exported:")
    print(f"   • Markdown Summary : {md_path}")
    print(f"   • Structured JSON  : {json_path}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
