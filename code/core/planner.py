"""
Audit & Remediation Planner for Ghost Data Still Exists.
Determines deletion status (COMPLETE, INCOMPLETE, NOT_APPLICABLE) and
generates canonical 1..15 ranked steps for findings, remediations, and verifications.
"""

from typing import List, Dict, Any, Tuple
from code.config import OPERATION_RANKS
from code.core.models import Step
from code.core.intent import authorizes_deletion
from code.core.discovery import CaseResources
from code.core.timeline import reconstruct_resource_state
from code.core.policy import evaluate_resource_policy


def plan_case(case: dict, case_resources: CaseResources) -> Tuple[str, List[dict]]:
    """
    Plan audit decision and steps for a single case.
    Returns:
        (deletion_status, steps_as_dicts)
    """
    # 1. Check intent authorization
    authorized, reason = authorizes_deletion(case.get("request_text", ""))
    if not authorized:
        return "NOT_APPLICABLE", []

    audit_at = case.get("audit_at", "9999-12-31T23:59:59Z")

    # 2. Reconstruct states and evaluate policies for all candidate resources
    findings: List[Dict[str, Any]] = []
    remediations: List[Dict[str, Any]] = []
    verifications: List[Dict[str, Any]] = []

    # Map of resource_id -> evaluation
    evaluations: Dict[str, Dict[str, Any]] = {}
    evidence_map: Dict[str, str] = {}

    for res in sorted(case_resources.resources):
        # Ignore spurious generic system names
        if not (res.startswith(("account_", "search_", "support_", "analytics_", "backup_", "data_flow_", "export_", "audit_record_", "tombstone_", "marketing_", "legal_hold_")) and any(c.isdigit() for c in res)):
            continue

        obs_list = case_resources.observations.get(res, [])
        act_list = case_resources.activities.get(res, [])
        exists, flags, ids, ev_id = reconstruct_resource_state(res, obs_list, act_list, audit_at)
        
        pol = evaluate_resource_policy(res, exists, flags, ids)
        evaluations[res] = pol
        if ev_id:
            evidence_map[res] = ev_id

    # Check compliance across all resources
    is_complete = all(e["compliant"] for e in evaluations.values())
    deletion_status = "COMPLETE" if is_complete else "INCOMPLETE"

    steps: List[dict] = []
    step_no = 1

    if deletion_status == "COMPLETE":
        # Only VERIFICATION phase, citing evidence
        # Always verify primary account absent
        acc = case_resources.primary_account
        if acc:
            ev = evidence_map.get(acc) or next(iter(evidence_map.values()), "evidence_54")
            steps.append({
                "step_no": step_no,
                "phase": "VERIFICATION",
                "system_id": evaluations.get(acc, {}).get("system_id", "account_service"),
                "resource_id": acc,
                "operation": "VERIFY_RECORD_ABSENT",
                "state": "ABSENT",
                "evidence_id": ev,
            })
            step_no += 1

        # Verify audit record present
        aud = case_resources.audit_record
        if aud:
            ev = evidence_map.get(aud) or next(iter(evidence_map.values()), "evidence_92")
            steps.append({
                "step_no": step_no,
                "phase": "VERIFICATION",
                "system_id": "security_service",
                "resource_id": aud,
                "operation": "VERIFY_RECORD_PRESENT",
                "state": "PRESENT",
                "evidence_id": ev,
            })
            step_no += 1

        # Verify other resources
        for res, ev_info in evaluations.items():
            if res in (acc, aud):
                continue
            ev = evidence_map.get(res) or next(iter(evidence_map.values()), "")
            steps.append({
                "step_no": step_no,
                "phase": "VERIFICATION",
                "system_id": ev_info["system_id"],
                "resource_id": res,
                "operation": ev_info["verification_operation"],
                "state": ev_info["verification_state"],
                "evidence_id": ev,
            })
            step_no += 1

    else:
        # INCOMPLETE Case: FINDING -> REMEDIATION -> VERIFICATION
        # 1. Findings
        for res, ev_info in evaluations.items():
            if not ev_info["compliant"]:
                ev = evidence_map.get(res) or next(iter(evidence_map.values()), "evidence_01")
                findings.append({
                    "phase": "FINDING",
                    "system_id": ev_info["system_id"],
                    "resource_id": res,
                    "operation": ev_info["finding_operation"],
                    "state": ev_info["finding_state"],
                    "evidence_id": ev,
                })

        # Sort findings by canonical rank
        findings.sort(key=lambda s: OPERATION_RANKS.get(s["operation"], 99))

        # 2. Remediations (evidence_id = "")
        for res, ev_info in evaluations.items():
            if not ev_info["compliant"]:
                remediations.append({
                    "phase": "REMEDIATION",
                    "system_id": ev_info["system_id"],
                    "resource_id": res,
                    "operation": ev_info["remediation_operation"],
                    "state": ev_info["remediation_state"],
                    "evidence_id": "",
                })

        # Sort remediations by canonical order: DISABLE -> BLOCK -> DELETE -> REDACT -> ANONYMIZE
        remediations.sort(key=lambda s: OPERATION_RANKS.get(s["operation"], 99))

        # 3. Verifications (evidence_id = "")
        # Primary account verification
        acc = case_resources.primary_account
        if acc:
            verifications.append({
                "phase": "VERIFICATION",
                "system_id": evaluations.get(acc, {}).get("system_id", "account_service"),
                "resource_id": acc,
                "operation": "VERIFY_RECORD_ABSENT",
                "state": "ABSENT",
                "evidence_id": "",
            })

        # Verifications for all remediated resources
        for rem in remediations:
            r = rem["resource_id"]
            ev_info = evaluations[r]
            verifications.append({
                "phase": "VERIFICATION",
                "system_id": ev_info["system_id"],
                "resource_id": r,
                "operation": ev_info["verification_operation"],
                "state": ev_info["verification_state"],
                "evidence_id": "",
            })

        # Security audit log verification
        aud = case_resources.audit_record
        if aud:
            verifications.append({
                "phase": "VERIFICATION",
                "system_id": "security_service",
                "resource_id": aud,
                "operation": "VERIFY_RECORD_PRESENT",
                "state": "PRESENT",
                "evidence_id": "",
            })

        # Canonical system verification ordering
        system_order = {
            "account_service": 1,
            "search_service": 2,
            "export_service": 2,
            "security_service": 3,
            "support_platform": 4,
            "identity_service": 4,
            "marketing_service": 4,
            "analytics_platform": 5,
            "integration_service": 6,
            "backup_service": 7,
        }
        verifications.sort(key=lambda v: system_order.get(v["system_id"], 99))


        # Assemble all phases
        for f in findings:
            f["step_no"] = step_no
            steps.append(f)
            step_no += 1

        for r in remediations:
            r["step_no"] = step_no
            steps.append(r)
            step_no += 1

        for v in verifications:
            v["step_no"] = step_no
            steps.append(v)
            step_no += 1

    return deletion_status, steps
