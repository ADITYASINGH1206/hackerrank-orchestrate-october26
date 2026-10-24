"""
Log evidence parser: handles key=value lines, JSON lines, syslog, and pipe-delimited log events.
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

from code.core.models import Observation
from code.core.categories import get_system_id

ISO_TIMESTAMP_RE = re.compile(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z)")
RESOURCE_PATTERN = re.compile(r"\b(account_\w+|search_\w+|data_flow_\w+|analytics_\w+|backup_\w+|support_\w+|export_\w+|audit_record_\w+|tombstone_\w+|marketing_\w+|legal_hold_\w+|object_\w+)\b")
KV_PATTERN = re.compile(r'(\w+)=(?:"([^"]*)"|(\S+))')


def load_log_evidence(file_path: Path, file_id: str, manifest_captured_at: str) -> List[Observation]:
    """Parse a .log evidence file into a list of Observations."""
    observations: List[Observation] = []
    
    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, raw_line in enumerate(f, 1):
            line = raw_line.strip()
            if not line:
                continue

            obs = parse_log_line(line, file_id, manifest_captured_at)
            if obs:
                observations.append(obs)

    return observations


def parse_log_line(line: str, file_id: str, manifest_captured_at: str) -> Optional[Observation]:
    """Parse a single log line into an Observation if it concerns a resource."""
    # 1. Extract line timestamp
    observed_at = None
    ts_match = ISO_TIMESTAMP_RE.search(line)
    if ts_match:
        observed_at = ts_match.group(1)

    kv: Dict[str, Any] = {}

    # Check if line is pure JSON or contains JSON
    if line.startswith("{") and line.endswith("}"):
        try:
            kv = json.loads(line)
        except Exception:
            kv = {}

    if not kv:
        # Extract all key=value pairs
        for k, qv, sqv in KV_PATTERN.findall(line):
            val = qv if qv is not None and qv != "" else sqv
            kv[k] = val

    # 2. Extract resource_id
    res_id = kv.get("resource_id") or kv.get("resource")
    if not res_id:
        m = RESOURCE_PATTERN.search(line)
        if m:
            res_id = m.group(1)

    if not res_id:
        return None

    # Clean resource_id if quoted
    res_id = str(res_id).strip("\"'")

    # 3. Determine existence and state
    exists: Optional[bool] = True
    flags: Dict[str, Any] = {}
    ids: Dict[str, Any] = {}

    event = kv.get("event") or ""
    if event:
        flags["event"] = event

    # Check existence flags
    rows = kv.get("rows")
    http_status = kv.get("http_status")
    result = str(kv.get("result", "")).upper()
    total_hits = kv.get("total_hits")
    archive_present = str(kv.get("archive_present", "")).lower()
    available = str(kv.get("available", "")).lower()

    if rows is not None and str(rows) == "0":
        exists = False
    elif http_status is not None and str(http_status) in ("404", "410"):
        exists = False
    elif result in ("NOT_FOUND", "MISS"):
        exists = False
    elif total_hits is not None and str(total_hits) == "0":
        exists = False
    elif archive_present == "false" or available == "false":
        exists = False
    elif rows is not None and str(rows).isdigit() and int(rows) > 0:
        exists = True
    elif http_status is not None and str(http_status) == "200":
        exists = True
    elif result in ("FOUND", "HIT"):
        exists = True
    elif total_hits is not None and str(total_hits).isdigit() and int(total_hits) > 0:
        exists = True
    elif archive_present == "true" or available == "true":
        exists = True

    # Deletion marker check
    if "marker_found" in kv:
        mf = str(kv["marker_found"]).lower() == "true"
        flags["marker_found"] = mf
        if not mf:
            # Marker not found means deletion marker is missing -> record or old state alive
            exists = True

    # PII scan event
    if event == "message_pii_scan" or "matched_value" in kv:
        exists = True
        flags["pii_exposed"] = True
        mv = kv.get("matched_value", "")
        if "@" in mv:
            ids["email"] = mv

    # Other flags
    if "enabled" in kv:
        flags["enabled"] = str(kv["enabled"]).lower() == "true"
    if "restore_allowed" in kv:
        flags["restore_allowed"] = str(kv["restore_allowed"]).lower() == "true"
    if "retention_until" in kv:
        flags["retention_until"] = kv["retention_until"]
    if "deletion_block" in kv:
        flags["deletion_block"] = str(kv["deletion_block"]).lower() == "true"
    if "eligible" in kv:
        flags["eligible"] = str(kv["eligible"]).lower() == "true"

    # Extract identifiers
    for k in ("email", "customer_email", "owner_email", "requester_email", "lookup_key", "owner_key", "subject_key", "match_key"):
        if k in kv and kv[k] and "@" in str(kv[k]):
            ids["email"] = str(kv[k]).strip("\"'")
            break

    for k in ("phone", "owner_phone", "requester_phone"):
        if k in kv and kv[k] and str(kv[k]) != "null":
            ids["phone"] = str(kv[k]).strip("\"'")
            break

    for k in ("correlation_key", "email_hash"):
        if k in kv and kv[k] and str(kv[k]) != "null":
            ids["email_hash"] = str(kv[k]).strip("\"'")
            break

    for k in ("customer_reference", "subject_reference", "subject_ref", "user_id"):
        if k in kv and kv[k] and str(kv[k]) != "null":
            ids["user_id"] = str(kv[k]).strip("\"'")
            break

    for k in ("requester_name", "full_name", "display_name", "name"):
        if k in kv and kv[k] and str(kv[k]) != "null":
            ids["name"] = str(kv[k]).strip("\"'")
            break

    location = kv.get("service") or kv.get("logger") or "log"
    system_id = get_system_id(res_id, default_system=location)

    return Observation(
        file_id=file_id,
        captured_at=manifest_captured_at,
        system_id=system_id,
        location=location,
        resource_id=res_id,
        exists=exists,
        ids=ids,
        flags=flags,
        raw=kv,
        observed_at=observed_at or manifest_captured_at,
    )
