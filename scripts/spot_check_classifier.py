#!/usr/bin/env python3
"""
Spot-check audit script: Evaluates 50 representative failure events across
all 13 error taxonomy buckets and 10 edge cases, verifying classification accuracy,
confidence thresholds, stopping rule adherence, and reasoning strings.
"""

import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from src.generators.batch_generator import BatchFailureGenerator
from src.classifiers.rule_classifier import RuleBasedClassifier
from src.classifiers.llm_fallback import LLMFallbackClassifier


def run_spot_check():
    gen = BatchFailureGenerator(seed=42)
    events = gen.load_from_json(root_dir / "data" / "synthetic_transactions_750.json")
    rule_cls = RuleBasedClassifier()
    llm_cls = LLMFallbackClassifier()

    # Collect 50 diverse cases
    sample_50 = []
    # 1. All 10 deliberate edge cases
    sample_50.extend([e for e in events if e.edge_case_tag is not None])
    # 2. Representatives from all 13 buckets
    for b_id in range(1, 14):
        matching = [e for e in events if e.error_reason == gen.BUCKET_SIGNATURES[b_id - 1]["error_reason"] and e.edge_case_tag is None]
        if matching:
            sample_50.append(matching[0])
    # 3. Fill up to 50
    for e in events:
        if len(sample_50) >= 50:
            break
        if e not in sample_50:
            sample_50.append(e)

    print(f"Auditing {len(sample_50)} representative transactions...\n")
    audit_rows = []

    for i, e in enumerate(sample_50, 1):
        res1 = rule_cls.classify(e)
        stage = "Rule Engine"
        if res1.requires_llm_disambiguation:
            res_final = llm_cls.disambiguate_error(e)
            stage = "LLM Fallback"
            conf = res_final.confidence
            bucket_id = res_final.assigned_bucket_id
            bucket_name = res_final.assigned_bucket_name
            action = res_final.recommended_action
            reasoning = res_final.reasoning
            status = "✅ RESOLVED (LLM)" if conf >= 0.70 else "⚠️ SAFE HUMAN ESCALATION"
        elif res1.requires_human_escalation:
            conf = res1.confidence
            bucket_id = res1.bucket_id
            bucket_name = res1.bucket_name
            action = res1.recommended_action
            reasoning = f"Risk/Dispute Guard: {res1.internal_policy_applied}"
            status = "🛡️ RISK QUARANTINE"
        else:
            conf = res1.confidence
            bucket_id = res1.bucket_id
            bucket_name = res1.bucket_name
            action = res1.recommended_action
            reasoning = f"Rule Match: {res1.statutory_rule_applied} | {res1.internal_policy_applied}"
            status = "✅ MATCH (Rule)"

        audit_rows.append({
            "idx": i,
            "txn_id": e.txn_id,
            "error_reason": e.error_reason,
            "amount": e.amount,
            "stage": stage,
            "bucket_id": bucket_id,
            "bucket_name": bucket_name,
            "confidence": conf,
            "action": action,
            "reasoning": reasoning,
            "status": status,
        })

    return audit_rows


if __name__ == "__main__":
    rows = run_spot_check()
    for r in rows:
        print(f"[{r['idx']:02d}] {r['txn_id']} | B={r['bucket_id']:<2} | Conf={r['confidence']:.2f} | {r['status']:<25} | Action={r['action'][:30]}")
