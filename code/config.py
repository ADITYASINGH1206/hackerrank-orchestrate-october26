"""
Configuration and constants for Ghost Data Still Exists deletion audit agent.
"""

from pathlib import Path
import os

# Project Roots
REPO_ROOT = Path(__file__).resolve().parent.parent
CODE_DIR = REPO_ROOT / "code"
DATASET_DIR = REPO_ROOT / "dataset"
EVIDENCE_DIR = DATASET_DIR / "evidence"

# Dataset Files
DELETION_REQUESTS_CSV = DATASET_DIR / "deletion_requests.csv"
SAMPLE_DELETION_REQUESTS_CSV = DATASET_DIR / "sample_deletion_requests.csv"
SAMPLE_OUTPUT_CSV = DATASET_DIR / "sample_output.csv"
USER_IDENTITIES_CSV = DATASET_DIR / "user_identities.csv"
USER_AUDIT_LOG_CSV = DATASET_DIR / "user_audit_log.csv"
SYSTEM_ACTIVITY_CSV = DATASET_DIR / "system_activity.csv"
DELETION_RULES_CSV = DATASET_DIR / "deletion_rules.csv"
EVIDENCE_FILES_CSV = DATASET_DIR / "evidence_files.csv"
FINAL_OUTPUT_CSV = REPO_ROOT / "output.csv"

# Cache Directory
CACHE_DIR = CODE_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
(CACHE_DIR / "vlm").mkdir(parents=True, exist_ok=True)
(CACHE_DIR / "intent").mkdir(parents=True, exist_ok=True)

# Phase Order
PHASE_ORDER = ["FINDING", "REMEDIATION", "VERIFICATION"]

# Canonical Operation Order (1 to 15)
CANONICAL_OPERATIONS = [
    "REPORT_REMAINING_RECORD",      # FINDING, state PRESENT
    "REPORT_EXPOSED_PII",           # FINDING, state PRESENT
    "REPORT_ACTIVE_DATA_FLOW",      # FINDING, state ACTIVE
    "REPORT_RESTORE_RISK",          # FINDING, state ACTIVE
    "DISABLE_DATA_FLOW",            # REMEDIATION, state DISABLED
    "BLOCK_RESTORE",                # REMEDIATION, state BLOCKED
    "DELETE_RECORD",                # REMEDIATION, state ABSENT
    "REDACT_RECORD",                # REMEDIATION, state REDACTED
    "ANONYMIZE_RECORD",             # REMEDIATION, state ANONYMIZED
    "VERIFY_RECORD_ABSENT",         # VERIFICATION, state ABSENT
    "VERIFY_RECORD_PRESENT",        # VERIFICATION, state PRESENT
    "VERIFY_RECORD_REDACTED",       # VERIFICATION, state REDACTED
    "VERIFY_RECORD_ANONYMIZED",     # VERIFICATION, state ANONYMIZED
    "VERIFY_DATA_FLOW_DISABLED",    # VERIFICATION, state DISABLED
    "VERIFY_RESTORE_BLOCKED",       # VERIFICATION, state BLOCKED
]

OPERATION_RANK = {op: i + 1 for i, op in enumerate(CANONICAL_OPERATIONS)}

OPERATION_LEGAL_STATES = {
    "REPORT_REMAINING_RECORD": "PRESENT",
    "REPORT_EXPOSED_PII": "PRESENT",
    "REPORT_ACTIVE_DATA_FLOW": "ACTIVE",
    "REPORT_RESTORE_RISK": "ACTIVE",
    "DISABLE_DATA_FLOW": "DISABLED",
    "BLOCK_RESTORE": "BLOCKED",
    "DELETE_RECORD": "ABSENT",
    "REDACT_RECORD": "REDACTED",
    "ANONYMIZE_RECORD": "ANONYMIZED",
    "VERIFY_RECORD_ABSENT": "ABSENT",
    "VERIFY_RECORD_PRESENT": "PRESENT",
    "VERIFY_RECORD_REDACTED": "REDACTED",
    "VERIFY_RECORD_ANONYMIZED": "ANONYMIZED",
    "VERIFY_DATA_FLOW_DISABLED": "DISABLED",
    "VERIFY_RESTORE_BLOCKED": "BLOCKED",
}
