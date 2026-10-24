"""
Regression test floor ensuring Status Accuracy == 100% and Step F1 >= 95.0%.
"""

from code.core.store import ObservationStore
from code.evaluation.main import evaluate_samples


def test_golden_baseline_accuracy():
    results = evaluate_samples()
    assert results["status_accuracy"] == 100.0, f"Expected 100% status accuracy, got {results['status_accuracy']}%"
    assert results["reachable_step_f1"] >= 95.0, f"Expected reachable step F1 >= 95.0%, got {results['reachable_step_f1']}%"
    assert results["reachable_sequence_accuracy"] >= 70.0, f"Expected sequence accuracy >= 70.0%, got {results['reachable_sequence_accuracy']}%"
