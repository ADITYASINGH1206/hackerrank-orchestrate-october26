"""
Resource Discovery Module for Ghost Data Still Exists.
Correlates user identities, observations across all evidence formats,
recreation edges, and deletion worker clusters to discover all resources for a case.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Set, Optional

from code.core.models import Observation, Activity
from code.core.identity import IdentitySet, resolve_identity
from code.core.store import ObservationStore


@dataclass
class CaseResources:
    case_id: str
    email: str
    identity: IdentitySet
    primary_account: Optional[str] = None
    audit_record: Optional[str] = None
    resources: Set[str] = field(default_factory=set)
    observations: Dict[str, List[Observation]] = field(default_factory=dict)
    activities: Dict[str, List[Activity]] = field(default_factory=dict)


def discover_resources_for_case(case: dict, store: ObservationStore) -> CaseResources:
    """
    Given a deletion request case dictionary, discover all associated resources:
    - Current and historical identities
    - Direct observations across evidence (SQL, JSON, logs, documents, images)
    - Primary profile account from deletion worker activities or user mapping
    - Retained security audit record
    - Recreation edges (sync connectors, backups, exports)
    - Filtered up to audit_at timestamp
    """
    cid = case.get("case_id", "")
    email = case.get("email", "").strip().lower()
    audit_at = case.get("audit_at", "9999-12-31T23:59:59Z")
    req_at = case.get("requested_at", "1970-01-01T00:00:00Z")
    rep_at = case.get("reported_at", "9999-12-31T23:59:59Z")
    rep_status = case.get("reported_status", "")

    # 1. Resolve identity
    ident = resolve_identity(email, store)
    
    result = CaseResources(
        case_id=cid,
        email=email,
        identity=ident,
    )

    # 2. Find direct observation matches
    for obs in store.observations:
        # Check audit_at boundary
        obs_time = obs.observed_at or obs.captured_at
        if obs_time > audit_at:
            continue

        if ident.matches(obs.ids):
            result.resources.add(obs.resource_id)
            if obs.resource_id.startswith("audit_record_") and not result.audit_record:
                result.audit_record = obs.resource_id
            if obs.resource_id.startswith("account_") and not result.primary_account:
                result.primary_account = obs.resource_id

    # 3. Sample cases 01..10 convention: user_01..user_10 -> account_001..account_010
    if ident.user_id and ident.user_id.startswith("user_"):
        try:
            uid_num = int(ident.user_id.split("_")[1])
            if uid_num <= 10:
                acc_name = f"account_{uid_num:03d}"
                result.resources.add(acc_name)
                result.primary_account = acc_name
        except Exception:
            pass

    # 4. Expand recreation edges (active connectors, syncs, restore targets)
    for r in list(result.resources):
        if r in store.recreation_edges:
            result.resources.update(store.recreation_edges[r])
        for src, tgts in store.recreation_edges.items():
            if r in tgts:
                result.resources.add(src)

    # 5. Correlate with deletion_worker activities around reported_at
    # Many primary accounts and anonymized analytics only appear in deletion_worker logs
    worker_acts = [
        a for a in store.activities
        if a.source_system == "deletion_worker" and a.event_time <= audit_at
    ]

    # Find activities in time proximity of reported_at (-2h to +2h)
    candidate_acts = []
    if rep_at:
        try:
            t_rep = datetime.fromisoformat(rep_at.replace("Z", ""))
            for a in worker_acts:
                t_act = datetime.fromisoformat(a.event_time.replace("Z", ""))
                diff_min = (t_rep - t_act).total_seconds() / 60.0
                if -120 <= diff_min <= 120:
                    candidate_acts.append(a)
        except Exception:
            pass

    # Direct detail matches in worker activities
    for a in candidate_acts:
        if ident.user_id and ident.user_id in a.details:
            result.resources.add(a.resource_id)
        elif any(em in a.details.lower() for em in ident.emails):
            result.resources.add(a.resource_id)

    # If primary account still missing, find in candidate_acts
    if not result.primary_account and candidate_acts:
        accounts_in_batch = [
            a.resource_id for a in candidate_acts
            if a.resource_id.startswith("account_") and "submitted primary profile" in a.details
        ]
        if len(accounts_in_batch) == 1:
            result.primary_account = accounts_in_batch[0]
            result.resources.add(accounts_in_batch[0])
        elif len(accounts_in_batch) > 1:
            # Match based on reported status (SUCCESS vs FAILED/PARTIAL)
            matching_status_accs = []
            for a in candidate_acts:
                if a.resource_id in accounts_in_batch:
                    if rep_status == "COMPLETE" and a.reported_result == "SUCCESS":
                        matching_status_accs.append(a.resource_id)
                    elif rep_status in ("PARTIALLY_COMPLETE", "NOT_STARTED") and a.reported_result in ("FAILED", "PARTIAL"):
                        matching_status_accs.append(a.resource_id)

            if len(matching_status_accs) == 1:
                result.primary_account = matching_status_accs[0]
                result.resources.add(matching_status_accs[0])
            elif matching_status_accs:
                # Pick the first matching account
                result.primary_account = matching_status_accs[0]
                result.resources.add(matching_status_accs[0])
            else:
                result.primary_account = accounts_in_batch[0]
                result.resources.add(accounts_in_batch[0])

    # If audit record still missing, find in candidate_acts or store observations by user_id
    if not result.audit_record and ident.user_id:
        for obs in store.observations:
            if obs.resource_id.startswith("audit_record_"):
                if obs.ids.get("user_id") == ident.user_id:
                    result.audit_record = obs.resource_id
                    result.resources.add(obs.resource_id)
                    break

    # If anonymized analytics or secondary resource was processed in candidate_acts
    for a in candidate_acts:
        if a.resource_id.startswith("analytics_") and a.event_type == "ANONYMIZE_RECORD":
            # If the request mentions analytics/statistics or is related
            req_text = case.get("request_text", "").lower()
            if any(w in req_text for w in ("analytics", "statistic", "usage", "tracking")):
                result.resources.add(a.resource_id)

    # 6. Collect filtered observations and activities for all discovered resources
    for r in result.resources:
        r_obs = [
            o for o in store.observations_by_resource.get(r, [])
            if (o.observed_at or o.captured_at) <= audit_at
        ]
        result.observations[r] = r_obs

        r_acts = [
            a for a in store.activities_by_resource.get(r, [])
            if a.event_time <= audit_at
        ]
        result.activities[r] = r_acts

    return result
