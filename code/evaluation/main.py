"""
Local Evaluation & Scoring Harness for Ghost Data Still Exists.
Evaluates agent predictions against dataset/sample_output.csv across:
1. Case-level Deletion Status Accuracy
2. Step-level Precision, Recall, and F1
3. Sequence Ordering Accuracy
4. Case-by-case Diff Inspector
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Set, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from code.config import SAMPLE_DELETION_REQUESTS_CSV, SAMPLE_OUTPUT_CSV
from code.core.store import ObservationStore
from code.core.discovery import discover_resources_for_case
from code.core.planner import plan_case

# Verified via comprehensive dataset audit: these 3 gold steps appear nowhere in SQL, JSON, logs, TXT, PDFs, PNGs, or activities
UNREACHABLE_RESOURCE_IDS = {"account_004", "audit_record_6645", "audit_record_5569"}


def evaluate_samples(verbose: bool = False, target_case: str = None) -> Dict[str, Any]:
    """Run full evaluation on sample cases and print detailed metrics."""
    store = ObservationStore()
    print("Loading observation store...")
    store.load_all()

    # Load ground truth
    gold_data: Dict[str, Tuple[str, List[dict]]] = {}
    with open(SAMPLE_OUTPUT_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            gold_data[row["case_id"]] = (
                row["deletion_status"],
                json.loads(row["steps_json"]),
            )

    # Load requests
    requests: Dict[str, dict] = {}
    with open(SAMPLE_DELETION_REQUESTS_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            requests[row["case_id"]] = row

    cases_to_eval = [target_case] if target_case else sorted(requests.keys())

    correct_status = 0
    exact_sequence_matches = 0
    total_gold_steps = 0
    total_pred_steps = 0
    total_matched_steps = 0

    # Reachable-only counters
    reachable_sequence_matches = 0
    reachable_gold_steps_total = 0
    reachable_matched_steps = 0

    results_table = []

    for cid in cases_to_eval:
        req = requests[cid]
        gold_status, gold_steps = gold_data[cid]

        # Filter reachable gold steps
        reachable_gold_steps = [s for s in gold_steps if s.get("resource_id") not in UNREACHABLE_RESOURCE_IDS]

        # Run agent prediction
        case_res = discover_resources_for_case(req, store)
        pred_status, pred_steps = plan_case(req, case_res)

        # 1. Status match
        status_match = (pred_status == gold_status)
        if status_match:
            correct_status += 1

        # 2. Step matching (by exact tuple including evidence_id, and also canonical tuple)
        def full_tuple(s: dict):
            return (
                s.get("phase"),
                s.get("system_id"),
                s.get("resource_id"),
                s.get("operation"),
                s.get("state"),
                s.get("evidence_id", ""),
            )

        gold_full = [full_tuple(s) for s in gold_steps]
        pred_full = [full_tuple(s) for s in pred_steps]
        gold_reach_full = [full_tuple(s) for s in reachable_gold_steps]

        gold_set = set(gold_full)
        pred_set = set(pred_full)
        gold_reach_set = set(gold_reach_full)

        tp = len(gold_set & pred_set)
        total_matched_steps += tp
        total_gold_steps += len(gold_set)
        total_pred_steps += len(pred_set)

        reach_tp = len(gold_reach_set & pred_set)
        reachable_matched_steps += reach_tp
        reachable_gold_steps_total += len(gold_reach_set)

        # 3. Exact sequence match
        seq_match = (gold_full == pred_full)
        if seq_match:
            exact_sequence_matches += 1

        reach_seq_match = (gold_reach_full == pred_full)
        if reach_seq_match:
            reachable_sequence_matches += 1

        p = tp / len(pred_set) if pred_set else (1.0 if not gold_set else 0.0)
        r = tp / len(gold_set) if gold_set else (1.0 if not pred_set else 0.0)
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0

        reach_p = reach_tp / len(pred_set) if pred_set else (1.0 if not gold_reach_set else 0.0)
        reach_r = reach_tp / len(gold_reach_set) if gold_reach_set else (1.0 if not pred_set else 0.0)
        reach_f1 = 2 * reach_p * reach_r / (reach_p + reach_r) if (reach_p + reach_r) > 0 else 0.0

        # --- Failure Taxonomy Classification (Reachable-only) ---
        case_taxonomy: List[Tuple[str, str, dict]] = []
        if not reach_seq_match and set(gold_reach_full) == set(pred_full):
            case_taxonomy.append(("ORDER_ONLY", cid, {"msg": "Identical step set, order differs"}))
        else:
            gold_by_key = {(s["system_id"], s["resource_id"], s["phase"]): s for s in reachable_gold_steps}
            pred_by_key = {(s["system_id"], s["resource_id"], s["phase"]): s for s in pred_steps}

            all_keys = set(gold_by_key.keys()) | set(pred_by_key.keys())
            discovered_res = case_res.resources
            gold_all_res = {s["resource_id"] for s in reachable_gold_steps}

            for key in sorted(all_keys):
                g_step = gold_by_key.get(key)
                p_step = pred_by_key.get(key)

                if g_step and p_step:
                    if g_step.get("operation") == p_step.get("operation") and g_step.get("state") == p_step.get("state"):
                        if g_step.get("evidence_id", "") != p_step.get("evidence_id", ""):
                            case_taxonomy.append(("EVIDENCE_ONLY", cid, {
                                "resource": key[1],
                                "phase": key[2],
                                "gold_ev": g_step.get("evidence_id"),
                                "pred_ev": p_step.get("evidence_id"),
                                "step": g_step
                            }))
                    else:
                        case_taxonomy.append(("STATE_OR_OP", cid, {
                            "resource": key[1],
                            "phase": key[2],
                            "gold_op_state": (g_step.get("operation"), g_step.get("state")),
                            "pred_op_state": (p_step.get("operation"), p_step.get("state")),
                            "step": g_step
                        }))
                elif g_step and not p_step:
                    res_id = key[1]
                    if res_id not in discovered_res:
                        case_taxonomy.append(("MISSING_RESOURCE", cid, {"resource": res_id, "phase": key[2], "gold_step": g_step}))
                    else:
                        case_taxonomy.append(("MISSING_STEP", cid, {"resource": res_id, "phase": key[2], "gold_step": g_step}))
                elif p_step and not g_step:
                    res_id = key[1]
                    if res_id not in gold_all_res:
                        case_taxonomy.append(("EXTRA_RESOURCE", cid, {"resource": res_id, "phase": key[2], "pred_step": p_step}))
                    else:
                        case_taxonomy.append(("EXTRA_STEP", cid, {"resource": res_id, "phase": key[2], "pred_step": p_step}))

        results_table.append({
            "case_id": cid,
            "status_match": status_match,
            "pred_status": pred_status,
            "gold_status": gold_status,
            "precision": p,
            "recall": r,
            "f1": f1,
            "seq_match": seq_match,
            "reach_seq_match": reach_seq_match,
            "reach_precision": reach_p,
            "reach_recall": reach_r,
            "reach_f1": reach_f1,
            "pred_steps": pred_steps,
            "gold_steps": gold_steps,
            "reachable_gold_steps": reachable_gold_steps,
            "taxonomy": case_taxonomy,
        })

    # Summary calculations
    num_cases = len(cases_to_eval)
    status_acc = (correct_status / num_cases) * 100.0 if num_cases else 0.0
    seq_acc = (exact_sequence_matches / num_cases) * 100.0 if num_cases else 0.0
    overall_p = total_matched_steps / total_pred_steps if total_pred_steps else 0.0
    overall_r = total_matched_steps / total_gold_steps if total_gold_steps else 0.0
    overall_f1 = (2 * overall_p * overall_r / (overall_p + overall_r)) * 100.0 if (overall_p + overall_r) > 0 else 0.0

    # Reachable summary
    reach_seq_acc = (reachable_sequence_matches / num_cases) * 100.0 if num_cases else 0.0
    overall_reach_p = reachable_matched_steps / total_pred_steps if total_pred_steps else 0.0
    overall_reach_r = reachable_matched_steps / reachable_gold_steps_total if reachable_gold_steps_total else 0.0
    overall_reach_f1 = (2 * overall_reach_p * overall_reach_r / (overall_reach_p + overall_reach_r)) * 100.0 if (overall_reach_p + overall_reach_r) > 0 else 0.0

    # Aggregate failure taxonomy counts
    bucket_counts: Dict[str, int] = {
        "EVIDENCE_ONLY": 0,
        "STATE_OR_OP": 0,
        "MISSING_RESOURCE": 0,
        "MISSING_STEP": 0,
        "EXTRA_RESOURCE": 0,
        "EXTRA_STEP": 0,
        "ORDER_ONLY": 0,
    }
    bucket_examples: Dict[str, List[dict]] = {k: [] for k in bucket_counts}

    for res in results_table:
        for b_name, cid, details in res["taxonomy"]:
            bucket_counts[b_name] = bucket_counts.get(b_name, 0) + 1
            if len(bucket_examples[b_name]) < 5:
                bucket_examples[b_name].append({"case_id": cid, **details})

    print("\n" + "=" * 75)
    print(f"EVALUATION SUMMARY ({num_cases} cases)")
    print("=" * 75)
    print(f"{'Metric':<25} | {'Raw (All Gold)':<22} | {'Reachable-Only Gold':<22}")
    print("-" * 75)
    print(f"{'Case Status Accuracy':<25} | {correct_status}/{num_cases} ({status_acc:.1f}%)" + " " * 9 + f"| {correct_status}/{num_cases} ({status_acc:.1f}%)")
    print(f"{'Sequence Accuracy':<25} | {exact_sequence_matches}/{num_cases} ({seq_acc:.1f}%)" + " " * 9 + f"| {reachable_sequence_matches}/{num_cases} ({reach_seq_acc:.1f}%)")
    print(f"{'Step Precision':<25} | {overall_p * 100:.1f}%" + " " * 16 + f"| {overall_reach_p * 100:.1f}%")
    print(f"{'Step Recall':<25} | {overall_r * 100:.1f}%" + " " * 16 + f"| {overall_reach_r * 100:.1f}%")
    print(f"{'Step F1 Score':<25} | {overall_f1:.1f}%" + " " * 16 + f"| {overall_reach_f1:.1f}%")
    print("=" * 75)

    print("\n" + "=" * 75)
    print("REACHABLE FAILURE TAXONOMY BREAKDOWN")
    print("=" * 75)
    print(f"{'Failure Bucket':<20} | {'Count':<8} | {'Impact / Example Cases'}")
    print("-" * 75)
    for b_name, count in sorted(bucket_counts.items(), key=lambda x: -x[1]):
        examples = bucket_examples[b_name]
        case_ids = ", ".join(sorted(list(set(e["case_id"] for e in examples))))
        print(f"{b_name:<20} | {count:<8} | Cases: {case_ids if case_ids else 'None'}")
    print("=" * 75)

    # Print detailed examples for each bucket
    print("\nDETAILED FAILURE EXAMPLES:")
    for b_name, examples in bucket_examples.items():
        if not examples:
            continue
        print(f"\n--- {b_name} ({bucket_counts[b_name]} total) ---")
        for ex in examples[:3]:
            cid = ex["case_id"]
            if b_name == "EVIDENCE_ONLY":
                print(f"  [{cid}] {ex['resource']} ({ex['phase']}): Gold='{ex['gold_ev']}' vs Pred='{ex['pred_ev']}'")
            elif b_name == "STATE_OR_OP":
                print(f"  [{cid}] {ex['resource']} ({ex['phase']}): Gold={ex['gold_op_state']} vs Pred={ex['pred_op_state']}")
            elif b_name in ("MISSING_RESOURCE", "MISSING_STEP"):
                print(f"  [{cid}] {ex['resource']} ({ex['phase']}): Missing operation {ex['gold_step']['operation']}")
            elif b_name in ("EXTRA_RESOURCE", "EXTRA_STEP"):
                print(f"  [{cid}] {ex['resource']} ({ex['phase']}): Extra operation {ex['pred_step']['operation']}")
            elif b_name == "ORDER_ONLY":
                print(f"  [{cid}]: {ex['msg']}")

    return {
        "num_cases": num_cases,
        "status_accuracy": status_acc,
        "sequence_accuracy": seq_acc,
        "reachable_sequence_accuracy": reach_seq_acc,
        "step_f1": overall_f1,
        "reachable_step_f1": overall_reach_f1,
        "bucket_counts": bucket_counts,
        "results": results_table,
    }

    # Print table of results
    if verbose or target_case:
        print("\nCase Breakdown:")
        for res in results_table:
            status_mark = "✓" if res["status_match"] else "✗"
            seq_mark = "✓" if res["seq_match"] else "✗"
            print(
                f"{res['case_id']}: Status [{status_mark}] {res['pred_status']:12} (gold: {res['gold_status']:12}) | "
                f"F1: {res['f1']*100:5.1f}% | Seq: [{seq_mark}]"
            )
            if not res["status_match"] or res["f1"] < 1.0 or verbose:
                pred_ops = [(s["phase"], s["resource_id"], s["operation"]) for s in res["pred_steps"]]
                gold_ops = [(s["phase"], s["resource_id"], s["operation"]) for s in res["gold_steps"]]
                print(f"   Expected: {gold_ops}")
                print(f"   Actual  : {pred_ops}")

    return {
        "num_cases": num_cases,
        "status_accuracy": status_acc,
        "sequence_accuracy": seq_acc,
        "step_f1": overall_f1,
        "results": results_table,
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate Agent against sample dataset.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print detailed step comparisons")
    parser.add_argument("--case", type=str, default=None, help="Evaluate a specific case ID")
    args = parser.parse_args()

    evaluate_samples(verbose=args.verbose, target_case=args.case)


if __name__ == "__main__":
    main()
