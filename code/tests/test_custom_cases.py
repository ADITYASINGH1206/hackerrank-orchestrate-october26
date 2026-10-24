"""
Custom scenario evaluation suite fulfilling §6.8 requirement:
Defines and tests 4 challenging edge-case scenarios:
1. Scenario A: Replica Desynchronization / Ghost Resurrection
2. Scenario B: Anonymized Tombstone Retention under Legal Hold
3. Scenario C: Active Sync Connector Continuously Recreating Search Records
4. Scenario D: Ambiguous Multilingual Right-to-Access Request (NOT_APPLICABLE)
"""

from code.core.store import ObservationStore
from code.core.models import Observation, Activity
from code.core.identity import IdentitySet
from code.core.timeline import reconstruct_resource_state
from code.core.policy import evaluate_resource_policy
from code.core.intent import authorizes_deletion


def test_scenario_a_replica_desynchronization():
    """Primary snapshot is deleted (ABSENT), but failover replica still has user profile (PRESENT)."""
    obs = [
        Observation(
            file_id="evidence_primary",
            captured_at="2026-09-01T12:00:00Z",
            system_id="account_service",
            location="customer_profiles_primary",
            resource_id="account_test_01",
            exists=False,
            ids={},
            flags={},
            raw={},
        ),
        Observation(
            file_id="evidence_replica",
            captured_at="2026-09-01T12:00:00Z",
            system_id="account_service",
            location="customer_profiles_failover_replica",
            resource_id="account_test_01",
            exists=True,
            ids={"email": "victim@example.com"},
            flags={},
            raw={},
        ),
    ]

    exists, flags, ids, ev = reconstruct_resource_state("account_test_01", obs, [], "2026-09-02T12:00:00Z")
    assert exists is True, "Replication drift must detect that replica data remains un-deleted!"

    pol = evaluate_resource_policy("account_test_01", exists, flags, ids, [])
    assert pol["compliant"] is False, "Resource must be evaluated as non-compliant!"
    assert pol["finding_operation"] == "REPORT_REMAINING_RECORD"
    assert pol["remediation_operation"] == "DELETE_RECORD"


def test_scenario_b_anonymized_tombstone():
    """Tombstone preserved with subject reference but direct PII removed."""
    obs = [
        Observation(
            file_id="evidence_tomb",
            captured_at="2026-09-01T12:00:00Z",
            system_id="identity_service",
            location="account_tombstones",
            resource_id="tombstone_test_02",
            exists=True,
            ids={"user_id": "user_999"},  # permitted stable reference
            flags={},
            raw={"subject_reference": "user_999"},
        )
    ]

    exists, flags, ids, ev = reconstruct_resource_state("tombstone_test_02", obs, [], "2026-09-02T12:00:00Z")
    pol = evaluate_resource_policy("tombstone_test_02", exists, flags, ids, [])
    assert pol["compliant"] is True, "Tombstone without direct PII must be compliant!"
    assert pol["verification_operation"] == "VERIFY_RECORD_REDACTED"


def test_scenario_c_active_data_flow_recreation():
    """Active connector continuously syncs user data to warehouse."""
    obs = [
        Observation(
            file_id="evidence_flow",
            captured_at="2026-09-01T12:00:00Z",
            system_id="integration_service",
            location="connector_table",
            resource_id="data_flow_test_03",
            exists=True,
            ids={"user_id": "user_888"},
            flags={"enabled": True},
            raw={"enabled": True},
        )
    ]

    exists, flags, ids, ev = reconstruct_resource_state("data_flow_test_03", obs, [], "2026-09-02T12:00:00Z")
    pol = evaluate_resource_policy("data_flow_test_03", exists, flags, ids, [])
    assert pol["compliant"] is False, "Active data flow must be flagged non-compliant!"
    assert pol["finding_operation"] == "REPORT_ACTIVE_DATA_FLOW"
    assert pol["remediation_operation"] == "DISABLE_DATA_FLOW"
    assert pol["verification_operation"] == "VERIFY_DATA_FLOW_DISABLED"


def test_scenario_d_ambiguous_gdpr_access_request():
    """Request for GDPR data export must be classified as NOT_APPLICABLE."""
    req_text = "Je vous prie de m'adresser l'ensemble des données personnelles collectées à mon sujet."
    auth, _ = authorizes_deletion(req_text)
    assert not auth, "Access request must not be treated as deletion authorization!"
