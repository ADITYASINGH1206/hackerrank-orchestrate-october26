"""
Main entry point for Ghost Data Still Exists deletion audit agent.
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from code.core.store import ObservationStore


def main():
    parser = argparse.ArgumentParser(description="Ghost Data Still Exists Deletion-Audit Agent")
    parser.add_argument("--inspect", type=str, help="Inspect history of a specific resource_id")
    parser.add_argument("--stats", action="store_true", help="Print observation store statistics")
    parser.add_argument("--no-llm", action="store_true", help="Run without calling external LLMs")
    args = parser.parse_args()

    # Initialize and load store
    store = ObservationStore()
    store.load_all()

    if args.inspect:
        print(store.inspect_resource(args.inspect))
        return

    # Print summary statistics
    sql_obs = sum(1 for o in store.observations if o.file_id in store.manifest and store.manifest[o.file_id].file_path.endswith(".sql"))
    json_obs = sum(1 for o in store.observations if o.file_id in store.manifest and store.manifest[o.file_id].file_path.endswith(".json"))
    log_obs = sum(1 for o in store.observations if o.file_id in store.manifest and store.manifest[o.file_id].file_path.endswith(".log"))
    txt_obs = sum(1 for o in store.observations if o.file_id in store.manifest and store.manifest[o.file_id].file_path.endswith(".txt"))

    print("=== Observation Store Ingestion Summary ===")
    print(f"Total observations: {len(store.observations)}")
    print(f"  SQL observations: {sql_obs}")
    print(f"  JSON observations: {json_obs}")
    print(f"  Log observations: {log_obs}")
    print(f"  Text observations: {txt_obs}")
    print(f"Total unique resources observed: {len(store.observations_by_resource)}")
    print(f"Total system activities: {len(store.activities)}")
    print(f"Total identities: {len(store.identities)}")
    print(f"Total audit logs: {len(store.audit_logs)}")
    print(f"Total deletion rules: {len(store.rules)}")

    # Check for evidence files with 0 observations
    zero_obs_files = [
        ef.file_id for ef in store.manifest.values()
        if len(store.observations_by_file.get(ef.file_id, [])) == 0
        and not ef.file_path.endswith(".pdf")
        and not ef.file_path.endswith(".png")
    ]
    if zero_obs_files:
        print(f"\nWarning: Evidence files yielding zero observations (excluding PDF/PNG): {zero_obs_files}")
    else:
        print("\nAll non-PDF/PNG evidence files yielded >0 observations.")


if __name__ == "__main__":
    main()
