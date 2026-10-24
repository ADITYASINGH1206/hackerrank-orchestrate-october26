# Audit Dossier: case_147

## Case Metadata
- **Email**: `l.fernandez84@gmail.com`
- **Requested At**: `2026-07-23T08:00:00Z`
- **Reported Status**: `PARTIALLY_COMPLETE`
- **Reported At**: `2026-07-25T08:00:00Z`
- **Audit Cutoff**: `2026-08-07T08:00:00Z`
- **Request Text**: *"Solicito la eliminación permanente de la cuenta asociada a este correo. Revisen los identificadores actuales y anteriores según su política de privacidad. Por favor, confirmen el resultado cuando termine la revisión."*

## Identity Resolution
- **User ID**: `user_145`
- **Emails**: ['l.fernandez84@gmail.com']
- **Historical Audit Changes**: 1
- **Phones**: ['+34 691 583 526', '+34 776 829 829']
- **Hashes**: ['0c02dab8cd949dc8c60f0f502ccfbbf7af8f0c41a6f74bc3acadcc51447bc4e7']

## Discovered Resources
- **Primary Account**: `account_5023`
- **Security Audit Record**: `None`
- **All Discovered Resources (2)**: ['account_5023', 'backup_4244']

## Audit Verdict & Plan
- **Determined Status**: **`INCOMPLETE`**
- **Step Count**: `4`

### Plan Steps
```json
[
  {
    "phase": "FINDING",
    "system_id": "backup_service",
    "resource_id": "backup_4244",
    "operation": "REPORT_RESTORE_RISK",
    "state": "ACTIVE",
    "evidence_id": "evidence_86",
    "step_no": 1
  },
  {
    "phase": "REMEDIATION",
    "system_id": "backup_service",
    "resource_id": "backup_4244",
    "operation": "BLOCK_RESTORE",
    "state": "BLOCKED",
    "evidence_id": "",
    "step_no": 2
  },
  {
    "phase": "VERIFICATION",
    "system_id": "account_service",
    "resource_id": "account_5023",
    "operation": "VERIFY_RECORD_ABSENT",
    "state": "ABSENT",
    "evidence_id": "",
    "step_no": 3
  },
  {
    "phase": "VERIFICATION",
    "system_id": "backup_service",
    "resource_id": "backup_4244",
    "operation": "VERIFY_RESTORE_BLOCKED",
    "state": "BLOCKED",
    "evidence_id": "",
    "step_no": 4
  }
]
```

## Grounding Observations
### Resource: `account_5023` (0 observations)
### Resource: `backup_4244` (1 observations)
- **File**: `evidence_86` (captured: `2026-08-07T07:41:04Z`) | System: `backup_service` | Exists: `True` | Flags: `{'restore_allowed': True}`