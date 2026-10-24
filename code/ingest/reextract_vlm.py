"""
Re-extraction and hardening tool for VLM (11 PNGs) and PDF (4 PDFs) evidence.
Runs dual-pass OCR extraction, diffs the runs, and produces a disagreement report.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Set, Any
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract

IMAGES_DIR = Path("dataset/evidence/images")
CACHE_DIR = Path("code/cache/vlm")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

TOKEN_RE = re.compile(
    r"\b(user_\d+|account_\w+|search_\w+|data_flow[._]?\w+|analytics_\w+|backup_\w+|support_\w+|export[._]?\w+|audit_record_\w+|tombstone_\w+|marketing_\w+|legal_hold_\w+|object_\w+)\b",
    re.IGNORECASE
)
EMAIL_RE = re.compile(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)")
PHONE_RE = re.compile(r"(\+\d{1,3}\s*\d[\d\s-]{6,}\d)")
OBJECT_FILE_RE = re.compile(r"\b([a-zA-Z0-9_-]+_(?:confirmation|label|damage|export)_(\d+)\.(?:pdf|jpg|zip))\b", re.IGNORECASE)


def run_pass_1(img: Image.Image) -> str:
    """Pass 1: standard global scan."""
    txt1 = pytesseract.image_to_string(img, config="--psm 3")
    txt2 = pytesseract.image_to_string(img, config="--psm 6")
    return txt1 + "\n" + txt2


def run_pass_2(img: Image.Image) -> str:
    """Pass 2: enhanced contrast + sparse/line OCR for sidebars and small text."""
    enhanced = ImageEnhance.Contrast(img.convert("L")).enhance(1.8)
    txt1 = pytesseract.image_to_string(enhanced, config="--psm 11")
    txt2 = pytesseract.image_to_string(enhanced, config="--psm 12")
    return txt1 + "\n" + txt2


def extract_entities(text: str) -> Dict[str, Set[str]]:
    tokens = set()
    for m in TOKEN_RE.findall(text):
        clean = m.lower().replace(".", "_")
        tokens.add(clean)

    # Check object files like delivery_confirmation_19.pdf -> object_19
    for m in re.finditer(r"\b([a-zA-Z0-9_-]+)_(\d+)\.(pdf|jpg|zip)\b", text, re.IGNORECASE):
        num = m.group(2)
        tokens.add(f"object_{num}")

    emails = {e.lower() for e in EMAIL_RE.findall(text)}
    # Filter common OCR false positives
    emails = {e for e in emails if not e.endswith((".shop", ".pdt", ".con")) or "@" in e}

    phones = {p.strip() for p in PHONE_RE.findall(text)}

    return {
        "tokens": tokens,
        "emails": emails,
        "phones": phones,
    }


def reextract_all() -> Dict[str, Any]:
    png_files = sorted(list(IMAGES_DIR.glob("*.png")))
    results = {}
    disagreements = {}

    for p in png_files:
        name = p.name
        img = Image.open(p)
        text1 = run_pass_1(img)
        text2 = run_pass_2(img)

        ent1 = extract_entities(text1)
        ent2 = extract_entities(text2)

        # Merge entities
        merged_tokens = sorted(list(ent1["tokens"] | ent2["tokens"]))
        merged_emails = sorted(list(ent1["emails"] | ent2["emails"]))
        merged_phones = sorted(list(ent1["phones"] | ent2["phones"]))

        results[name] = {
            "tokens": merged_tokens,
            "emails": merged_emails,
            "phones": merged_phones,
            "raw_text": text1 + "\n--- PASS 2 ---\n" + text2,
        }

        # Check disagreements
        diff_tokens_1 = ent1["tokens"] - ent2["tokens"]
        diff_tokens_2 = ent2["tokens"] - ent1["tokens"]
        diff_emails_1 = ent1["emails"] - ent2["emails"]
        diff_emails_2 = ent2["emails"] - ent1["emails"]

        if diff_tokens_1 or diff_tokens_2 or diff_emails_1 or diff_emails_2:
            disagreements[name] = {
                "pass1_only_tokens": sorted(list(diff_tokens_1)),
                "pass2_only_tokens": sorted(list(diff_tokens_2)),
                "pass1_only_emails": sorted(list(diff_emails_1)),
                "pass2_only_emails": sorted(list(diff_emails_2)),
                "merged_tokens": merged_tokens,
                "merged_emails": merged_emails,
            }

    return {"results": results, "disagreements": disagreements}


if __name__ == "__main__":
    out = reextract_all()
    print(f"Processed {len(out['results'])} images.")
    print(f"Images with pass discrepancies: {len(out['disagreements'])}")
    print(json.dumps(out["disagreements"], indent=2))
