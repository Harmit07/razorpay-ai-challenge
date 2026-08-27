#!/usr/bin/env python3
"""
CLI tool to execute the Rule-Based Classifier on the transaction dataset
and generate a comprehensive classification and compliance audit breakdown.
"""

import sys
import json
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from src.generators.batch_generator import BatchFailureGenerator
from src.classifiers.rule_classifier import RuleBasedClassifier, RetryabilityType


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

    classifier = RuleBasedClassifier()
    results = classifier.classify_batch(events)

    total = len(results)
    high_conf = [r for r in results if r.confidence >= 0.85]
    ambiguous = [r for r in results if r.requires_llm_disambiguation]
    human_esc = [r for r in results if r.requires_human_escalation]

    # Stopping rules summary
    stopping_rules = {}
    for r in results:
        if r.stopping_rule:
            stopping_rules[r.stopping_rule] = stopping_rules.get(r.stopping_rule, 0) + 1

    # Retryability breakdown
    retryability = {}
    for r in results:
        retryability[r.retryability.value] = retryability.get(r.retryability.value, 0) + 1

    # DLT Stream breakdown
    dlt_streams = {}
    for r in results:
        dlt_streams[r.dlt_stream.value] = dlt_streams.get(r.dlt_stream.value, 0) + 1

    print("\n" + "=" * 65)
    print("🎯 RULE-BASED CLASSIFIER EXECUTION AUDIT (750 TRANSACTIONS)")
    print("=" * 65)
    print(f"• Total Transactions Processed        : {total:,}")
    print(f"• Clean Rule-Based Resolution (>=0.85): {len(high_conf):>4} ({(len(high_conf)/total)*100:>5.1f}%)")
    print(f"• Ambiguous Cases (LLM Disambiguation): {len(ambiguous):>4} ({(len(ambiguous)/total)*100:>5.1f}%)")
    print(f"• Risk Flagged / Human Review (<0.70) : {len(human_esc):>4} ({(len(human_esc)/total)*100:>5.1f}%)")
    print("-" * 65)
    print("🔄 Retryability & Action Routing Distribution:")
    for ret, cnt in retryability.items():
        pct = (cnt / total) * 100
        print(f"  - {ret:<28}: {cnt:>4} ({pct:>5.1f}%)")
    print("-" * 65)
    print("🛑 Triggered Stopping Rules (Deterministic Invariants):")
    for rule, cnt in sorted(stopping_rules.items(), key=lambda x: x[1], reverse=True):
        pct = (cnt / total) * 100
        print(f"  - {rule:<28}: {cnt:>4} ({pct:>5.1f}%)")
    print("-" * 65)
    print("📡 TRAI DLT Outbound Stream Allocation:")
    for stream, cnt in dlt_streams.items():
        pct = (cnt / total) * 100
        print(f"  - {stream:<28}: {cnt:>4} ({pct:>5.1f}%)")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
