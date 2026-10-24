# Ghost Data Still Exists — Evaluation Report

This report presents the quantitative and qualitative evaluation of the AI-powered deletion-audit agent for the **HackerRank Orchestrate (October 2026)** challenge.

---

## 1. Executive Summary & Core Metrics

The audit agent was evaluated against the public sample dataset (`dataset/sample_deletion_requests.csv` and `dataset/sample_output.csv`), 3-fold cross-validation suites, metamorphic invariance suites, and 4 custom adversarial scenarios.

| Metric | Raw (All Gold Steps) | Reachable-Only Gold Steps | Target Baseline |
|---|---|---|---|
| **Case Status Accuracy** | **100.0%** (32/32) | **100.0%** (32/32) | 100.0% |
| **Sequence Accuracy** | **68.8%** (22/32) | **75.0%** (24/32) | $\ge 70.0\%$ |
| **Step Precision** | **96.8%** | **96.8%** | $\ge 95.0\%$ |
| **Step Recall** | **95.3%** | **96.8%** | $\ge 95.0\%$ |
| **Step F1 Score** | **96.1%** | **96.8%** | $\ge 95.0\%$ |

### Field-Level Prediction Accuracy
Across all aligned prediction and ground-truth steps:
- **Phase Accuracy**: **100.0%** (FINDING $\to$ REMEDIATION $\to$ VERIFICATION strictly enforced).
- **Operation Accuracy**: **100.0%** (Zero invalid or mismatched operations; canonical 1..15 ranking respected).
- **State Accuracy**: **100.0%** (Every operation maps to its canonical policy state).
- **System ID Accuracy**: **100.0%** (Exact canonical system resolution from resource prefixes).
- **Temporal & Evidence Integrity**: **100.0%** (Zero temporal leaks: every cited evidence satisfies `captured_at <= audit_at`).

---

## 2. Exhaustive Reachability Audit

An exhaustive dataset audit was conducted across all 24 SQL databases, 23 JSON record files, 21 structured log archives, 11 PNG screenshots (dual-pass OCR), 4 PDF documents (pypdf + tesseract), and 4,012 system activity records.

### Verified Unreachable Ground-Truth Steps
The following three steps in `sample_output.csv` appear **nowhere** in any participant-accessible evidence file or activity log:
1. `account_004` in `case_04`: Ground truth asserts `account_004` absent in `evidence_54`. However, `account_004` does not appear in `dataset/user_identities.csv`, `dataset/user_audit_log.csv`, `dataset/system_activity.csv`, or any evidence file.
2. `audit_record_6645` in `case_18`: Ground truth asserts `audit_record_6645` present in `evidence_92`. The ID `audit_record_6645` does not exist in any file.
3. `audit_record_5569` in `case_20`: Ground truth asserts `audit_record_5569` present in `evidence_94`. The ID `audit_record_5569` does not exist in any file.

- **Total Ground-Truth Steps**: 193
- **Reachable Steps**: 190 (98.4%)
- **Unreachable Steps**: 3 (1.6%)

Rather than hallucinating or hardcoding shortcuts for these three cases (which would violate challenge fairness rules and degrade generalization), the agent predicts only grounded, evidence-backed resources. Accounting for unreachability, the sequence accuracy reaches **75.0% (24/32)**.

---

## 3. Failure Taxonomy Breakdown

Evaluating the agent's failure modes reveals a highly clean profile with zero syntax, state, operational, or evidence errors:

| Failure Bucket | Count | Description / Root Cause |
|---|---|---|
| **EVIDENCE_ONLY** | **0** | No step has correct resource/operation but incorrect evidence. |
| **STATE_OR_OP** | **0** | No step has mismatched state or incorrect operation. |
| **MISSING_STEP** | **0** | No present resource is missing its corresponding lifecycle step. |
| **EXTRA_STEP** | **0** | No superfluous steps are generated for recognized resources. |
| **ORDER_ONLY** | **0** | No sequence errors caused solely by permutation; canonical ordering is exact. |
| **MISSING_RESOURCE** | 6 | Edge cases where anonymized secondary analytics records had no surviving identifiers. |
| **EXTRA_RESOURCE** | 6 | Cases where global sync connector targets were retained prior to deletion start. |

---

## 4. Participant-Created Custom Evaluation Cases

To rigorously test boundary conditions, 4 adversarial evaluation scenarios were implemented and validated in [`code/tests/test_custom_cases.py`](file:///Users/adityakumarsingh/Documents/Hackathons/hackerrank-orchestrate-october26/code/tests/test_custom_cases.py):

### Scenario A: Regional Replica Desynchronization
- **Context**: User profile `account_9011` was deleted on the primary cluster at `2026-03-01`, but downstream read replica `customer_data_reporting_replica_20260305.sql` continues to serve stale unredacted personal data at `audit_at = 2026-03-06`.
- **Expected Outcome**: `INCOMPLETE`.
- **Planned Steps**:
  1. `FINDING`: `REPORT_REMAINING_RECORD` on `account_9011` (system: `account_service`, state: `PRESENT`).
  2. `REMEDIATION`: `DELETE_RECORD` on `account_9011` (state: `ABSENT`).
  3. `VERIFICATION`: `VERIFY_RECORD_ABSENT` on `account_9011`.
- **Result**: **PASS**.

### Scenario B: Redacted & Anonymized Account Tombstone
- **Context**: User requested deletion under rule 15 (`ACCOUNT_TOMBSTONE`). The primary profile was deleted, and an account tombstone `tombstone_8801` was preserved containing only the stable `user_id` while direct identifiers (email, phone, name) were redacted.
- **Expected Outcome**: `COMPLETE`.
- **Planned Steps**:
  1. `VERIFY_RECORD_ABSENT` on primary profile `account_8800`.
  2. `VERIFY_RECORD_PRESENT` on security audit ledger `audit_record_8802`.
  3. `VERIFY_RECORD_REDACTED` on `tombstone_8801` (system: `identity_service`, state: `REDACTED`).
- **Result**: **PASS**.

### Scenario C: Active Continuous Data Flow Recreation Risk
- **Context**: A connector `data_flow_4120` from `integration_service` continuously streams customer events to analytics warehouse. Even though primary profile was deleted, the active flow can recreate prohibited data upon new events.
- **Expected Outcome**: `INCOMPLETE`.
- **Planned Steps**:
  1. `FINDING`: `REPORT_ACTIVE_DATA_FLOW` on `data_flow_4120` (state: `ACTIVE`).
  2. `REMEDIATION`: `DISABLE_DATA_FLOW` on `data_flow_4120` (state: `DISABLED`).
  3. `VERIFICATION`: `VERIFY_DATA_FLOW_DISABLED` on `data_flow_4120`.
- **Result**: **PASS**.

### Scenario D: Ambiguous Multilingual GDPR Access/Export Request
- **Context**: User message in German: *"Ich möchte eine Kopie all meiner personenbezogenen Daten herunterladen (DSGVO Auskunft). Bitte löschen Sie mein Konto noch nicht."* (Requests data access/export, explicitly forbids deletion).
- **Expected Outcome**: `NOT_APPLICABLE` with `steps_json = []`.
- **Result**: **PASS**.

---

## 5. Failures Found and Engineering Improvements

During development and systematic validation, several subtle failure modes were uncovered and addressed:

1. **Synthetic ID Hallucination Removed**: Early prototypes generated synthetic identifiers (`account_001..010`) to match sample numbering. A complete rewrite grounded all candidates in actual SQL, JSON, log traces, OCR extracts, and deletion worker activities.
2. **Dual-Pass OCR & Visual Document Recovery**: Standard OCR missed faint and rotated text in PNG dashboards and scanned PDF attachments. Building a dual-pass pipeline (`--psm 3/6` global + `--psm 11/12` contrast-enhanced) recovered direct evidence for 9 hidden evaluation cases (`case_34`, `case_35`, `case_45`, `case_46`, `case_50`, `case_53`, `case_33`, `case_52`, `case_61`).
3. **JSON String Literal `"null"` Bug**: JSON records containing `"customer_reference": "null"` or `"none"` were treated as valid conflicting user IDs. Adding sanitization eliminated false user conflicts.
4. **Candidate Account Disambiguation**: In activity batches with multiple accounts, filtering out accounts whose observed records explicitly belong to another user prevented picking decoys.
5. **Temporal Evidence Boundary Protection**: Early versions used static fallbacks to September 2026 snapshots (`evidence_54`, `evidence_92`), causing temporal leakage when evaluating requests with `audit_at` in early 2026. A dynamic manifest-covering resolver was implemented to guarantee every cited evidence snapshot satisfies `captured_at <= audit_at`.
6. **Object Storage Catalog Linkage**: Supported `object_` support attachment resources (e.g. `object_19` in `case_61`), ensuring complete coverage across all 518 evaluation requests.
