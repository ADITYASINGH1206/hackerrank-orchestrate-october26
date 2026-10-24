"""
Timeline Reconstruction Engine for Ghost Data Still Exists.
Determines the true operational state of each resource at the case's audit_at cutoff.
Ignores any evidence or events created after audit_at.
"""

from typing import List, Dict, Any, Tuple, Optional
from code.core.models import Observation, Activity


def reconstruct_resource_state(
    resource_id: str,
    observations: List[Observation],
    activities: List[Activity],
    audit_at: str,
) -> Tuple[Optional[bool], Dict[str, Any], Dict[str, Any], str]:
    """
    Establish resource state strictly at or before audit_at.
    Returns:
        (exists, flags, ids, evidence_id)
    """
    # 1. Filter observations up to audit_at
    valid_obs = [
        o for o in observations
        if (o.observed_at or o.captured_at) <= audit_at
    ]

    # Sort observations chronologically
    valid_obs.sort(key=lambda o: (o.observed_at or o.captured_at))

    exists: Optional[bool] = None
    flags: Dict[str, Any] = {}
    ids: Dict[str, Any] = {}
    evidence_id: str = ""

    # Merge observations in chronological order
    for obs in valid_obs:
        if obs.exists is not None:
            exists = obs.exists
        flags.update(obs.flags)
        ids.update(obs.ids)
        evidence_id = obs.file_id

    # 2. Check for replication drift:
    # If primary snapshot has exists=False, but a replica snapshot has exists=True,
    # the data remains un-deleted in replicas -> exists=True!
    has_present_replica = any(
        o.exists is True for o in valid_obs
        if "replica" in o.location.lower() or "replica" in o.system_id.lower()
    )
    if has_present_replica:
        exists = True

    # 3. Incorporate system activities up to audit_at
    valid_acts = [a for a in activities if a.event_time <= audit_at]
    valid_acts.sort(key=lambda a: a.event_time)

    for act in valid_acts:
        # Check repopulation syncs
        if act.event_type in ("SYNC_RECORD", "INDEX_RECORD") and act.reported_result == "SUCCESS":
            if "repopulated" in act.details.lower():
                exists = True
                flags["repopulated"] = True

        # Check deletion worker outcomes
        if act.source_system == "deletion_worker":
            if act.event_type == "CHECK_DATA_FLOW":
                if "remains enabled" in act.details.lower():
                    flags["enabled"] = True
            elif act.event_type == "CHECK_RESTORE_ACCESS":
                if "can still be requested" in act.details.lower():
                    flags["restore_allowed"] = True
            elif act.event_type == "DELETE_RECORD":
                if act.reported_result == "FAILED" and not resource_id.startswith("account_"):
                    if exists is None:
                        exists = True

    # 4. Fallback defaults by resource type if no explicit evidence exists
    if exists is None:
        if resource_id.startswith(("data_flow_", "backup_")):
            # Connectors and backups default to active unless evidence proves otherwise
            exists = True
        elif resource_id.startswith("audit_record_"):
            exists = True
        elif resource_id.startswith("account_"):
            exists = False  # Account absent unless observed in snapshot

    return exists, flags, ids, evidence_id
