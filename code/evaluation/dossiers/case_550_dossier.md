# Audit Dossier: case_550

## Case Metadata
- **Email**: `cmoreau0179@fastmail.com`
- **Requested At**: `2026-08-31T12:00:00Z`
- **Reported Status**: `COMPLETE`
- **Reported At**: `2026-09-02T12:00:00Z`
- **Audit Cutoff**: `2026-09-20T12:00:00Z`
- **Request Text**: *"Please begin the deletion process for the account using this email address. Please follow the applicable retention and deletion requirements for the account. Please let me know once the request has been reviewed."*

## Identity Resolution
- **User ID**: `user_550`
- **Emails**: ['cmoreau0179@fastmail.com']
- **Historical Audit Changes**: 1
- **Phones**: ['+33 6 36 39 01 06', '+33 6 46 28 67 05']
- **Hashes**: ['2a2f4423e4c6bf31171176c97fc49139a90fbd3832c244fea3a92b50735bee2f']

## Discovered Resources
- **Primary Account**: `account_010`
- **Security Audit Record**: `audit_record_3831`
- **All Discovered Resources (4)**: ['account_010', 'audit_record_3831', 'support_002', 'tombstone_7389']

## Audit Verdict & Plan
- **Determined Status**: **`INCOMPLETE`**
- **Step Count**: `8`

### Plan Steps
```json
[
  {
    "phase": "FINDING",
    "system_id": "support_platform",
    "resource_id": "support_002",
    "operation": "REPORT_REMAINING_RECORD",
    "state": "PRESENT",
    "evidence_id": "evidence_61",
    "step_no": 1
  },
  {
    "phase": "FINDING",
    "system_id": "identity_service",
    "resource_id": "tombstone_7389",
    "operation": "REPORT_EXPOSED_PII",
    "state": "PRESENT",
    "evidence_id": "evidence_52",
    "step_no": 2
  },
  {
    "phase": "REMEDIATION",
    "system_id": "support_platform",
    "resource_id": "support_002",
    "operation": "DELETE_RECORD",
    "state": "ABSENT",
    "evidence_id": "",
    "step_no": 3
  },
  {
    "phase": "REMEDIATION",
    "system_id": "identity_service",
    "resource_id": "tombstone_7389",
    "operation": "REDACT_RECORD",
    "state": "REDACTED",
    "evidence_id": "",
    "step_no": 4
  },
  {
    "phase": "VERIFICATION",
    "system_id": "account_service",
    "resource_id": "account_010",
    "operation": "VERIFY_RECORD_ABSENT",
    "state": "ABSENT",
    "evidence_id": "",
    "step_no": 5
  },
  {
    "phase": "VERIFICATION",
    "system_id": "support_platform",
    "resource_id": "support_002",
    "operation": "VERIFY_RECORD_ABSENT",
    "state": "ABSENT",
    "evidence_id": "",
    "step_no": 6
  },
  {
    "phase": "VERIFICATION",
    "system_id": "security_service",
    "resource_id": "audit_record_3831",
    "operation": "VERIFY_RECORD_PRESENT",
    "state": "PRESENT",
    "evidence_id": "",
    "step_no": 7
  },
  {
    "phase": "VERIFICATION",
    "system_id": "identity_service",
    "resource_id": "tombstone_7389",
    "operation": "VERIFY_RECORD_REDACTED",
    "state": "REDACTED",
    "evidence_id": "",
    "step_no": 8
  }
]
```

## Grounding Observations
### Resource: `account_010` (0 observations)
### Resource: `audit_record_3831` (2 observations)
- **File**: `evidence_52` (captured: `2026-09-20T12:00:00Z`) | System: `security_service` | Exists: `True` | Flags: `{'anonymized': True}`
- **File**: `evidence_52` (captured: `2026-09-20T12:00:00Z`) | System: `security_service` | Exists: `True` | Flags: `{'anonymized': True}`
### Resource: `support_002` (2 observations)
- **File**: `evidence_61` (captured: `2026-09-17T22:00:19Z`) | System: `support_platform` | Exists: `True` | Flags: `{'trace_id': 'tr-rp-002', 'event': 'contact_query_completed'}`
- **File**: `evidence_61` (captured: `2026-09-17T22:00:19Z`) | System: `support_platform` | Exists: `True` | Flags: `{'trace_id': 'tr-rp-002', 'event': 'deletion_marker_check', 'marker_found': False}`
### Resource: `tombstone_7389` (2 observations)
- **File**: `evidence_52` (captured: `2026-09-20T12:00:00Z`) | System: `identity_service` | Exists: `True` | Flags: `{}`
- **File**: `evidence_52` (captured: `2026-09-20T12:00:00Z`) | System: `identity_service` | Exists: `True` | Flags: `{}`