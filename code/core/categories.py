"""
Category and system mapping for Ghost Data resources.
"""

import re
from typing import Optional, Tuple

PREFIX_TO_SYSTEM = {
    "account": "account_service",
    "search": "search_service",
    "support": "support_platform",
    "analytics": "analytics_platform",
    "audit_record": "security_service",
    "backup": "backup_service",
    "data_flow": "integration_service",
    "export": "export_service",
    "tombstone": "identity_service",
    "marketing": "marketing_platform",
    "legal_hold": "legal_service",
    "object": "object_storage",
}


def get_prefix(resource_id: str) -> str:
    """Extract resource prefix e.g. account from account_005, audit_record from audit_record_001."""
    m = re.match(r"^([a-z]+(?:_[a-z]+)?)(?:_\d+)?$", resource_id)
    if m:
        p = m.group(1)
        if p in PREFIX_TO_SYSTEM:
            return p
    # fallback: split by last underscore with digits
    parts = resource_id.rsplit("_", 1)
    if len(parts) == 2 and parts[1].isdigit():
        return parts[0]
    return resource_id


def get_system_id(resource_id: str, default_system: Optional[str] = None) -> str:
    """Resolve canonical system_id for a resource_id."""
    prefix = get_prefix(resource_id)
    if prefix in PREFIX_TO_SYSTEM:
        return PREFIX_TO_SYSTEM[prefix]
    if default_system:
        return default_system
    return "unknown_system"


def get_data_category(resource_id: str, context: Optional[dict] = None) -> str:
    """Resolve data_category defined in deletion_rules.csv."""
    prefix = get_prefix(resource_id)
    
    if prefix == "account":
        return "USER_PROFILE"
    elif prefix == "search":
        return "SEARCH_INDEX_ENTRY"
    elif prefix == "analytics":
        return "ANALYTICS_PROFILE"
    elif prefix == "export":
        return "USER_EXPORT"
    elif prefix == "marketing":
        return "MARKETING_PROFILE"
    elif prefix == "audit_record":
        return "SECURITY_AUDIT_LOG"
    elif prefix == "legal_hold":
        return "LEGAL_HOLD_RECORD"
    elif prefix == "backup":
        return "BACKUP_ARCHIVE"
    elif prefix == "tombstone":
        return "ACCOUNT_TOMBSTONE"
    elif prefix == "data_flow":
        return "DATA_FLOW"
    elif prefix == "object":
        return "SUPPORT_ATTACHMENT"
    elif prefix == "support":
        # Check context: attachment vs message
        if context:
            if context.get("is_attachment") or "attachment" in str(context.get("location", "")).lower():
                return "SUPPORT_ATTACHMENT"
            if context.get("file_name") or str(context.get("resource_id", "")).startswith("object_"):
                return "SUPPORT_ATTACHMENT"
        return "SUPPORT_MESSAGE"
    
    return "USER_PROFILE"
