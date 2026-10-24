# Audit Dossier: case_122

## Case Metadata
- **Email**: `hannah.sullivan@gmail.com`
- **Requested At**: `2026-08-12T11:00:00Z`
- **Reported Status**: `PARTIALLY_COMPLETE`
- **Reported At**: `2026-08-13T11:00:00Z`
- **Audit Cutoff**: `2026-08-22T11:00:00Z`
- **Request Text**: *"I would like to submit a request to delete this account and its personal data. Please apply the correct treatment to records covered by the request. Let me know when the request has been completed."*

## Identity Resolution
- **User ID**: `user_120`
- **Emails**: ['hannah.sullivan@gmail.com']
- **Historical Audit Changes**: 1
- **Phones**: ['+44 7700 900120', '+44 7700 900620']
- **Hashes**: ['2956cf1395c2863c7d75a86eb744b4d857a247411716c2cae71cfcc016da6c1d']

## Discovered Resources
- **Primary Account**: `account_9580`
- **Security Audit Record**: `None`
- **All Discovered Resources (3)**: ['account_9580', 'data_flow_3199', 'search_1752']

## Audit Verdict & Plan
- **Determined Status**: **`INCOMPLETE`**
- **Step Count**: `7`

### Plan Steps
```json
[
  {
    "phase": "FINDING",
    "system_id": "search_service",
    "resource_id": "search_1752",
    "operation": "REPORT_REMAINING_RECORD",
    "state": "PRESENT",
    "evidence_id": "evidence_88",
    "step_no": 1
  },
  {
    "phase": "FINDING",
    "system_id": "integration_service",
    "resource_id": "data_flow_3199",
    "operation": "REPORT_ACTIVE_DATA_FLOW",
    "state": "ACTIVE",
    "evidence_id": "evidence_88",
    "step_no": 2
  },
  {
    "phase": "REMEDIATION",
    "system_id": "integration_service",
    "resource_id": "data_flow_3199",
    "operation": "DISABLE_DATA_FLOW",
    "state": "DISABLED",
    "evidence_id": "",
    "step_no": 3
  },
  {
    "phase": "REMEDIATION",
    "system_id": "search_service",
    "resource_id": "search_1752",
    "operation": "DELETE_RECORD",
    "state": "ABSENT",
    "evidence_id": "",
    "step_no": 4
  },
  {
    "phase": "VERIFICATION",
    "system_id": "account_service",
    "resource_id": "account_9580",
    "operation": "VERIFY_RECORD_ABSENT",
    "state": "ABSENT",
    "evidence_id": "",
    "step_no": 5
  },
  {
    "phase": "VERIFICATION",
    "system_id": "search_service",
    "resource_id": "search_1752",
    "operation": "VERIFY_RECORD_ABSENT",
    "state": "ABSENT",
    "evidence_id": "",
    "step_no": 6
  },
  {
    "phase": "VERIFICATION",
    "system_id": "integration_service",
    "resource_id": "data_flow_3199",
    "operation": "VERIFY_DATA_FLOW_DISABLED",
    "state": "DISABLED",
    "evidence_id": "",
    "step_no": 7
  }
]
```

## Grounding Observations
### Resource: `account_9580` (0 observations)
### Resource: `data_flow_3199` (2 observations)
- **File**: `evidence_88` (captured: `2026-08-22T10:39:10Z`) | System: `integration_service` | Exists: `True` | Flags: `{'trace_id': 'rb-074559-001', 'event': 'connector_config_read_started'}`
- **File**: `evidence_88` (captured: `2026-08-22T10:39:10Z`) | System: `integration_service` | Exists: `True` | Flags: `{'trace_id': 'rb-074559-001', 'event': 'connector_config_read_completed', 'enabled': True}`
### Resource: `search_1752` (2 observations)
- **File**: `evidence_88` (captured: `2026-08-22T10:39:10Z`) | System: `search_service` | Exists: `True` | Flags: `{'trace_id': 'rb-074655-002', 'event': 'index_query_started'}`
- **File**: `evidence_88` (captured: `2026-08-22T10:39:10Z`) | System: `search_service` | Exists: `True` | Flags: `{'trace_id': 'rb-074655-002', 'event': 'index_query_completed'}`