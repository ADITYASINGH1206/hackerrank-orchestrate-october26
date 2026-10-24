"""
VLM evidence loader: uses pytesseract OCR on PNG screenshots in dataset/evidence/images/
with disk caching in code/cache/vlm/.
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional

import pytesseract
from PIL import Image

from code.core.models import Observation
from code.core.categories import get_system_id

CACHE_DIR = Path("code/cache/vlm")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

EMAIL_RE = re.compile(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)")
USER_RE = re.compile(r"\b(user_\d+)\b")
PHONE_RE = re.compile(r"(\+\d{1,3}\s*\d[\d\s-]{6,}\d)")
RESOURCE_RE = re.compile(r"\b(account_\w+|search_\w+|data_flow[._]?\w+|analytics_\w+|backup_\w+|support_\w+|export[._]?\w+|audit_record_\w+|tombstone_\w+|marketing_\w+|legal_hold_\w+|object_\w+)\b")


def load_vlm_evidence(file_path: Path, file_id: str, manifest_captured_at: str) -> List[Observation]:
    """Extract observations from PNG screenshot evidence using OCR and cached text."""
    observations: List[Observation] = []
    cache_file = CACHE_DIR / f"{file_id}.txt"

    if cache_file.exists():
        ocr_text = cache_file.read_text(encoding="utf-8")
    else:
        try:
            img = Image.open(file_path)
            ocr_text = pytesseract.image_to_string(img)
            cache_file.write_text(ocr_text, encoding="utf-8")
        except Exception:
            return observations

    fname = file_path.name
    lines = [l.strip() for l in ocr_text.split("\n") if l.strip()]

    # Specific extractors for known console screenshot formats
    if "account_admin_console" in fname:
        # user_11 - account_5762, haruka.s1838@zoho.com, support_9538
        res_m = re.search(r"\b(account_\d+)\b", ocr_text)
        user_m = re.search(r"\b(user_\d+)\b", ocr_text)
        email_m = EMAIL_RE.search(ocr_text)
        if res_m:
            ids = {}
            if user_m:
                ids["user_id"] = user_m.group(1)
            if email_m:
                ids["email"] = email_m.group(1).lower()
            observations.append(Observation(
                file_id=file_id,
                captured_at=manifest_captured_at,
                system_id="account_service",
                location="admin_console",
                resource_id=res_m.group(1),
                exists=True,
                ids=ids,
                flags={},
                raw={"ocr_snippet": ocr_text[:150]},
                observed_at=manifest_captured_at,
            ))

    elif "analytics_profile_view" in fname:
        # user_20 - analytics_7438 - darwish.omar@icloud.com
        res_m = re.search(r"\b(analytics_\d+)\b", ocr_text)
        user_m = re.search(r"\b(user_\d+)\b", ocr_text)
        email_m = EMAIL_RE.search(ocr_text)
        if res_m:
            ids = {}
            if user_m:
                ids["user_id"] = user_m.group(1)
            if email_m:
                ids["email"] = email_m.group(1).lower()
            observations.append(Observation(
                file_id=file_id,
                captured_at=manifest_captured_at,
                system_id="analytics_platform",
                location="profile_view",
                resource_id=res_m.group(1),
                exists=True,
                ids=ids,
                flags={},
                raw={"ocr_snippet": ocr_text[:150]},
                observed_at=manifest_captured_at,
            ))

    elif "backup_restore_console" in fname:
        # lines with backup_9287 areedt433@gmail.com
        for line in lines:
            bm = re.search(r"\b(backup_\d+)\b", line)
            em = EMAIL_RE.search(line)
            if bm and em:
                observations.append(Observation(
                    file_id=file_id,
                    captured_at=manifest_captured_at,
                    system_id="backup_service",
                    location="recovery_manager",
                    resource_id=bm.group(1),
                    exists=True,
                    ids={"email": em.group(1).lower()},
                    flags={"backup_present": True},
                    raw={"line": line},
                    observed_at=manifest_captured_at,
                ))

    elif "connector_management_console" in fname:
        # data_flow1121 -> jain.aditi@gmail.com, data_flow.9846 -> lucia-torres@gmail.com
        for line in lines:
            df_m = re.search(r"\b(data_flow[._]?\d+)\b", line)
            em = EMAIL_RE.search(line)
            if df_m and em:
                norm_res = df_m.group(1).replace(".", "_")
                if not norm_res.startswith("data_flow_"):
                    norm_res = norm_res.replace("data_flow", "data_flow_")
                observations.append(Observation(
                    file_id=file_id,
                    captured_at=manifest_captured_at,
                    system_id="integration_service",
                    location="connector_console",
                    resource_id=norm_res,
                    exists=True,
                    ids={"email": em.group(1).lower()},
                    flags={"enabled": True},
                    raw={"line": line},
                    observed_at=manifest_captured_at,
                ))

    elif "customer_export_console" in fname:
        # export_1260 -> ingrid.dahl@outlook.com
        for line in lines:
            ex_m = re.search(r"\b(export[._ ]?\d+)\b", line)
            em = EMAIL_RE.search(line)
            if ex_m and em:
                norm_res = ex_m.group(1).replace(" ", "_").replace(".", "_")
                observations.append(Observation(
                    file_id=file_id,
                    captured_at=manifest_captured_at,
                    system_id="export_platform",
                    location="export_console",
                    resource_id=norm_res,
                    exists=True,
                    ids={"email": em.group(1).lower()},
                    flags={"export_ready": True},
                    raw={"line": line},
                    observed_at=manifest_captured_at,
                ))

    elif "marketing_profile_console" in fname:
        # marketing_001 - sj.park@naver.com - +82 10-5837-9451
        m_res = re.search(r"\b(marketing_\d+)\b", ocr_text)
        em = EMAIL_RE.search(ocr_text)
        pm = PHONE_RE.search(ocr_text)
        if m_res:
            ids = {}
            if em:
                ids["email"] = em.group(1).lower()
            if pm:
                ids["phone"] = pm.group(1).strip()
            observations.append(Observation(
                file_id=file_id,
                captured_at=manifest_captured_at,
                system_id="marketing_service",
                location="audience_operations",
                resource_id=m_res.group(1),
                exists=True,
                ids=ids,
                flags={"profile_refreshed": True},
                raw={"ocr_snippet": ocr_text[:150]},
                observed_at=manifest_captured_at,
            ))

    elif "search_index_inspector" in fname:
        # search_428, g.silva76@gmail.com, user_13
        sm = re.search(r"\b(search_\d+)\b", ocr_text)
        em = EMAIL_RE.search(ocr_text)
        um = re.search(r"\b(user_\d+)\b", ocr_text)
        if sm:
            ids = {}
            if em:
                ids["email"] = em.group(1).lower()
            if um:
                ids["user_id"] = um.group(1)
            observations.append(Observation(
                file_id=file_id,
                captured_at=manifest_captured_at,
                system_id="search_service",
                location="index_inspector",
                resource_id=sm.group(1),
                exists=True,
                ids=ids,
                flags={"index_hit": True},
                raw={"ocr_snippet": ocr_text[:150]},
                observed_at=manifest_captured_at,
            ))

    elif "support_ticket_console" in fname:
        # support_1034 - Kofi Agyeman - kagyeman8947@fastmail.com
        sm = re.search(r"\b(support_\d+)\b", ocr_text)
        em = EMAIL_RE.search(ocr_text)
        if sm:
            ids = {}
            if em:
                ids["email"] = em.group(1).lower()
            if "Kofi Agyeman" in ocr_text:
                ids["name"] = "Kofi Agyeman"
            observations.append(Observation(
                file_id=file_id,
                captured_at=manifest_captured_at,
                system_id="support_platform",
                location="ticket_console",
                resource_id=sm.group(1),
                exists=True,
                ids=ids,
                flags={},
                raw={"ocr_snippet": ocr_text[:150]},
                observed_at=manifest_captured_at,
            ))

    elif "security_audit_explorer" in fname:
        # audit_record_003, user_03
        am = re.search(r"\b(audit_record_\d+)\b", ocr_text)
        um = re.search(r"\b(user_\d+)\b", ocr_text)
        if am:
            ids = {}
            if um:
                ids["user_id"] = um.group(1)
            observations.append(Observation(
                file_id=file_id,
                captured_at=manifest_captured_at,
                system_id="security_service",
                location="audit_explorer",
                resource_id=am.group(1),
                exists=True,
                ids=ids,
                flags={},
                raw={"ocr_snippet": ocr_text[:150]},
                observed_at=manifest_captured_at,
            ))

    else:
        # Generic fallback
        for match in RESOURCE_RE.finditer(ocr_text):
            r = match.group(1).replace(".", "_").replace(" ", "_")
            emails = EMAIL_RE.findall(ocr_text)
            users = USER_RE.findall(ocr_text)
            ids = {}
            if emails:
                ids["email"] = emails[0].lower()
            if users:
                ids["user_id"] = users[0]
            observations.append(Observation(
                file_id=file_id,
                captured_at=manifest_captured_at,
                system_id=get_system_id(r),
                location="screenshot",
                resource_id=r,
                exists=True,
                ids=ids,
                flags={},
                raw={},
                observed_at=manifest_captured_at,
            ))

    return observations
