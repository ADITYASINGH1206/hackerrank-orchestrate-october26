"""
Multilingual Request Intent Classifier.
Determines whether a user request authorizes account and personal data deletion.
Requests for access, export, rectification, marketing opt-out, or general inquiries
without deletion authorization are classified as NOT_APPLICABLE.
"""

import re
from typing import Tuple

DELETION_RE = re.compile(
    r"\b(?:"
    r"delet\w*|remov\w*|eras\w*|purg\w*|destroy\w*|forget\w*|wipe\w*|"
    r"clos\w*\s+(?:the|my|this)?\s*account|account\s+(?:is|was|had been)\s+(?:closed|deleted|gone)|"
    r"profile\s+is\s+gone|no\s+longer\s+need\s+this\s+account|"
    r"supprim\w*|suppress\w*|effac\w*|elimin\w*|borr\w*|lösch\w*|entfern\w*|cancell\w*|apag\w*|exclu\w*"
    r")\b|削除|消去|탈퇴",
    re.IGNORECASE
)

# Pure non-deletion patterns: access, download, portability, rectification, or marketing opt-out
NON_DELETION_RE = re.compile(
    r"\b(?:"
    r"keep (?:the|my|this) account (?:as it is|open|active)|do not delete|"
    r"export my data|download my (?:account|data|information)|copy of my data|portable format|"
    r"subject access request|access request|what information do you hold|"
    r"rectify|rectification|update my|correct my|change my|"
    r"unsubscribe|marketing emails|newsletter|opt-out of marketing"
    r")\b|"
    r"データをエクスポート|ダウンロード|アカウントは維持|데이터 사본|수정|광고 수신 거부",
    re.IGNORECASE
)


def authorizes_deletion(request_text: str) -> Tuple[bool, str]:
    """
    Classify whether request_text authorizes deletion.
    Returns:
        (is_authorized, reason)
    """
    if not request_text or not request_text.strip():
        return False, "EMPTY_REQUEST"

    text = request_text.strip()

    # 1. Explicit statements to keep the account active/open
    if re.search(r"keep (?:the|my|this) account (?:as it is|open|active)", text, re.IGNORECASE):
        return False, "EXPLICIT_KEEP_ACCOUNT"

    # 2. Check deletion keywords
    has_deletion = bool(DELETION_RE.search(text))

    # 3. Check pure non-deletion keywords
    has_non_deletion = bool(NON_DELETION_RE.search(text))

    if has_deletion:
        # If user explicitly asks for export or download AND says to keep account or doesn't authorize deletion:
        if has_non_deletion and ("keep" in text.lower() or "portable format" in text.lower()):
            return False, "NON_DELETION_REQUEST"
        return True, "DELETION_AUTHORIZED"

    if has_non_deletion:
        return False, "NON_DELETION_REQUEST"

    # Fallback default
    return False, "NO_DELETION_INTENT_DETECTED"
