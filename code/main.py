"""
Main entry point for Ghost Data Still Exists deletion audit agent.
Runs audit pipeline on evaluation requests and produces compliant output.csv.
"""

import sys
import argparse
import csv
import json
from pathlib import Path

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from code.config import (
    DELETION_REQUESTS_CSV,
    SAMPLE_DELETION_REQUESTS_CSV,
    FINAL_OUTPUT_CSV,
)
from code.core.store import ObservationStore
from code.core.discovery import discover_resources_for_case
from code.core.planner import plan_case


def run_pipeline(input_csv: Path, output_csv: Path, store: ObservationStore = None):
    """Run full deletion audit pipeline on input cases and produce output CSV."""
    if store is None:
        print("Initializing and loading ObservationStore...")
        store = ObservationStore()
        store.load_all()

    with open(input_csv, "r", encoding="utf-8") as f:
        cases = list(csv.DictReader(f))

    # Sort cases deterministically by case_id
    cases.sort(key=lambda c: int(c["case_id"].split("_")[-1]) if c["case_id"].split("_")[-1].isdigit() else c["case_id"])

    print(f"Processing {len(cases)} cases from {input_csv.name}...")

    results = []
    status_counts = {"COMPLETE": 0, "INCOMPLETE": 0, "NOT_APPLICABLE": 0}
    total_steps_count = 0

    for idx, case in enumerate(cases, start=1):
        case_id = case["case_id"]
        case_res = discover_resources_for_case(case, store)
        status, steps = plan_case(case, case_res)

        status_counts[status] = status_counts.get(status, 0) + 1
        total_steps_count += len(steps)

        # Ensure steps_json is empty array for NOT_APPLICABLE
        if status == "NOT_APPLICABLE":
            steps_json = "[]"
        else:
            steps_json = json.dumps(steps, separators=(",", ":"))

        results.append({
            "case_id": case_id,
            "deletion_status": status,
            "steps_json": steps_json,
        })

        if idx % 100 == 0 or idx == len(cases):
            print(f"  Processed {idx}/{len(cases)} cases...")

    # Write output CSV with exact required headers
    print(f"Writing {len(results)} rows to {output_csv}...")
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["case_id", "deletion_status", "steps_json"])
        writer.writeheader()
        writer.writerows(results)

    print("\n=== Execution Summary ===")
    print(f"Total cases evaluated: {len(results)}")
    print(f"Status breakdown: {status_counts}")
    print(f"Total steps planned: {total_steps_count}")
    print(f"Average steps per case: {total_steps_count / len(results):.2f}")
    print(f"Output successfully written to: {output_csv}")


def main():
    parser = argparse.ArgumentParser(description="Ghost Data Still Exists Deletion-Audit Agent")
    parser.add_argument("--samples", action="store_true", help="Run audit on sample_deletion_requests.csv")
    parser.add_argument("--input", type=str, help="Custom input CSV path")
    parser.add_argument("--output", type=str, help="Custom output CSV path")
    parser.add_argument("--inspect", type=str, help="Inspect history of a specific resource_id")
    args = parser.parse_args()

    store = ObservationStore()
    print("Loading observation store...")
    store.load_all()

    if args.inspect:
        print(store.inspect_resource(args.inspect))
        return

    input_file = Path(args.input) if args.input else (SAMPLE_DELETION_REQUESTS_CSV if args.samples else DELETION_REQUESTS_CSV)
    output_file = Path(args.output) if args.output else FINAL_OUTPUT_CSV

    run_pipeline(input_file, output_file, store)


if __name__ == "__main__":
    main()
