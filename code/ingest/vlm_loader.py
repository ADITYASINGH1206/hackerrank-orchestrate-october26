"""
VLM evidence loader (stub for Stage 1, returning empty list until Stage 8).
"""

from pathlib import Path
from typing import List
from code.core.models import Observation


def load_vlm_evidence(file_path: Path, file_id: str, manifest_captured_at: str) -> List[Observation]:
    """Stub loader for PNG screenshot evidence."""
    return []
