"""
Unified Observation Store: loads and indexes all evidence, activity, identities, and policies.
"""

import csv
import re
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
from collections import defaultdict

from code.config import (
    EVIDENCE_FILES_CSV,
    SYSTEM_ACTIVITY_CSV,
    USER_IDENTITIES_CSV,
    USER_AUDIT_LOG_CSV,
    DELETION_RULES_CSV,
)
from code.core.models import (
    Observation,
    Activity,
    UserIdentity,
    UserAuditLog,
    DeletionRule,
    EvidenceFile,
)
from code.ingest.manifest import load_manifest
from code.ingest.sql_loader import load_sql_evidence
from code.ingest.json_loader import load_json_evidence
from code.ingest.log_parser import load_log_evidence
from code.ingest.text_loader import load_text_evidence
from code.ingest.pdf_loader import load_pdf_evidence
from code.ingest.vlm_loader import load_vlm_evidence

REPOPULATION_RE = re.compile(r"(?:repopulated downstream resource|Target resource:?)\s+(\w+)", re.IGNORECASE)
LINK_IDENTITY_RE = re.compile(r"linked\s+(\w+)\s+.*?\s+to\s+(\S+@\S+)\s+and\s+(user_\d+)", re.IGNORECASE)
BELONGS_RE = re.compile(r"belongs only to\s+(\S+@\S+)\s+and\s+(user_\d+)", re.IGNORECASE)


class ObservationStore:
    def __init__(self):
        self.manifest: Dict[str, EvidenceFile] = {}
        self.observations: List[Observation] = []
        self.observations_by_resource: Dict[str, List[Observation]] = defaultdict(list)
        self.observations_by_file: Dict[str, List[Observation]] = defaultdict(list)

        self.activities: List[Activity] = []
        self.activities_by_resource: Dict[str, List[Activity]] = defaultdict(list)

        self.identities: Dict[str, UserIdentity] = {}                # user_id -> UserIdentity
        self.identities_by_email: Dict[str, UserIdentity] = {}       # normalized email -> UserIdentity
        self.identities_by_hash: Dict[str, UserIdentity] = {}        # email_hash -> UserIdentity

        self.audit_logs: List[UserAuditLog] = []
        self.audit_logs_by_user_id: Dict[str, List[UserAuditLog]] = defaultdict(list)
        self.audit_logs_by_email: Dict[str, List[UserAuditLog]] = defaultdict(list)

        self.rules: Dict[str, DeletionRule] = {}                     # data_category -> DeletionRule

        self.recreation_edges: Dict[str, Set[str]] = defaultdict(set) # source_res -> {target_res}
        self.identity_links: List[Dict[str, str]] = []

    def load_all(self):
        """Load manifest, evidence files, system activity, identities, audit log, and rules."""
        # 1. Manifest
        self.manifest = load_manifest(EVIDENCE_FILES_CSV)

        # 2. Evidence files
        for file_id, ef in self.manifest.items():
            f_path = Path(ef.file_path)
            if not f_path.exists():
                continue

            suffix = f_path.suffix.lower()
            file_obs: List[Observation] = []

            if suffix == ".sql":
                file_obs = load_sql_evidence(f_path, file_id, ef.captured_at)
            elif suffix == ".json":
                file_obs = load_json_evidence(f_path, file_id, ef.captured_at)
            elif suffix == ".log":
                file_obs = load_log_evidence(f_path, file_id, ef.captured_at)
            elif suffix == ".txt":
                file_obs = load_text_evidence(f_path, file_id, ef.captured_at)
            elif suffix == ".pdf":
                file_obs = load_pdf_evidence(f_path, file_id, ef.captured_at)
            elif suffix == ".png":
                file_obs = load_vlm_evidence(f_path, file_id, ef.captured_at)

            for obs in file_obs:
                self.observations.append(obs)
                self.observations_by_resource[obs.resource_id].append(obs)
                self.observations_by_file[file_id].append(obs)

        # Sort observations per resource chronologically
        for r_id in self.observations_by_resource:
            self.observations_by_resource[r_id].sort(key=lambda o: (o.timestamp, o.file_id))

        # 3. System activity
        with open(SYSTEM_ACTIVITY_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                d = row["details"]
                linked_res = None
                linked_email = None
                linked_user = None
                flags: Dict[str, Any] = {}

                # Regex parsing of details
                m_r = REPOPULATION_RE.search(d)
                if m_r:
                    linked_res = m_r.group(1)
                    self.recreation_edges[row["resource_id"]].add(linked_res)

                m_l = LINK_IDENTITY_RE.search(d)
                if m_l:
                    linked_res = m_l.group(1)
                    linked_email = m_l.group(2).lower()
                    linked_user = m_l.group(3)
                    self.identity_links.append({"resource_id": row["resource_id"], "email": linked_email, "user_id": linked_user})
                else:
                    m_b = BELONGS_RE.search(d)
                    if m_b:
                        linked_email = m_b.group(1).lower()
                        linked_user = m_b.group(2)
                        self.identity_links.append({"resource_id": row["resource_id"], "email": linked_email, "user_id": linked_user})

                if "remains enabled" in d.lower():
                    flags["remains_enabled"] = True
                if "can still be restored" in d.lower():
                    flags["can_still_be_restored"] = True
                if "non-deletion" in d.lower():
                    flags["non_deletion"] = True

                act = Activity(
                    activity_id=row["activity_id"],
                    event_time=row["event_time"],
                    event_type=row["event_type"],
                    source_system=row["source_system"],
                    target_system=row["target_system"],
                    resource_id=row["resource_id"],
                    reported_result=row["reported_result"],
                    details=row["details"],
                    linked_resource=linked_res,
                    linked_email=linked_email,
                    linked_user=linked_user,
                    flags=flags,
                )
                self.activities.append(act)
                self.activities_by_resource[act.resource_id].append(act)

        # Sort activities per resource chronologically
        for r_id in self.activities_by_resource:
            self.activities_by_resource[r_id].sort(key=lambda a: a.event_time)

        # 4. User identities
        with open(USER_IDENTITIES_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ui = UserIdentity(
                    user_id=row["user_id"],
                    name=row["name"],
                    email=row["email"].strip().lower(),
                    phone=row["phone"].strip(),
                    email_hash=row["email_hash"].strip(),
                    updated_at=row["updated_at"],
                )
                self.identities[ui.user_id] = ui
                self.identities_by_email[ui.email] = ui
                self.identities_by_hash[ui.email_hash] = ui

        # 5. User audit log
        with open(USER_AUDIT_LOG_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                al = UserAuditLog(
                    audit_id=row["audit_id"],
                    user_id=row["user_id"],
                    event_time=row["event_time"],
                    field_name=row["field_name"],
                    old_value=row["old_value"].strip(),
                    new_value=row["new_value"].strip(),
                )
                self.audit_logs.append(al)
                self.audit_logs_by_user_id[al.user_id].append(al)
                if al.field_name == "email":
                    self.audit_logs_by_email[al.old_value.lower()].append(al)
                    self.audit_logs_by_email[al.new_value.lower()].append(al)

        # 6. Deletion rules
        with open(DELETION_RULES_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rule = DeletionRule(
                    rule_id=row["rule_id"],
                    data_category=row["data_category"],
                    condition=row["condition"],
                    required_action=row["required_action"],
                )
                self.rules[rule.data_category] = rule

    def inspect_resource(self, resource_id: str) -> str:
        """Return formatted inspection history for a resource across evidence and activity."""
        lines = [f"=== Inspection for Resource: {resource_id} ==="]
        
        # Observations
        obs_list = self.observations_by_resource.get(resource_id, [])
        lines.append(f"\nObservations ({len(obs_list)}):")
        if not obs_list:
            lines.append("  (No direct observations found)")
        for obs in obs_list:
            state_str = "PRESENT" if obs.exists is True else ("ABSENT" if obs.exists is False else "UNKNOWN")
            lines.append(
                f"  [{obs.timestamp}] {obs.file_id} | {obs.system_id} | loc={obs.location} | "
                f"exists={state_str} | ids={obs.ids} | flags={obs.flags}"
            )

        # Activities
        act_list = self.activities_by_resource.get(resource_id, [])
        lines.append(f"\nActivities ({len(act_list)}):")
        if not act_list:
            lines.append("  (No system activities found)")
        for act in act_list:
            lines.append(
                f"  [{act.event_time}] {act.activity_id} | {act.event_type} | {act.source_system}->{act.target_system} | "
                f"result={act.reported_result} | details={act.details}"
            )

        # Recreation edges
        if resource_id in self.recreation_edges:
            lines.append(f"\nRecreation target edges: {self.recreation_edges[resource_id]}")

        # Check if resource is target of any recreation edge
        sources = [src for src, targets in self.recreation_edges.items() if resource_id in targets]
        if sources:
            lines.append(f"Recreation source origins: {sources}")

        return "\n".join(lines)
