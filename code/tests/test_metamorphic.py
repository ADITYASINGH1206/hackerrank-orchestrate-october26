"""
Metamorphic test suite verifying agent behavioral robustness:
1. Email casing symmetry: user@example.com == USER@EXAMPLE.COM
2. Multilingual non-deletion intent invariance: requests for export, correction, or marketing opt-out
   yield NOT_APPLICABLE across English, French, Spanish, German, Japanese.
"""

from code.core.store import ObservationStore
from code.core.intent import authorizes_deletion
from code.core.discovery import discover_resources_for_case
from code.core.planner import plan_case


def test_email_casing_symmetry():
    store = ObservationStore()
    store.load_all()

    case_lower = {
        "case_id": "test_01",
        "email": "amina.elmasri@gmail.com",
        "requested_at": "2026-08-18T09:14:00Z",
        "reported_status": "COMPLETE",
        "reported_at": "2026-08-20T16:42:00Z",
        "audit_at": "2026-09-03T11:30:00Z",
        "request_text": "Please delete my account and remove my personal details.",
    }
    case_upper = dict(case_lower)
    case_upper["email"] = "AMINA.ELMASRI@GMAIL.COM"

    res_lower = discover_resources_for_case(case_lower, store)
    res_upper = discover_resources_for_case(case_upper, store)

    status_lower, steps_lower = plan_case(case_lower, res_lower)
    status_upper, steps_upper = plan_case(case_upper, res_upper)

    assert status_lower == status_upper
    assert steps_lower == steps_upper


def test_multilingual_non_deletion_requests():
    non_deletion_prompts = [
        # English
        "I want a copy of all data you have collected about me under GDPR Article 15.",
        "Please update my shipping address and fix my phone number.",
        "Unsubscribe me from your weekly marketing newsletters.",
        # Spanish
        "Deseo ejercer mi derecho de acceso y recibir una copia de mis datos personales.",
        "Por favor corrijan mi apellido en la factura del mes pasado.",
        # French
        "Veuillez m'envoyer une copie intégrale de mes données personnelles conformément au RGPD.",
        "Je souhaite rectifier mon adresse de facturation.",
        # German
        "Ich beantrage hiermit Auskunft über meine bei Ihnen gespeicherten personenbezogenen Daten.",
        "Bitte korrigieren Sie meine Telefonnummer.",
        # Japanese
        "登録されている個人情報の開示を請求します。",
        "メールマガジンの配信停止をお願いします。",
    ]

    for text in non_deletion_prompts:
        auth, _ = authorizes_deletion(text)
        assert not auth, f"Failed to classify non-deletion text: '{text}'"
