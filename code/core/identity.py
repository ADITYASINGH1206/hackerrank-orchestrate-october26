"""
Identity resolution module for Ghost Data Still Exists.
Resolves stable user_id, current and historical emails, phones, names, and SHA-256 hashes.
"""

import hashlib
from dataclasses import dataclass, field
from typing import Set, Optional

from code.core.store import ObservationStore


def sha256_hash(text: str) -> str:
    """Compute standard SHA-256 hex digest of string."""
    return hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()


@dataclass
class IdentitySet:
    user_id: Optional[str] = None
    emails: Set[str] = field(default_factory=set)
    phones: Set[str] = field(default_factory=set)
    email_hashes: Set[str] = field(default_factory=set)
    names: Set[str] = field(default_factory=set)

    def matches(self, ids: dict) -> bool:
        """Check if any ID dictionary matches this identity set."""
        if not ids:
            return False
            
        # Match user_id
        if self.user_id and ids.get("user_id"):
            if ids["user_id"] == self.user_id:
                return True
                
        # Match email
        if ids.get("email"):
            if ids["email"].strip().lower() in self.emails:
                return True

        # Match email hash
        if ids.get("email_hash"):
            if ids["email_hash"].strip().lower() in self.email_hashes:
                return True

        # Match phone
        if ids.get("phone"):
            p_clean = ids["phone"].replace(" ", "").replace("-", "")
            for ph in self.phones:
                if ph.replace(" ", "").replace("-", "") == p_clean:
                    return True

        return False


def resolve_identity(request_email: str, store: ObservationStore) -> IdentitySet:
    """
    Given a request email (current or historical), resolve the full identity set:
    user_id, all historical emails, all phones, all names, and all SHA-256 hashes.
    """
    clean_email = request_email.strip().lower()
    ident_set = IdentitySet()
    ident_set.emails.add(clean_email)
    ident_set.email_hashes.add(sha256_hash(clean_email))

    # 1. Check direct current identity by email
    ui = store.identities_by_email.get(clean_email)

    # 2. Check if clean_email is an email hash
    if not ui and len(clean_email) == 64:
        ui = store.identities_by_hash.get(clean_email)

    # 3. If not found, check audit logs for historical email matches
    if not ui:
        historical_logs = store.audit_logs_by_email.get(clean_email, [])
        if historical_logs:
            matched_user_id = historical_logs[0].user_id
            ui = store.identities.get(matched_user_id)

    # 4. If user identity snapshot found, populate current fields
    if ui:
        ident_set.user_id = ui.user_id
        if ui.email:
            e_low = ui.email.strip().lower()
            ident_set.emails.add(e_low)
            ident_set.email_hashes.add(sha256_hash(e_low))
        if ui.email_hash:
            ident_set.email_hashes.add(ui.email_hash.strip().lower())
        if ui.phone:
            ident_set.phones.add(ui.phone.strip())
        if ui.name:
            ident_set.names.add(ui.name.strip())

    # 5. Expand all historical identity fields from user_audit_log
    if ident_set.user_id:
        user_logs = store.audit_logs_by_user_id.get(ident_set.user_id, [])
        for entry in user_logs:
            field = entry.field_name.strip()
            old_val = entry.old_value.strip()
            new_val = entry.new_value.strip()

            if field == "email":
                if old_val:
                    o_low = old_val.lower()
                    ident_set.emails.add(o_low)
                    ident_set.email_hashes.add(sha256_hash(o_low))
                if new_val:
                    n_low = new_val.lower()
                    ident_set.emails.add(n_low)
                    ident_set.email_hashes.add(sha256_hash(n_low))

            elif field == "email_hash":
                if old_val:
                    ident_set.email_hashes.add(old_val.lower())
                if new_val:
                    ident_set.email_hashes.add(new_val.lower())

            elif field == "phone":
                if old_val:
                    ident_set.phones.add(old_val)
                if new_val:
                    ident_set.phones.add(new_val)

            elif field in ("name", "full_name"):
                if old_val:
                    ident_set.names.add(old_val)
                if new_val:
                    ident_set.names.add(new_val)

    # 6. Ensure all email variants have their SHA-256 hash computed
    for em in list(ident_set.emails):
        ident_set.email_hashes.add(sha256_hash(em))

    return ident_set
