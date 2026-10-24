"""
Policy and Treatment Engine for Ghost Data Still Exists.
Maps data categories and conditions to required actions (DELETE, REDACT, ANONYMIZE, RETAIN, DISABLE, BLOCK).
Determines findings, remediations, and verifications for candidate resources.
"""

from typing import Dict, Any, Optional
from code.core.categories import get_system_id, get_data_category


def evaluate_resource_policy(
    resource_id: str,
    exists: Optional[bool],
    flags: Dict[str, Any],
    ids: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Given a resource and its state at audit_at, determine compliance against deletion_rules.csv.
    Returns:
        {
            "category": str,
            "required_action": str,
            "compliant": bool,
            "finding_operation": Optional[str],
            "finding_state": Optional[str],
            "remediation_operation": Optional[str],
            "remediation_state": Optional[str],
            "verification_operation": str,
            "verification_state": str,
        }
    """
    category = get_data_category(resource_id)
    system_id = get_system_id(resource_id)

    # 1. Active Data Flows / Connectors
    if resource_id.startswith("data_flow_"):
        is_enabled = flags.get("enabled", True)
        if is_enabled:
            return {
                "category": "ACTIVE_DATA_FLOW",
                "system_id": system_id,
                "required_action": "DISABLE",
                "compliant": False,
                "finding_operation": "REPORT_ACTIVE_DATA_FLOW",
                "finding_state": "ACTIVE",
                "remediation_operation": "DISABLE_DATA_FLOW",
                "remediation_state": "DISABLED",
                "verification_operation": "VERIFY_DATA_FLOW_DISABLED",
                "verification_state": "DISABLED",
            }
        else:
            return {
                "category": "ACTIVE_DATA_FLOW",
                "system_id": system_id,
                "required_action": "DISABLE",
                "compliant": True,
                "finding_operation": None,
                "finding_state": None,
                "remediation_operation": None,
                "remediation_state": None,
                "verification_operation": "VERIFY_DATA_FLOW_DISABLED",
                "verification_state": "DISABLED",
            }

    # 2. Backup Archives
    if resource_id.startswith("backup_"):
        restore_allowed = flags.get("restore_allowed", True)
        if restore_allowed:
            return {
                "category": "BACKUP_ARCHIVE",
                "system_id": system_id,
                "required_action": "BLOCK",
                "compliant": False,
                "finding_operation": "REPORT_RESTORE_RISK",
                "finding_state": "ACTIVE",
                "remediation_operation": "BLOCK_RESTORE",
                "remediation_state": "BLOCKED",
                "verification_operation": "VERIFY_RESTORE_BLOCKED",
                "verification_state": "BLOCKED",
            }
        else:
            return {
                "category": "BACKUP_ARCHIVE",
                "system_id": system_id,
                "required_action": "BLOCK",
                "compliant": True,
                "finding_operation": None,
                "finding_state": None,
                "remediation_operation": None,
                "remediation_state": None,
                "verification_operation": "VERIFY_RESTORE_BLOCKED",
                "verification_state": "BLOCKED",
            }

    # 3. Account Tombstones
    if resource_id.startswith("tombstone_"):
        pii_exposed = flags.get("pii_exposed", False)
        # Check if direct PII is present (email, phone, name)
        if ids.get("email") or ids.get("phone") or ids.get("name") or pii_exposed:
            return {
                "category": "ACCOUNT_TOMBSTONE",
                "system_id": system_id,
                "required_action": "REDACT",
                "compliant": False,
                "finding_operation": "REPORT_EXPOSED_PII",
                "finding_state": "PRESENT",
                "remediation_operation": "REDACT_RECORD",
                "remediation_state": "REDACTED",
                "verification_operation": "VERIFY_RECORD_REDACTED",
                "verification_state": "REDACTED",
            }
        else:
            return {
                "category": "ACCOUNT_TOMBSTONE",
                "system_id": system_id,
                "required_action": "REDACT",
                "compliant": True,
                "finding_operation": None,
                "finding_state": None,
                "remediation_operation": None,
                "remediation_state": None,
                "verification_operation": "VERIFY_RECORD_REDACTED",
                "verification_state": "REDACTED",
            }

    # 4. Security Audit Logs / Legal Holds / Retained Records
    if resource_id.startswith(("audit_record_", "legal_hold_")):
        return {
            "category": "SECURITY_AUDIT_LOG" if resource_id.startswith("audit_record_") else "LEGAL_HOLD_RECORD",
            "system_id": system_id,
            "required_action": "RETAIN",
            "compliant": True,
            "finding_operation": None,
            "finding_state": None,
            "remediation_operation": None,
            "remediation_state": None,
            "verification_operation": "VERIFY_RECORD_PRESENT",
            "verification_state": "PRESENT",
        }

    # 5. Analytics Profiles
    if resource_id.startswith("analytics_"):
        is_anonymized = flags.get("anonymized", False)
        # Check if historical email hash remained in analytics store
        if ids.get("email_hash") and not is_anonymized and exists is True:
            return {
                "category": "ANALYTICS_PROFILE",
                "system_id": system_id,
                "required_action": "DELETE",
                "compliant": False,
                "finding_operation": "REPORT_REMAINING_RECORD",
                "finding_state": "PRESENT",
                "remediation_operation": "DELETE_RECORD",
                "remediation_state": "ABSENT",
                "verification_operation": "VERIFY_RECORD_ABSENT",
                "verification_state": "ABSENT",
            }
        elif not is_anonymized and (ids.get("email") or ids.get("user_id") or ids.get("phone")):
            return {
                "category": "ANALYTICS_PROFILE",
                "system_id": system_id,
                "required_action": "ANONYMIZE",
                "compliant": False,
                "finding_operation": "REPORT_EXPOSED_PII",
                "finding_state": "PRESENT",
                "remediation_operation": "ANONYMIZE_RECORD",
                "remediation_state": "ANONYMIZED",
                "verification_operation": "VERIFY_RECORD_ANONYMIZED",
                "verification_state": "ANONYMIZED",
            }
        else:
            return {
                "category": "ANALYTICS_PROFILE",
                "system_id": system_id,
                "required_action": "ANONYMIZE",
                "compliant": True,
                "finding_operation": None,
                "finding_state": None,
                "remediation_operation": None,
                "remediation_state": None,
                "verification_operation": "VERIFY_RECORD_ANONYMIZED",
                "verification_state": "ANONYMIZED",
            }


    # 6. Support Tickets / Attachments
    if resource_id.startswith("support_"):
        doc_type = flags.get("document_type")
        file_name = flags.get("file_name", "")
        # If it is a file/attachment belonging solely to customer -> DELETE
        if doc_type == "support_attachment" or file_name.endswith((".pdf", ".png", ".jpg")):
            if exists is True:
                return {
                    "category": "SUPPORT_ATTACHMENT",
                    "system_id": system_id,
                    "required_action": "DELETE",
                    "compliant": False,
                    "finding_operation": "REPORT_REMAINING_RECORD",
                    "finding_state": "PRESENT",
                    "remediation_operation": "DELETE_RECORD",
                    "remediation_state": "ABSENT",
                    "verification_operation": "VERIFY_RECORD_ABSENT",
                    "verification_state": "ABSENT",
                }
            else:
                return {
                    "category": "SUPPORT_ATTACHMENT",
                    "system_id": system_id,
                    "required_action": "DELETE",
                    "compliant": True,
                    "finding_operation": None,
                    "finding_state": None,
                    "remediation_operation": None,
                    "remediation_state": None,
                    "verification_operation": "VERIFY_RECORD_ABSENT",
                    "verification_state": "ABSENT",
                }
        else:
            # Support message/ticket -> REDACT
            pii_exposed = flags.get("pii_exposed", False) or bool(ids.get("email") or ids.get("phone"))
            if pii_exposed and exists is not False:
                return {
                    "category": "SUPPORT_MESSAGE",
                    "system_id": system_id,
                    "required_action": "REDACT",
                    "compliant": False,
                    "finding_operation": "REPORT_EXPOSED_PII",
                    "finding_state": "PRESENT",
                    "remediation_operation": "REDACT_RECORD",
                    "remediation_state": "REDACTED",
                    "verification_operation": "VERIFY_RECORD_REDACTED",
                    "verification_state": "REDACTED",
                }
            else:
                return {
                    "category": "SUPPORT_MESSAGE",
                    "system_id": system_id,
                    "required_action": "REDACT",
                    "compliant": True,
                    "finding_operation": None,
                    "finding_state": None,
                    "remediation_operation": None,
                    "remediation_state": None,
                    "verification_operation": "VERIFY_RECORD_REDACTED",
                    "verification_state": "REDACTED",
                }

    # 7. User Profiles, Search Indices, Customer Exports (Standard DELETE)
    # e.g., account_\w+, search_\w+, export_\w+, marketing_\w+
    if exists is True:
        return {
            "category": category,
            "system_id": system_id,
            "required_action": "DELETE",
            "compliant": False,
            "finding_operation": "REPORT_REMAINING_RECORD",
            "finding_state": "PRESENT",
            "remediation_operation": "DELETE_RECORD",
            "remediation_state": "ABSENT",
            "verification_operation": "VERIFY_RECORD_ABSENT",
            "verification_state": "ABSENT",
        }
    else:
        return {
            "category": category,
            "system_id": system_id,
            "required_action": "DELETE",
            "compliant": True,
            "finding_operation": None,
            "finding_state": None,
            "remediation_operation": None,
            "remediation_state": None,
            "verification_operation": "VERIFY_RECORD_ABSENT",
            "verification_state": "ABSENT",
        }
