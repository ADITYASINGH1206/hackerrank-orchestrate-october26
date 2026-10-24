"""
Data models for Ghost Data deletion-audit agent.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List


@dataclass
class Observation:
    file_id: str                      # e.g. "evidence_01"
    captured_at: str                  # ISO-8601 string from manifest or file
    system_id: str                    # e.g. "account_service", "search_service"
    location: str                     # table name, replica name, collection, log event
    resource_id: str                  # e.g. "account_005", "search_052"
    exists: Optional[bool]            # True: present, False: absent (404/NOT_FOUND), None: unknown
    ids: Dict[str, Any] = field(default_factory=dict)     # email, phone, hash, user_id, name
    flags: Dict[str, Any] = field(default_factory=dict)   # enabled, restore_allowed, pii_exposed, retention_until
    raw: Dict[str, Any] = field(default_factory=dict)     # original record / data
    observed_at: Optional[str] = None # fine-grained event timestamp if available

    @property
    def timestamp(self) -> str:
        return self.observed_at or self.captured_at


@dataclass
class Activity:
    activity_id: str
    event_time: str
    event_type: str
    source_system: str
    target_system: str
    resource_id: str
    reported_result: str
    details: str
    linked_resource: Optional[str] = None
    linked_email: Optional[str] = None
    linked_user: Optional[str] = None
    flags: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserIdentity:
    user_id: str
    name: str
    email: str
    phone: str
    email_hash: str
    updated_at: str


@dataclass
class UserAuditLog:
    audit_id: str
    user_id: str
    event_time: str
    field_name: str
    old_value: str
    new_value: str


@dataclass
class DeletionRule:
    rule_id: str
    data_category: str
    condition: str
    required_action: str


@dataclass
class EvidenceFile:
    file_id: str
    file_path: str
    origin: str
    captured_at: str


@dataclass
class Step:
    step_no: int
    phase: str
    system_id: str
    resource_id: str
    operation: str
    state: str
    evidence_id: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_no": self.step_no,
            "phase": self.phase,
            "system_id": self.system_id,
            "resource_id": self.resource_id,
            "operation": self.operation,
            "state": self.state,
            "evidence_id": self.evidence_id,
        }
