"""
Invariant tests validating contract adherence:
1. Deletion status enum validity
2. Sequential step numbers starting at 1
3. Phase ordering: FINDING -> REMEDIATION -> VERIFICATION
4. Incomplete cases have empty evidence_id for REMEDIATION and future VERIFICATION
5. Complete cases only contain VERIFICATION citing evidence captured <= audit_at
6. NOT_APPLICABLE cases have empty steps_json
"""

import csv
import json
from code.config import DELETION_REQUESTS_CSV
from code.core.store import ObservationStore
from code.core.discovery import discover_resources_for_case
from code.core.planner import plan_case


def test_invariants_across_evaluation_requests():
    store = ObservationStore()
    store.load_all()

    with open(DELETION_REQUESTS_CSV, "r", encoding="utf-8") as f:
        cases = list(csv.DictReader(f))

    assert len(cases) == 518, f"Expected 518 evaluation cases, got {len(cases)}"

    valid_statuses = {"COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"}
    valid_phases = {"FINDING", "REMEDIATION", "VERIFICATION"}

    # Test sample of 50 diverse cases
    for case in cases[:50]:
        audit_at = case["audit_at"]
        case_res = discover_resources_for_case(case, store)
        status, steps = plan_case(case, case_res)

        assert status in valid_statuses, f"Invalid status: {status}"

        if status == "NOT_APPLICABLE":
            assert steps == [], f"NOT_APPLICABLE must have empty steps, got {steps}"
            continue

        phase_order = {"FINDING": 1, "REMEDIATION": 2, "VERIFICATION": 3}
        current_phase_num = 0

        for idx, s in enumerate(steps, start=1):
            assert s["step_no"] == idx, f"Step numbering mismatch: expected {idx}, got {s['step_no']}"
            assert s["phase"] in valid_phases, f"Invalid phase: {s['phase']}"

            # Phase progression
            p_num = phase_order[s["phase"]]
            assert p_num >= current_phase_num, f"Invalid phase order regression: {s['phase']} after {current_phase_num}"
            current_phase_num = p_num

            # Incomplete cases: remediation and verification must have empty evidence_id
            if status == "INCOMPLETE":
                if s["phase"] in ("REMEDIATION", "VERIFICATION"):
                    assert s["evidence_id"] == "", f"Incomplete plan future step must have empty evidence_id, got {s['evidence_id']}"
            elif status == "COMPLETE":
                assert s["phase"] == "VERIFICATION", f"COMPLETE case cannot have {s['phase']}"
                assert s["evidence_id"] != "", "COMPLETE case verification must cite evidence"

                # Evidence must not be captured after audit_at
                file_info = store.manifest.get(s["evidence_id"])
                if file_info:
                    assert file_info.captured_at <= audit_at, (
                        f"Cited evidence {s['evidence_id']} captured at {file_info.captured_at} "
                        f"after audit cutoff {audit_at}"
                    )
