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

    results_table = []

    for cid in cases_to_eval:
        req = requests[cid]
        gold_status, gold_steps = gold_data[cid]

        # Run agent prediction
        case_res = discover_resources_for_case(req, store)
        pred_status, pred_steps = plan_case(req, case_res)

        # 1. Status match
        status_match = (pred_status == gold_status)
        if status_match:
            correct_status += 1

        # 2. Step matching (by tuple: phase, system_id, resource_id, operation, state)
        def step_tuple(s: dict):
            return (
                s.get("phase"),
                s.get("system_id"),
                s.get("resource_id"),
                s.get("operation"),
                s.get("state"),
            )

        gold_tuples = [step_tuple(s) for s in gold_steps]
        pred_tuples = [step_tuple(s) for s in pred_steps]

        gold_set = set(gold_tuples)
        pred_set = set(pred_tuples)

        tp = len(gold_set & pred_set)
        total_matched_steps += tp
        total_gold_steps += len(gold_set)
        total_pred_steps += len(pred_set)

        # 3. Exact sequence match
        seq_match = (gold_tuples == pred_tuples)
        if seq_match:
            exact_sequence_matches += 1

        p = tp / len(pred_set) if pred_set else (1.0 if not gold_set else 0.0)
        r = tp / len(gold_set) if gold_set else (1.0 if not pred_set else 0.0)
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0

        results_table.append({
            "case_id": cid,
            "status_match": status_match,
            "pred_status": pred_status,
            "gold_status": gold_status,
            "precision": p,
            "recall": r,
            "f1": f1,
            "seq_match": seq_match,
            "pred_steps": pred_steps,
            "gold_steps": gold_steps,
        })

    # Summary calculations
    num_cases = len(cases_to_eval)
    status_acc = (correct_status / num_cases) * 100.0 if num_cases else 0.0
    seq_acc = (exact_sequence_matches / num_cases) * 100.0 if num_cases else 0.0
    overall_p = total_matched_steps / total_pred_steps if total_pred_steps else 0.0
    overall_r = total_matched_steps / total_gold_steps if total_gold_steps else 0.0
    overall_f1 = (2 * overall_p * overall_r / (overall_p + overall_r)) * 100.0 if (overall_p + overall_r) > 0 else 0.0

    print("\n" + "=" * 70)
    print(f"EVALUATION SUMMARY ({num_cases} cases)")
    print("=" * 70)
    print(f"Case Status Accuracy : {correct_status}/{num_cases} ({status_acc:.1f}%)")
    print(f"Sequence Accuracy    : {exact_sequence_matches}/{num_cases} ({seq_acc:.1f}%)")
    print(f"Step Precision       : {overall_p * 100:.1f}%")
    print(f"Step Recall          : {overall_r * 100:.1f}%")
    print(f"Step F1 Score        : {overall_f1:.1f}%")
    print("=" * 70)

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
