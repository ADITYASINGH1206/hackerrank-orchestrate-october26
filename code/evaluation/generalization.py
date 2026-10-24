"""
Generalization validation suite:
1. 3-Fold Cross-Validation on sample cases
2. Generation of 20 detailed case dossiers for hidden evaluation cases
3. Distribution shift comparison between 32 sample cases and 518 evaluation cases
"""

import csv
import json
import random
import sys
from pathlib import Path
from typing import Dict, List, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from code.config import (
    DELETION_REQUESTS_CSV,
    SAMPLE_DELETION_REQUESTS_CSV,
    SAMPLE_OUTPUT_CSV,
)
from code.core.store import ObservationStore
from code.core.identity import resolve_identity
from code.core.discovery import discover_resources_for_case
from code.core.planner import plan_case
from code.evaluation.main import UNREACHABLE_RESOURCE_IDS

DOSSIERS_DIR = Path("code/evaluation/dossiers")
DOSSIERS_DIR.mkdir(parents=True, exist_ok=True)


def run_cross_validation(store: ObservationStore) -> Dict[str, Any]:
    """Run 3-fold cross validation on 32 sample cases."""
    with open(SAMPLE_DELETION_REQUESTS_CSV, "r", encoding="utf-8") as f:
        requests = list(csv.DictReader(f))
    with open(SAMPLE_OUTPUT_CSV, "r", encoding="utf-8") as f:
        gold_data = {
            r["case_id"]: (r["deletion_status"], json.loads(r["steps_json"]))
            for r in csv.DictReader(f)
        }

    random.seed(42)
    shuffled = list(requests)
    random.shuffle(shuffled)

    folds = [shuffled[0:11], shuffled[11:22], shuffled[22:32]]
    fold_scores = []

    for fold_idx, test_set in enumerate(folds):
        status_correct = 0
        seq_matches = 0
        total_p, total_r = 0, 0
        tp, pred_cnt, gold_cnt = 0, 0, 0

        for req in test_set:
            cid = req["case_id"]
            gold_status, gold_steps = gold_data[cid]
            gold_reach = [s for s in gold_steps if s.get("resource_id") not in UNREACHABLE_RESOURCE_IDS]

            case_res = discover_resources_for_case(req, store)
            pred_status, pred_steps = plan_case(req, case_res)

            if pred_status == gold_status:
                status_correct += 1

            g_full = [(s["phase"], s["system_id"], s["resource_id"], s["operation"], s["state"], s.get("evidence_id", "")) for s in gold_reach]
            p_full = [(s["phase"], s["system_id"], s["resource_id"], s["operation"], s["state"], s.get("evidence_id", "")) for s in pred_steps]

            if g_full == p_full:
                seq_matches += 1

            g_set = set(g_full)
            p_set = set(p_full)
            tp += len(g_set & p_set)
            pred_cnt += len(p_set)
            gold_cnt += len(g_set)

        n = len(test_set)
        p = tp / pred_cnt if pred_cnt else 1.0
        r = tp / gold_cnt if gold_cnt else 1.0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0

        fold_scores.append({
            "fold": fold_idx + 1,
            "count": n,
            "status_accuracy": status_correct / n * 100.0,
            "seq_accuracy": seq_matches / n * 100.0,
            "precision": p * 100.0,
            "recall": r * 100.0,
            "f1": f1 * 100.0,
        })

    return {"fold_scores": fold_scores}


def generate_dossiers(store: ObservationStore, num_cases: int = 20) -> List[str]:
    """Generate 20 comprehensive case dossiers for hidden evaluation cases."""
    with open(DELETION_REQUESTS_CSV, "r", encoding="utf-8") as f:
        hidden_cases = list(csv.DictReader(f))

    random.seed(42)
    selected_cases = random.sample(hidden_cases, num_cases)
    generated_files = []

    for case in selected_cases:
        cid = case["case_id"]
        email = case["email"].lower()
        ident = resolve_identity(email, store)
        case_res = discover_resources_for_case(case, store)
        status, steps = plan_case(case, case_res)

        dossier_path = DOSSIERS_DIR / f"{cid}_dossier.md"
        content = [
            f"# Audit Dossier: {cid}",
            f"",
            f"## Case Metadata",
            f"- **Email**: `{case['email']}`",
            f"- **Requested At**: `{case['requested_at']}`",
            f"- **Reported Status**: `{case['reported_status']}`",
            f"- **Reported At**: `{case['reported_at']}`",
            f"- **Audit Cutoff**: `{case['audit_at']}`",
            f"- **Request Text**: *\"{case['request_text']}\"*",
            f"",
            f"## Identity Resolution",
            f"- **User ID**: `{ident.user_id}`",
            f"- **Emails**: {sorted(list(ident.emails))}",
            f"- **Historical Audit Changes**: {len(store.audit_logs_by_user_id.get(ident.user_id, []))}",
            f"- **Phones**: {sorted(list(ident.phones))}",
            f"- **Hashes**: {sorted(list(ident.email_hashes))}",
            f"",
            f"## Discovered Resources",
            f"- **Primary Account**: `{case_res.primary_account}`",
            f"- **Security Audit Record**: `{case_res.audit_record}`",
            f"- **All Discovered Resources ({len(case_res.resources)})**: {sorted(list(case_res.resources))}",
            f"",
            f"## Audit Verdict & Plan",
            f"- **Determined Status**: **`{status}`**",
            f"- **Step Count**: `{len(steps)}`",
            f"",
            f"### Plan Steps",
            f"```json",
            json.dumps(steps, indent=2),
            f"```",
            f"",
            f"## Grounding Observations",
        ]

        # Gather relevant observations
        for r in sorted(list(case_res.resources)):
            obs_list = [o for o in store.observations_by_resource.get(r, []) if o.captured_at <= case["audit_at"]]
            content.append(f"### Resource: `{r}` ({len(obs_list)} observations)")
            for obs in obs_list[:3]:
                content.append(f"- **File**: `{obs.file_id}` (captured: `{obs.captured_at}`) | System: `{obs.system_id}` | Exists: `{obs.exists}` | Flags: `{obs.flags}`")

        dossier_path.write_text("\n".join(content), encoding="utf-8")
        generated_files.append(str(dossier_path))

    return generated_files


def compare_distributions(store: ObservationStore) -> Dict[str, Any]:
    """Compare distributions between 32 sample cases and 518 evaluation cases."""
    with open(SAMPLE_DELETION_REQUESTS_CSV, "r", encoding="utf-8") as f:
        samples = list(csv.DictReader(f))
    with open(DELETION_REQUESTS_CSV, "r", encoding="utf-8") as f:
        full_cases = list(csv.DictReader(f))

    def profile_set(cases_list):
        status_counts = {"COMPLETE": 0, "INCOMPLETE": 0, "NOT_APPLICABLE": 0}
        total_steps = 0
        systems_touched = set()
        needs_historical = 0
        needs_img_pdf = 0

        img_pdf_files = {
            row["file_id"]
            for row in csv.DictReader(open("dataset/evidence_files.csv"))
            if "images/" in row["file_path"] or "documents/" in row["file_path"]
        }

        for c in cases_list:
            ident = resolve_identity(c["email"].lower(), store)
            if ident.user_id and store.audit_logs_by_user_id.get(ident.user_id):
                needs_historical += 1

            case_res = discover_resources_for_case(c, store)
            status, steps = plan_case(c, case_res)
            status_counts[status] = status_counts.get(status, 0) + 1
            total_steps += len(steps)
            for s in steps:
                systems_touched.add(s["system_id"])
                if s.get("evidence_id") in img_pdf_files:
                    needs_img_pdf += 1

        n = len(cases_list)
        return {
            "total_cases": n,
            "status_mix": {k: f"{v/n*100:.1f}% ({v})" for k, v in status_counts.items()},
            "avg_steps_per_case": total_steps / n if n else 0.0,
            "unique_systems": sorted(list(systems_touched)),
            "pct_requiring_historical_ident": f"{needs_historical/n*100:.1f}%",
            "pct_citing_img_or_pdf": f"{needs_img_pdf/n*100:.1f}%",
        }

    sample_dist = profile_set(samples)
    full_dist = profile_set(full_cases)

    return {
        "sample_distribution": sample_dist,
        "full_distribution": full_dist,
    }


if __name__ == "__main__":
    store = ObservationStore()
    store.load_all()

    print("Running 3-fold cross validation...")
    cv_res = run_cross_validation(store)
    print(json.dumps(cv_res, indent=2))

    print("\nGenerating 20 case dossiers...")
    dossiers = generate_dossiers(store, 20)
    print(f"Generated {len(dossiers)} dossiers in {DOSSIERS_DIR}")

    print("\nComputing distribution shift...")
    dist_res = compare_distributions(store)
    print(json.dumps(dist_res, indent=2))
