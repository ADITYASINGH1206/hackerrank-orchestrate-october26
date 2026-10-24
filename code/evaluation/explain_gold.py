"""
Gold Explainer for Ghost Data Still Exists.
Reverse-engineers ground-truth patterns across all 32 sample cases in sample_output.csv:
1. Evidence selection candidate rules evaluation
2. Verification scope rules evaluation
3. Policy treatment rules evaluation (DELETE vs REDACT vs ANONYMIZE)
4. Sort order evaluation (string vs numeric)
"""

import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from code.config import SAMPLE_DELETION_REQUESTS_CSV, SAMPLE_OUTPUT_CSV
from code.core.store import ObservationStore
from code.core.identity import resolve_identity


def explain_gold():
    store = ObservationStore()
    print("Loading observation store...")
    store.load_all()

    requests: Dict[str, dict] = {}
    with open(SAMPLE_DELETION_REQUESTS_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            requests[row["case_id"]] = row

    gold_data: Dict[str, Tuple[str, List[dict]]] = {}
    with open(SAMPLE_OUTPUT_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            gold_data[row["case_id"]] = (
                row["deletion_status"],
                json.loads(row["steps_json"]),
            )

    # 1. Evaluate Evidence Selection Rules
    # Only steps with non-empty evidence_id in gold
    ev_rule_counts = {
        "rule_a_latest_captured_lte": 0,
        "rule_b_latest_captured_lt": 0,
        "rule_c_latest_observed_lte": 0,
        "rule_d_latest_activity_lte": 0,
        "rule_e_single_latest_file": 0,
    }
    total_ev_steps = 0
    ev_exceptions: List[dict] = []

    # 2. Scope rules
    in_scope_findings = 0
    in_scope_verifs = 0
    verif_system_counts = defaultdict(int)

    # 3. Treatment rules
    treatment_records: List[dict] = []

    # 4. Sort ordering pairs
    sort_pairs_string = 0
    sort_pairs_numeric = 0

    for cid in sorted(requests.keys()):
        req = requests[cid]
        audit_at = req["audit_at"]
        gold_status, gold_steps = gold_data[cid]
        ids = resolve_identity(req["email"], store)

        # For rule e: find all files covering any resource in case with captured_at <= audit_at
        case_files = []
        for s in gold_steps:
            r = s["resource_id"]
            for obs in store.observations_by_resource.get(r, []):
                if obs.captured_at <= audit_at:
                    case_files.append((obs.captured_at, obs.file_id))
        case_files.sort(reverse=True)
        single_latest_file = case_files[0][1] if case_files else ""

        for step in gold_steps:
            phase = step["phase"]
            res = step["resource_id"]
            gold_ev = step.get("evidence_id", "")

            # Check sort ordering inside same system & operation
            # (handled per-case below)

            if phase == "VERIFICATION":
                verif_system_counts[step["system_id"]] += 1

            if phase in ("FINDING", "REMEDIATION"):
                treatment_records.append({
                    "case_id": cid,
                    "phase": phase,
                    "system_id": step["system_id"],
                    "resource_id": res,
                    "operation": step["operation"],
                    "state": step["state"],
                })

            if not gold_ev:
                continue

            total_ev_steps += 1
            obs_list = store.observations_by_resource.get(res, [])
            act_list = store.activities_by_resource.get(res, [])

            # Candidate a: latest observation with captured_at <= audit_at
            obs_lte = [o for o in obs_list if o.captured_at <= audit_at]
            obs_lte.sort(key=lambda o: (o.captured_at, o.observed_at or "", o.file_id), reverse=True)
            cand_a = obs_lte[0].file_id if obs_lte else ""

            # Candidate b: latest observation with captured_at < audit_at
            obs_lt = [o for o in obs_list if o.captured_at < audit_at]
            obs_lt.sort(key=lambda o: (o.captured_at, o.observed_at or "", o.file_id), reverse=True)
            cand_b = obs_lt[0].file_id if obs_lt else ""

            # Candidate c: latest by observed timestamp <= audit_at
            obs_c = [o for o in obs_list if (o.observed_at or o.captured_at) <= audit_at]
            obs_c.sort(key=lambda o: (o.observed_at or o.captured_at, o.file_id), reverse=True)
            cand_c = obs_c[0].file_id if obs_c else ""

            # Candidate d: latest activity <= audit_at
            act_lte = [a for a in act_list if a.event_time <= audit_at]
            act_lte.sort(key=lambda a: a.event_time, reverse=True)
            cand_d = act_lte[0].activity_id if act_lte else ""

            # Check matches
            if cand_a == gold_ev:
                ev_rule_counts["rule_a_latest_captured_lte"] += 1
            if cand_b == gold_ev:
                ev_rule_counts["rule_b_latest_captured_lt"] += 1
            if cand_c == gold_ev:
                ev_rule_counts["rule_c_latest_observed_lte"] += 1
            if cand_d == gold_ev:
                ev_rule_counts["rule_d_latest_activity_lte"] += 1
            if single_latest_file == gold_ev:
                ev_rule_counts["rule_e_single_latest_file"] += 1

            if cand_a != gold_ev:
                ev_exceptions.append({
                    "case_id": cid,
                    "phase": phase,
                    "resource_id": res,
                    "gold_ev": gold_ev,
                    "cand_a": cand_a,
                    "all_obs": [(o.file_id, o.captured_at, o.observed_at, o.exists) for o in obs_list],
                    "all_acts": [(a.activity_id, a.event_time, a.event_type, a.reported_result) for a in act_list],
                })

        # Check numeric vs string sort within gold steps
        for i in range(len(gold_steps) - 1):
            s1 = gold_steps[i]
            s2 = gold_steps[i + 1]
            if s1["phase"] == s2["phase"] and s1["system_id"] == s2["system_id"] and s1["operation"] == s2["operation"]:
                r1 = s1["resource_id"]
                r2 = s2["resource_id"]
                # Extract trailing digits
                m1 = re.search(r"\d+", r1)
                m2 = re.search(r"\d+", r2)
                if m1 and m2:
                    n1, n2 = int(m1.group()), int(m2.group())
                    if n1 < n2:
                        sort_pairs_numeric += 1
                    if r1 < r2:
                        sort_pairs_string += 1

    print("\n" + "=" * 70)
    print("EVIDENCE SELECTION CANDIDATE RULES EVALUATION")
    print(f"Total steps citing evidence in gold: {total_ev_steps}")
    print("=" * 70)
    for r_name, count in ev_rule_counts.items():
        pct = (count / total_ev_steps) * 100.0 if total_ev_steps else 0.0
        print(f"{r_name:<30}: {count}/{total_ev_steps} ({pct:.1f}%)")
    print("=" * 70)

    print(f"\nExceptions for Rule A (latest captured_at <= audit_at): {len(ev_exceptions)}")
    for ex in ev_exceptions[:10]:
        print(f"\n[{ex['case_id']}] {ex['resource_id']} ({ex['phase']}): Gold='{ex['gold_ev']}' vs Cand_A='{ex['cand_a']}'")
        print(f"   Observations: {ex['all_obs']}")
        print(f"   Activities  : {ex['all_acts']}")

    print("\n" + "=" * 70)
    print("VERIFICATION SCOPE RULES (GOLD)")
    print("=" * 70)
    for sys_id, count in sorted(verif_system_counts.items(), key=lambda x: -x[1]):
        print(f"{sys_id:<25}: {count} verification steps")
    print("=" * 70)

    print("\n" + "=" * 70)
    print("SORT ORDERING IN GOLD (Same phase, system, operation):")
    print(f"Numeric matches: {sort_pairs_numeric}, String matches: {sort_pairs_string}")
    print("=" * 70)


if __name__ == "__main__":
    explain_gold()
