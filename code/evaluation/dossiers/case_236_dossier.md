# Audit Dossier: case_236

## Case Metadata
- **Email**: `larissa.carvalho@outlook.com`
- **Requested At**: `2026-05-30T06:00:00Z`
- **Reported Status**: `NOT_STARTED`
- **Reported At**: `2026-05-31T06:00:00Z`
- **Audit Cutoff**: `2026-06-23T06:00:00Z`
- **Request Text**: *"I am requesting deletion of the account registered to this email address. Please ensure the request is applied to the relevant account records. Please send a confirmation after the process finishes."*

## Identity Resolution
- **User ID**: `user_234`
- **Emails**: ['larissa.carvalho@outlook.com']
- **Historical Audit Changes**: 0
- **Phones**: ['+55 61 97701-8815']
- **Hashes**: ['151e43f4159f6444e20ca09f16b222a1fc4cb9592745d00cdf6a515d0ea2717e']

## Discovered Resources
- **Primary Account**: `account_629`
- **Security Audit Record**: `None`
- **All Discovered Resources (3)**: ['account_629', 'data_flow_7352', 'search_5385']

## Audit Verdict & Plan
- **Determined Status**: **`INCOMPLETE`**
- **Step Count**: `7`

### Plan Steps
```json
[
  {
    "phase": "FINDING",
    "system_id": "search_service",
    "resource_id": "search_5385",
    "operation": "REPORT_REMAINING_RECORD",
    "state": "PRESENT",
    "evidence_id": "evidence_79",
    "step_no": 1
  },
  {
    "phase": "FINDING",
    "system_id": "integration_service",
    "resource_id": "data_flow_7352",
    "operation": "REPORT_ACTIVE_DATA_FLOW",
    "state": "ACTIVE",
    "evidence_id": "evidence_79",
    "step_no": 2
  },
  {
    "phase": "REMEDIATION",
    "system_id": "integration_service",
    "resource_id": "data_flow_7352",
    "operation": "DISABLE_DATA_FLOW",
    "state": "DISABLED",
    "evidence_id": "",
    "step_no": 3
  },
  {
    "phase": "REMEDIATION",
    "system_id": "search_service",
    "resource_id": "search_5385",
    "operation": "DELETE_RECORD",
    "state": "ABSENT",
    "evidence_id": "",
    "step_no": 4
  },
  {
    "phase": "VERIFICATION",
    "system_id": "account_service",
    "resource_id": "account_629",
    "operation": "VERIFY_RECORD_ABSENT",
    "state": "ABSENT",
    "evidence_id": "",
    "step_no": 5
  },
  {
    "phase": "VERIFICATION",
    "system_id": "search_service",
    "resource_id": "search_5385",
    "operation": "VERIFY_RECORD_ABSENT",
    "state": "ABSENT",
    "evidence_id": "",
    "step_no": 6
  },
  {
    "phase": "VERIFICATION",
    "system_id": "integration_service",
    "resource_id": "data_flow_7352",
    "operation": "VERIFY_DATA_FLOW_DISABLED",
    "state": "DISABLED",
    "evidence_id": "",
    "step_no": 7
  }
]
```

## Grounding Observations
### Resource: `account_629` (0 observations)
### Resource: `data_flow_7352` (2 observations)
- **File**: `evidence_79` (captured: `2026-06-23T05:37:26Z`) | System: `integration_service` | Exists: `True` | Flags: `{'trace_id': 'rb-035607-014', 'event': 'connector_config_read_started'}`
- **File**: `evidence_79` (captured: `2026-06-23T05:37:26Z`) | System: `integration_service` | Exists: `True` | Flags: `{'trace_id': 'rb-035607-014', 'event': 'connector_config_read_completed', 'enabled': True}`
### Resource: `search_5385` (2 observations)
- **File**: `evidence_79` (captured: `2026-06-23T05:37:26Z`) | System: `search_service` | Exists: `True` | Flags: `{'trace_id': 'rb-035537-013', 'event': 'index_query_started'}`
- **File**: `evidence_79` (captured: `2026-06-23T05:37:26Z`) | System: `search_service` | Exists: `True` | Flags: `{'trace_id': 'rb-035537-013', 'event': 'index_query_completed'}`