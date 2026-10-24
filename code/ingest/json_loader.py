"""
JSON evidence loader: handles snapshot bundles, service exports, configs, and reports.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from code.core.models import Observation
from code.core.categories import get_system_id


def load_json_evidence(file_path: Path, file_id: str, manifest_captured_at: str) -> List[Observation]:
    """Parse JSON evidence file into a list of Observations."""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    observations: List[Observation] = []
    file_captured_at = data.get("captured_at") or data.get("exported_at") or manifest_captured_at

    # Variant 1: Snapshot bundle
    if "snapshots" in data:
        for snap in data["snapshots"]:
            snap_time = snap.get("captured_at") or file_captured_at
            data_store = snap.get("data_store", "data_store")
            collection = snap.get("collection", "collection")

            for rec in snap.get("records", []):
                obs = _parse_record(rec, file_id, snap_time, data_store, collection)
                if obs:
                    observations.append(obs)

    # Variant 2: Service resource export
    elif "service_exports" in data:
        for sys_name, collections in data["service_exports"].items():
            for col_name, rec_list in collections.items():
                for rec in rec_list:
                    obs = _parse_service_export_record(rec, file_id, file_captured_at, sys_name, col_name)
                    if obs:
                        observations.append(obs)

    # Variant 3: Analytics report
    elif "collection" in data and "records" in data:
        collection = data.get("collection", "analytics")
        source = data.get("source", "analytics_platform")
        for rec in data.get("records", []):
            obs = _parse_record(rec, file_id, file_captured_at, source, collection)
            if obs:
                observations.append(obs)

    # Variant 4: Generic records with origin / export
    elif "records" in data:
        origin = data.get("origin") or data.get("source") or "export_service"
        for rec in data.get("records", []):
            obs = _parse_record(rec, file_id, file_captured_at, origin, "records")
            if obs:
                observations.append(obs)

    return observations


def _parse_record(
    rec: Dict[str, Any],
    file_id: str,
    captured_at: str,
    default_system: str,
    location: str,
) -> Optional[Observation]:
    res_id = rec.get("resource_id")
    if not res_id:
        return None

    ids: Dict[str, Any] = {}
    flags: Dict[str, Any] = {}
    exists: Optional[bool] = True
    observed_at = rec.get("observed_at") or rec.get("recorded_at") or rec.get("created_at") or captured_at

    # Result checks
    result = str(rec.get("result", "")).upper()
    if result in ("NOT_FOUND", "MISS"):
        exists = False
    elif result in ("FOUND", "HIT"):
        exists = True

    # Nested documents (e.g. search documents)
    doc = rec.get("document", {})
    if isinstance(doc, dict) and doc:
        for k in ("email", "customer_reference", "display_name"):
            if doc.get(k):
                if k == "display_name":
                    ids["name"] = doc[k]
                elif k == "customer_reference":
                    ids["user_id"] = doc[k]
                else:
                    ids[k] = doc[k]

    # Extract ID fields
    for k in ("email", "customer_email", "owner_email", "requester_email", "uploaded_by", "subject_selector", "lookup_value"):
        if rec.get(k):
            ids["email"] = rec[k]
            break

    for k in ("phone", "owner_phone", "requester_phone"):
        if rec.get(k):
            ids["phone"] = rec[k]
            break

    for k in ("full_name", "display_name", "requester_name"):
        if rec.get(k):
            ids["name"] = rec[k]
            break

    for k in ("user_id", "customer_reference", "subject_reference"):
        if rec.get(k):
            ids["user_id"] = rec[k]
            break

    if rec.get("email_hash"):
        ids["email_hash"] = rec["email_hash"]

    # Check anonymization
    if "user_id" in rec and rec.get("user_id") is None and rec.get("email") is None and rec.get("phone") is None:
        flags["anonymized"] = True

    # Flags
    if "enabled" in rec:
        flags["enabled"] = bool(rec["enabled"])
    if "restore_allowed" in rec:
        flags["restore_allowed"] = bool(rec["restore_allowed"])
    if "download_available" in rec:
        flags["download_available"] = bool(rec["download_available"])
    if "retention_until" in rec or "retained_until" in rec:
        flags["retention_until"] = rec.get("retention_until") or rec.get("retained_until")
    if "file_name" in rec:
        flags["file_name"] = rec["file_name"]
    if "message_text" in rec or "message_excerpt" in rec:
        flags["message_text"] = rec.get("message_text") or rec.get("message_excerpt")

    system_id = get_system_id(res_id, default_system=default_system)

    return Observation(
        file_id=file_id,
        captured_at=captured_at,
        system_id=system_id,
        location=location,
        resource_id=res_id,
        exists=exists,
        ids=ids,
        flags=flags,
        raw=rec,
        observed_at=observed_at,
    )


def _parse_service_export_record(
    rec: Dict[str, Any],
    file_id: str,
    captured_at: str,
    system_name: str,
    collection_name: str,
) -> Optional[Observation]:
    res_id = rec.get("resource_id")
    if not res_id:
        return None

    ids: Dict[str, Any] = {}
    flags: Dict[str, Any] = {}
    exists: Optional[bool] = True
    observed_at = rec.get("observed_at") or captured_at

    # Account profile lookups
    if "status_code" in rec or "profile" in rec:
        status_code = rec.get("status_code")
        profile = rec.get("profile")
        if status_code == 404 or profile is None:
            exists = False
        else:
            exists = True
            if isinstance(profile, dict):
                if profile.get("email"): ids["email"] = profile["email"]
                if profile.get("phone"): ids["phone"] = profile["phone"]
                if profile.get("full_name"): ids["name"] = profile["full_name"]
                if profile.get("customer_reference") or profile.get("user_id"):
                    ids["user_id"] = profile.get("customer_reference") or profile.get("user_id")
                if profile.get("email_hash"): ids["email_hash"] = profile["email_hash"]

    # Search index queries
    elif "hits" in rec or "query" in rec:
        hits = rec.get("hits")
        total_hits = 0
        docs = []
        if isinstance(hits, dict):
            total_hits = hits.get("total", 0)
            docs = hits.get("documents", [])
        elif isinstance(hits, list):
            docs = hits
            total_hits = len(docs)
        elif isinstance(hits, int):
            total_hits = hits

        if total_hits == 0 or (hits is not None and not docs and isinstance(hits, dict)):
            exists = False
        else:
            exists = True
            if docs and isinstance(docs[0], dict):
                first_doc = docs[0]
                if first_doc.get("email"): ids["email"] = first_doc["email"]
                if first_doc.get("phone"): ids["phone"] = first_doc["phone"]
                if first_doc.get("display_name"): ids["name"] = first_doc["display_name"]
                if first_doc.get("customer_reference") or first_doc.get("user_id"):
                    ids["user_id"] = first_doc.get("customer_reference") or first_doc.get("user_id")
                if first_doc.get("email_hash"): ids["email_hash"] = first_doc["email_hash"]

        if rec.get("query") and not ids.get("email"):
            ids["email"] = rec["query"]

    # Other systems
    else:
        for k in ("email", "customer_email", "owner_email", "requester_email"):
            if rec.get(k): ids["email"] = rec[k]; break
        for k in ("phone", "owner_phone", "requester_phone"):
            if rec.get(k): ids["phone"] = rec[k]; break
        for k in ("full_name", "display_name", "requester_name"):
            if rec.get(k): ids["name"] = rec[k]; break
        for k in ("user_id", "customer_reference", "subject_reference"):
            if rec.get(k): ids["user_id"] = rec[k]; break
        if rec.get("email_hash"):
            ids["email_hash"] = rec["email_hash"]

        if "enabled" in rec:
            flags["enabled"] = bool(rec["enabled"])
        if "restore_allowed" in rec:
            flags["restore_allowed"] = bool(rec["restore_allowed"])
        if "retention_until" in rec:
            flags["retention_until"] = rec["retention_until"]

    system_id = get_system_id(res_id, default_system=system_name)

    return Observation(
        file_id=file_id,
        captured_at=captured_at,
        system_id=system_id,
        location=f"{system_name}.{collection_name}",
        resource_id=res_id,
        exists=exists,
        ids=ids,
        flags=flags,
        raw=rec,
        observed_at=observed_at,
    )
