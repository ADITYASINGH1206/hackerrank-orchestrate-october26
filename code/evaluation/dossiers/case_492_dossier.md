# Audit Dossier: case_492

## Case Metadata
- **Email**: `eamponsah5039@fastmail.com`
- **Requested At**: `2026-01-29T09:00:00Z`
- **Reported Status**: `COMPLETE`
- **Reported At**: `2026-01-31T09:00:00Z`
- **Audit Cutoff**: `2026-02-18T09:00:00Z`
- **Request Text**: *"I am requesting deletion of the account registered to this email address. Please follow the applicable retention and deletion requirements for the account. Please confirm the result after completing the required checks."*

## Identity Resolution
- **User ID**: `user_490`
- **Emails**: ['eamponsah5039@fastmail.com']
- **Historical Audit Changes**: 1
- **Phones**: ['+233 24 713 5812', '+233 24 879 6395']
- **Hashes**: ['4b725ee261bc56f980226f7c88d1ee0f854349343f53586d953693b1b747f36e']

## Discovered Resources
- **Primary Account**: `account_3589`
- **Security Audit Record**: `None`
- **All Discovered Resources (5)**: ['account_3589', 'analytics_1575', 'export_6406', 'search_9733', 'support_6737']

## Audit Verdict & Plan
- **Determined Status**: **`INCOMPLETE`**
- **Step Count**: `13`

### Plan Steps
```json
[
  {
    "phase": "FINDING",
    "system_id": "export_service",
    "resource_id": "export_6406",
    "operation": "REPORT_REMAINING_RECORD",
    "state": "PRESENT",
    "evidence_id": "evidence_64",
    "step_no": 1
  },
  {
    "phase": "FINDING",
    "system_id": "search_service",
    "resource_id": "search_9733",
    "operation": "REPORT_REMAINING_RECORD",
    "state": "PRESENT",
    "evidence_id": "evidence_64",
    "step_no": 2
  },
  {
    "phase": "FINDING",
    "system_id": "analytics_platform",
    "resource_id": "analytics_1575",
    "operation": "REPORT_EXPOSED_PII",
    "state": "PRESENT",
    "evidence_id": "evidence_64",
    "step_no": 3
  },
  {
    "phase": "FINDING",
    "system_id": "support_platform",
    "resource_id": "support_6737",
    "operation": "REPORT_EXPOSED_PII",
    "state": "PRESENT",
    "evidence_id": "evidence_64",
    "step_no": 4
  },
  {
    "phase": "REMEDIATION",
    "system_id": "export_service",
    "resource_id": "export_6406",
    "operation": "DELETE_RECORD",
    "state": "ABSENT",
    "evidence_id": "",
    "step_no": 5
  },
  {
    "phase": "REMEDIATION",
    "system_id": "search_service",
    "resource_id": "search_9733",
    "operation": "DELETE_RECORD",
    "state": "ABSENT",
    "evidence_id": "",
    "step_no": 6
  },
  {
    "phase": "REMEDIATION",
    "system_id": "support_platform",
    "resource_id": "support_6737",
    "operation": "REDACT_RECORD",
    "state": "REDACTED",
    "evidence_id": "",
    "step_no": 7
  },
  {
    "phase": "REMEDIATION",
    "system_id": "analytics_platform",
    "resource_id": "analytics_1575",
    "operation": "ANONYMIZE_RECORD",
    "state": "ANONYMIZED",
    "evidence_id": "",
    "step_no": 8
  },
  {
    "phase": "VERIFICATION",
    "system_id": "account_service",
    "resource_id": "account_3589",
    "operation": "VERIFY_RECORD_ABSENT",
    "state": "ABSENT",
    "evidence_id": "",
    "step_no": 9
  },
  {
    "phase": "VERIFICATION",
    "system_id": "export_service",
    "resource_id": "export_6406",
    "operation": "VERIFY_RECORD_ABSENT",
    "state": "ABSENT",
    "evidence_id": "",
    "step_no": 10
  },
  {
    "phase": "VERIFICATION",
    "system_id": "search_service",
    "resource_id": "search_9733",
    "operation": "VERIFY_RECORD_ABSENT",
    "state": "ABSENT",
    "evidence_id": "",
    "step_no": 11
  },
  {
    "phase": "VERIFICATION",
    "system_id": "support_platform",
    "resource_id": "support_6737",
    "operation": "VERIFY_RECORD_REDACTED",
    "state": "REDACTED",
    "evidence_id": "",
    "step_no": 12
  },
  {
    "phase": "VERIFICATION",
    "system_id": "analytics_platform",
    "resource_id": "analytics_1575",
    "operation": "VERIFY_RECORD_ANONYMIZED",
    "state": "ANONYMIZED",
    "evidence_id": "",
    "step_no": 13
  }
]
```

## Grounding Observations
### Resource: `account_3589` (0 observations)
### Resource: `analytics_1575` (2 observations)
- **File**: `evidence_64` (captured: `2026-02-18T08:39:11Z`) | System: `analytics_platform` | Exists: `True` | Flags: `{'trace_id': 'rb-054723-002', 'event': 'analytics_profile_read_started'}`
- **File**: `evidence_64` (captured: `2026-02-18T08:39:11Z`) | System: `analytics_platform` | Exists: `True` | Flags: `{'trace_id': 'rb-054723-002', 'event': 'analytics_profile_read_completed'}`
### Resource: `export_6406` (2 observations)
- **File**: `evidence_64` (captured: `2026-02-18T08:39:11Z`) | System: `export_service` | Exists: `True` | Flags: `{'trace_id': 'rb-060213-003', 'event': 'export_metadata_read_started'}`
- **File**: `evidence_64` (captured: `2026-02-18T08:39:11Z`) | System: `export_service` | Exists: `True` | Flags: `{'trace_id': 'rb-060213-003', 'event': 'export_metadata_read_completed'}`
### Resource: `search_9733` (2 observations)
- **File**: `evidence_64` (captured: `2026-02-18T08:39:11Z`) | System: `search_service` | Exists: `True` | Flags: `{'trace_id': 'rb-065406-009', 'event': 'index_query_started'}`
- **File**: `evidence_64` (captured: `2026-02-18T08:39:11Z`) | System: `search_service` | Exists: `True` | Flags: `{'trace_id': 'rb-065406-009', 'event': 'index_query_completed'}`
### Resource: `support_6737` (2 observations)
- **File**: `evidence_64` (captured: `2026-02-18T08:39:11Z`) | System: `support_platform` | Exists: `True` | Flags: `{'trace_id': 'rb-070859-012', 'event': 'support_ticket_read_started'}`
- **File**: `evidence_64` (captured: `2026-02-18T08:39:11Z`) | System: `support_platform` | Exists: `True` | Flags: `{'trace_id': 'rb-070859-012', 'event': 'support_ticket_read_completed'}`