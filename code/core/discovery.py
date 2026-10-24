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
import re

VALID_RESOURCE_RE = re.compile(
    r"^(account_\d+|analytics_\d+|audit_record_\d+|backup_\d+|data_flow_\d+|export_\d+|search_\d+|support_\d+|tombstone_\d+|marketing_\d+|legal_hold_\d+|object_\d+)$"
)


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
            if VALID_RESOURCE_RE.match(obs.resource_id):
                result.resources.add(obs.resource_id)
                if obs.resource_id.startswith("audit_record_") and not result.audit_record:
                    result.audit_record = obs.resource_id
                if obs.resource_id.startswith("account_") and not result.primary_account:
                    result.primary_account = obs.resource_id

    # 3. Direct identity matches in identity_links and activities
    for link in store.identity_links:
        if (ident.user_id and link.get("user_id") == ident.user_id) or (link.get("email") in ident.emails):
            res_id = link.get("resource_id", "")
            if res_id.startswith("tombstone_") and rep_status == "NOT_STARTED":
                continue
            if VALID_RESOURCE_RE.match(res_id):
                result.resources.add(res_id)
                if res_id.startswith("audit_record_") and not result.audit_record:
                    result.audit_record = res_id
                if res_id.startswith("account_") and not result.primary_account:
                    result.primary_account = res_id

    for act in store.activities:
        if act.event_time > audit_at:
            continue
        matches = False
        if ident.user_id and (act.linked_user == ident.user_id or ident.user_id in act.details):
            matches = True
        elif act.linked_email and act.linked_email in ident.emails:
            matches = True
        elif any(em in act.details.lower() for em in ident.emails):
            matches = True

        if matches:
            res_id = act.resource_id or act.linked_resource or ""
            if res_id.startswith("tombstone_") and rep_status == "NOT_STARTED":
                continue
            if VALID_RESOURCE_RE.match(res_id):
                result.resources.add(res_id)
                if res_id.startswith("audit_record_") and not result.audit_record:
                    result.audit_record = res_id
                if res_id.startswith("account_") and not result.primary_account:
                    result.primary_account = res_id


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
                if -15.0 <= diff_min <= 120.0:
                    candidate_acts.append(a)
            candidate_acts.sort(key=lambda a: a.event_time)
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
            if a.resource_id.startswith("account_") and a.source_system == "deletion_worker" and ("submitted primary profile" in a.details or "Target resource" in a.details or "internal work" in a.details)
        ]
        # Filter out candidate accounts whose observations explicitly belong to another user
        viable_accounts = []
        for acc in accounts_in_batch:
            has_other_user = False
            for obs in store.observations_by_resource.get(acc, []):
                em = (obs.ids.get("email") or obs.raw.get("customer_email") or "").lower()
                uid = obs.ids.get("user_id") or obs.raw.get("customer_reference") or obs.raw.get("subject_reference")
                if uid and uid not in ("null", "none", "[redacted]") and ident.user_id and uid != ident.user_id:
                    has_other_user = True
                    break
                if em and em not in ("null", "none", "[redacted]"):
                    other_u = store.identities_by_email.get(em)
                    if other_u and ident.user_id and other_u.user_id != ident.user_id:
                        has_other_user = True
                        break
            if not has_other_user:
                viable_accounts.append(acc)

        accounts_in_batch = viable_accounts if viable_accounts else accounts_in_batch

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
                    elif rep_status == "PARTIALLY_COMPLETE" and a.reported_result == "PARTIAL":
                        matching_status_accs.append(a.resource_id)
                    elif rep_status == "NOT_STARTED" and a.reported_result == "FAILED":
                        matching_status_accs.append(a.resource_id)

            if len(matching_status_accs) == 1:
                result.primary_account = matching_status_accs[0]
            elif matching_status_accs:
                result.primary_account = matching_status_accs[0]
            else:
                result.primary_account = accounts_in_batch[0]
            
            result.resources.add(result.primary_account)
            for other_acc in accounts_in_batch:
                if other_acc != result.primary_account:
                    result.resources.discard(other_acc)

    # Link candidate activities mentioned in request text
    req_txt = case.get("request_text", "").lower()
    for a in candidate_acts:
        if a.resource_id.startswith("analytics_") and "analytic" in req_txt:
            if rep_status == "COMPLETE" and a.reported_result == "SUCCESS":
                result.resources.add(a.resource_id)
            elif rep_status != "COMPLETE":
                result.resources.add(a.resource_id)

    # If audit record still missing, find in store observations by user_id or subject_reference
    if not result.audit_record and ident.user_id:
        for obs in store.observations:
            if obs.resource_id.startswith("audit_record_"):
                uid_match = (
                    obs.ids.get("user_id") == ident.user_id or
                    obs.raw.get("subject_reference") == ident.user_id or
                    obs.ids.get("customer_reference") == ident.user_id
                )
                if uid_match:
                    result.audit_record = obs.resource_id
                    result.resources.add(obs.resource_id)
                    break

    # If primary account is in candidate_acts, associate immediate secondary resource in the same worker batch
    if result.primary_account:
        acc_idx = None
        for i, a in enumerate(candidate_acts):
            if a.resource_id == result.primary_account and a.source_system == "deletion_worker":
                acc_idx = i
                break
        if acc_idx is not None and acc_idx + 1 < len(candidate_acts):
            next_a = candidate_acts[acc_idx + 1]
            if not next_a.resource_id.startswith("account_") and VALID_RESOURCE_RE.match(next_a.resource_id):
                try:
                    t_acc = datetime.fromisoformat(candidate_acts[acc_idx].event_time.replace("Z", ""))
                    t_next = datetime.fromisoformat(next_a.event_time.replace("Z", ""))
                    diff_sec = abs((t_next - t_acc).total_seconds())
                    if diff_sec <= 1800:
                        if rep_status == "COMPLETE" and next_a.reported_result == "SUCCESS":
                            result.resources.add(next_a.resource_id)
                        elif rep_status in ("PARTIALLY_COMPLETE", "INCOMPLETE", "NOT_STARTED"):
                            result.resources.add(next_a.resource_id)
                except Exception:
                    pass

    # Filter out resources that explicitly belong to a different user
    clean_res = set()
    for r in result.resources:
        has_positive = False
        has_conflict = False
        for obs in store.observations_by_resource.get(r, []):
            em = (obs.ids.get("email") or obs.raw.get("customer_email") or "").lower()
            if em in ("null", "none", "[redacted]"):
                em = ""
            ph = obs.ids.get("phone") or ""
            if ph in ("null", "none", "[redacted]"):
                ph = ""
            uid = obs.ids.get("user_id") or obs.raw.get("customer_reference") or obs.raw.get("subject_reference")
            if uid in ("null", "none", "[redacted]"):
                uid = None
            if (em and em in ident.emails) or (ph and ph in ident.phones) or (uid and uid == ident.user_id):
                has_positive = True
            elif uid and ident.user_id and uid != ident.user_id:
                has_conflict = True
            elif em and em not in ident.emails:
                other_u = store.identities_by_email.get(em)
                if other_u and ident.user_id and other_u.user_id != ident.user_id:
                    has_conflict = True

        if has_positive:
            clean_res.add(r)
        elif not has_conflict:
            clean_res.add(r)
        else:
            if r == result.primary_account:
                result.primary_account = None
            if r == result.audit_record:
                result.audit_record = None

    result.resources = clean_res

    # 6. Fallback assignment from discovered resources
    accs = sorted([r for r in result.resources if r.startswith("account_")])
    if not result.primary_account and accs:
        result.primary_account = accs[0]

    auds = sorted([r for r in result.resources if r.startswith("audit_record_")])
    if not result.audit_record and auds:
        result.audit_record = auds[0]

    # Filter to canonical resource identifiers only
    result.resources = {r for r in result.resources if VALID_RESOURCE_RE.match(r)}
    if result.primary_account and not VALID_RESOURCE_RE.match(result.primary_account):
        result.primary_account = None
    if result.audit_record and not VALID_RESOURCE_RE.match(result.audit_record):
        result.audit_record = None

    # 7. Collect filtered observations and activities for all discovered resources
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
