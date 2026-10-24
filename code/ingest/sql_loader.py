"""
SQL evidence loader: executes SQL dumps into in-memory SQLite and extracts observations.
"""

import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional

from code.core.models import Observation
from code.core.categories import get_system_id


def load_sql_evidence(file_path: Path, file_id: str, manifest_captured_at: str) -> List[Observation]:
    """Execute SQL dump into an in-memory SQLite database and extract observations for each table row."""
    observations = []
    
    with open(file_path, "r", encoding="utf-8") as f:
        sql_content = f.read()

    conn = sqlite3.connect(":memory:")
    try:
        conn.executescript(sql_content)
    except Exception as e:
        conn.close()
        raise RuntimeError(f"Failed to execute SQL for {file_id} ({file_path}): {e}")

    # Read snapshot_scope if present
    captured_at = manifest_captured_at
    try:
        scope_cur = conn.execute("SELECT captured_at FROM snapshot_scope LIMIT 1")
        scope_row = scope_cur.fetchone()
        if scope_row and scope_row[0]:
            captured_at = scope_row[0]
    except sqlite3.OperationalError:
        pass

    # Enumerate all tables
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

    for table in tables:
        if table == "snapshot_scope":
            continue

        cursor = conn.execute(f"SELECT * FROM {table}")
        col_names = [d[0] for d in cursor.description]

        for row in cursor.fetchall():
            row_dict = dict(zip(col_names, row))
            res_id = row_dict.get("resource_id")
            if not res_id:
                continue

            ids: Dict[str, Any] = {}
            flags: Dict[str, Any] = {}
            observed_at = row_dict.get("updated_at") or row_dict.get("indexed_at")

            # Check if there is an embedded JSON record
            if "record_json" in row_dict and row_dict["record_json"]:
                try:
                    inner_record = json.loads(row_dict["record_json"])
                    for k in ("email", "phone", "email_hash", "user_id", "customer_reference", "subject_reference"):
                        if inner_record.get(k):
                            ids[k] = inner_record[k]
                    for k in ("full_name", "display_name", "name"):
                        if inner_record.get(k):
                            ids["name"] = inner_record[k]
                    # Check for anonymization in record_json
                    if inner_record.get("email") is None and inner_record.get("phone") is None and inner_record.get("user_id") is None:
                        flags["anonymized"] = True
                except Exception:
                    pass

            # Extract standard ID fields
            for k in ("email", "customer_email", "owner_email", "requester_email"):
                if row_dict.get(k):
                    ids["email"] = row_dict[k]
                    break

            for k in ("phone", "owner_phone", "requester_phone"):
                if row_dict.get(k):
                    ids["phone"] = row_dict[k]
                    break

            for k in ("full_name", "display_name", "requester_name"):
                if row_dict.get(k):
                    ids["name"] = row_dict[k]
                    break

            for k in ("user_id", "customer_reference", "subject_reference"):
                if row_dict.get(k):
                    ids["user_id"] = row_dict[k]
                    break

            if row_dict.get("email_hash"):
                ids["email_hash"] = row_dict["email_hash"]

            # Extract flags
            if "enabled" in row_dict:
                flags["enabled"] = bool(row_dict["enabled"])
            if "restore_allowed" in row_dict:
                flags["restore_allowed"] = bool(row_dict["restore_allowed"])
            if "retention_until" in row_dict:
                flags["retention_until"] = row_dict["retention_until"]
            if "account_status" in row_dict:
                flags["account_status"] = row_dict["account_status"]
            if "last_delivery_status" in row_dict:
                flags["last_delivery_status"] = row_dict["last_delivery_status"]

            system_id = get_system_id(res_id)

            obs = Observation(
                file_id=file_id,
                captured_at=captured_at,
                system_id=system_id,
                location=table,
                resource_id=res_id,
                exists=True,
                ids=ids,
                flags=flags,
                raw=row_dict,
                observed_at=observed_at,
            )
            observations.append(obs)

    conn.close()
    return observations
