"""
Manifest loader for evidence_files.csv.
"""

import csv
from pathlib import Path
from typing import Dict
from code.config import EVIDENCE_FILES_CSV, DATASET_DIR
from code.core.models import EvidenceFile


def load_manifest(manifest_path: Path = EVIDENCE_FILES_CSV) -> Dict[str, EvidenceFile]:
    """Load evidence_files.csv into a dictionary of file_id -> EvidenceFile."""
    manifest = {}
    with open(manifest_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ef = EvidenceFile(
                file_id=row["file_id"],
                file_path=str(DATASET_DIR / row["file_path"]),
                origin=row["origin"],
                captured_at=row["captured_at"],
            )
            manifest[ef.file_id] = ef
    return manifest
