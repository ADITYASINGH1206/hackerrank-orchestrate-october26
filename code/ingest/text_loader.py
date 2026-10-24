"""
Text evidence loader: parses shift handover text files with pipe-delimited records.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional

from code.core.models import Observation
from code.core.categories import get_system_id


def load_text_evidence(file_path: Path, file_id: str, manifest_captured_at: str) -> List[Observation]:
    """Parse pipe-delimited handover TXT file into a list of Observations."""
    observations: List[Observation] = []

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or not line.startswith("-"):
                continue

            # Strip leading '-' and split by '|'
            parts = [p.strip() for p in line.lstrip("-").split("|")]
            if len(parts) < 6:
                continue

            observed_at, sys_name, res_id, r_type, status, ident = parts[:6]

            ids: Dict[str, Any] = {}
            flags: Dict[str, Any] = {"record_type": r_type, "status": status}
            exists: Optional[bool] = True

            # Normalize and identify subject
            clean_ident = ident.strip()
            if "@" in clean_ident:
                ids["email"] = clean_ident.lower()
            elif clean_ident.startswith("user_"):
                ids["user_id"] = clean_ident
            elif clean_ident.lower() == "no direct identifier":
                flags["anonymized"] = True

            # Map status to existence and flags
            status_upper = status.upper()
            if status_upper in ("NOT_FOUND", "ABSENT"):
                exists = False
            elif status_upper in ("FOUND", "PRESENT"):
                exists = True
            elif status_upper == "IDENTIFIABLE":
                exists = True
                flags["pii_exposed"] = True
            elif status_upper == "ANONYMIZED":
                exists = True
                flags["anonymized"] = True
            elif status_upper == "ACTIVE":
                exists = True
                if r_type == "DATA_FLOW" or res_id.startswith("data_flow"):
                    flags["enabled"] = True
                elif r_type == "BACKUP_ARCHIVE" or res_id.startswith("backup"):
                    flags["restore_allowed"] = True
            elif status_upper in ("DISABLED", "INACTIVE"):
                exists = True
                flags["enabled"] = False
            elif status_upper == "BLOCKED":
                exists = True
                flags["restore_allowed"] = False

            system_id = get_system_id(res_id, default_system=sys_name)

            obs = Observation(
                file_id=file_id,
                captured_at=manifest_captured_at,
                system_id=system_id,
                location="shift_handover",
                resource_id=res_id,
                exists=exists,
                ids=ids,
                flags=flags,
                raw={"line": line, "type": r_type, "status": status, "ident": ident},
                observed_at=observed_at or manifest_captured_at,
            )
            observations.append(obs)

    return observations
