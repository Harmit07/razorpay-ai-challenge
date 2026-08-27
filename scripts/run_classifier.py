#!/usr/bin/env python3
"""
CLI tool to execute the Full Diagnostic Classifier Pipeline
(Stage 1 Rule-Based Triage + Stage 2 LLM Fallback Disambiguation)
and print a detailed classification, reasoning, and compliance audit report.
"""

import sys
import json
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from src.generators.batch_generator import BatchFailureGenerator
from src.classifiers.rule_classifier import RuleBasedClassifier, RetryabilityType
from src.classifiers.llm_fallback import LLMFallbackClassifier


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

    rule_classifier = RuleBasedClassifier()
    llm_parser = LLMFallbackClassifier()

    stage1_results = rule_classifier.classify_batch(events)
    total = len(stage1_results)

    # Separate into Clean (>=0.85), Ambiguous (for LLM Disambiguation), and Human Esc (<0.70 / Risk)
    clean_cases = [r for r in stage1_results if r.confidence >= 0.85]
    ambiguous_events = [e for e, r in zip(events, stage1_results) if r.requires_llm_disambiguation]
    human_esc = [r for r in stage1_results if r.requires_human_escalation]

    # Stage 2: Process ambiguous cases through LLM fallback
    llm_resolved = [llm_parser.disambiguate_error(e) for e in ambiguous_events]

    print("\n" + "=" * 70)
    print("🎯 FULL RECOVERY DIAGNOSTIC & LLM FALLBACK PIPELINE AUDIT (750 TXNS)")
    print("=" * 70)
    print(f"• Total Ingested Transactions         : {total:,}")
    print(f"• Stage 1: Clean Deterministic Rules   : {len(clean_cases):>4} ({(len(clean_cases)/total)*100:>5.1f}%)")
    print(f"• Stage 2: Sent to LLM Fallback Parser : {len(ambiguous_events):>4} ({(len(ambiguous_events)/total)*100:>5.1f}%)")
    print(f"• Direct Human Review Escalations     : {len(human_esc):>4} ({(len(human_esc)/total)*100:>5.1f}%)")
    print("-" * 70)
    print("🤖 LLM FALLBACK DISAMBIGUATION BREAKDOWN (Sample Resolved Audits):")
    for i, res in enumerate(llm_resolved[:5], 1):
        print(f"  [{i}] Txn ID   : {res.txn_id}")
        print(f"      Assigned : Bucket {res.assigned_bucket_id} ({res.assigned_bucket_name})")
        print(f"      Conf     : {res.confidence:.2f}")
        print(f"      Audit Log: \"{res.reasoning}\"")
        print(f"      Action   : {res.recommended_action}")
        print()

    # Aggregate final state after LLM resolution
    final_resolved_count = len(clean_cases) + sum(1 for r in llm_resolved if not r.requires_human_escalation)
    final_human_count = len(human_esc) + sum(1 for r in llm_resolved if r.requires_human_escalation)

    print("-" * 70)
    print("📈 FINAL SYSTEM RESOLUTION YIELD:")
    print(f"• Successfully Automated Actions : {final_resolved_count:>4} ({(final_resolved_count/total)*100:>5.1f}%)")
    print(f"• Safe Human Escalation Queue    : {final_human_count:>4} ({(final_human_count/total)*100:>5.1f}%)")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
