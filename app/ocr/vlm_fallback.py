# """
# vlm_fallback.py
# ===============

# OPTIONAL local vision-model fallback for fuzzy documents that have no fixed
# format — offer letters, salary slips, W2s, degree certificates, green cards.
# The deterministic layer can't anchor those, so if it comes up empty we hand
# the image to a self-hosted VLM (Qwen2.5-VL served by Ollama) and ask for the
# same JSON your Claude prompt asked for.

# This is a drop-in for the *understanding* step only. It is disabled by default
# because a 7B VLM really wants a GPU to be fast enough for interactive use.
# Enable it with env:

#     VLM_ENABLED=true
#     VLM_BASE_URL=http://localhost:11434/v1     # Ollama's OpenAI-compatible API
#     VLM_MODEL=qwen2.5vl:7b

# Serve the model first: 
#     ollama pull qwen2.5vl:7b
#     ollama serve            # exposes http://localhost:11434

# Design note: every failure path returns None. The endpoint treats None as
# "VLM gave nothing" and falls back to whatever the deterministic layer produced,
# so a down/parse-failed VLM never breaks OCR — it just means less coverage on
# the fuzzy docs.
# """

# from __future__ import annotations

# import base64
# import json
# import os
# from typing import Optional

# import httpx


# VLM_ENABLED = os.getenv("VLM_ENABLED", "false").lower() in ("1", "true", "yes")
# VLM_BASE_URL = os.getenv("VLM_BASE_URL", "http://localhost:11434/v1").rstrip("/")
# VLM_MODEL = os.getenv("VLM_MODEL", "qwen2.5vl:7b")


# # Reuses your existing extraction instructions + document_type vocabulary so
# # downstream code sees the same values it does today.
# _SYSTEM_PROMPT = """You are a document OCR extractor for an immigration application platform.

# Extract ALL relevant fields from the document image.
# Return ONLY a JSON object — no explanation, no markdown, no backticks.

# Format:
# {
#   "document_type": "passport | aadhaar | pan_card | i797 | i94 | ead_card | green_card | offer_letter | salary_slip | w2 | form_16 | degree | other",
#   "fields": [
#     { "field_name": "Passport Number", "extracted_value": "X11000344", "confidence_score": 99, "needs_review": false }
#   ]
# }

# Rules:
# - confidence_score: 99 if clearly readable, 85 if slightly unclear, 70 if guessed, 50 if uncertain
# - needs_review: true if confidence_score < 80
# - Extract every field visible — name, dates, numbers, codes, addresses, amounts
# - For salary documents extract: gross pay, net pay, deductions, pay period, employer name
# - For offer letters extract: job title, salary/CTC, start date, employer, location
# - For degree certificates extract: name, degree, institution, year, grade/GPA
# - For Indian documents handle both English and transliterated fields
# - If a field is partially visible or unclear, still extract it and set needs_review: true"""


# def _sanitize_fields(raw_fields) -> list[dict]:
#     """Force VLM output into the exact OCRField shape; drop anything malformed."""
#     clean: list[dict] = []
#     if not isinstance(raw_fields, list):
#         return clean
#     for f in raw_fields:
#         if not isinstance(f, dict):
#             continue
#         name = str(f.get("field_name", "")).strip()
#         value = str(f.get("extracted_value", "")).strip()
#         if not name or not value:
#             continue
#         try:
#             conf = int(round(float(f.get("confidence_score", 70))))
#         except (TypeError, ValueError):
#             conf = 70
#         conf = max(0, min(100, conf))
#         review = f.get("needs_review")
#         if not isinstance(review, bool):
#             review = conf < 80
#         clean.append({
#             "field_name": name,
#             "extracted_value": value,
#             "confidence_score": conf,
#             "needs_review": review,
#         })
#     return clean


# def _parse_json_blob(text: str) -> Optional[dict]:
#     """Parse the model's reply, tolerating ```json fences / stray prose."""
#     if not text:
#         return None
#     try:
#         return json.loads(text)
#     except json.JSONDecodeError:
#         pass
#     cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
#     try:
#         return json.loads(cleaned)
#     except json.JSONDecodeError:
#         # last resort: grab the outermost { ... }
#         start, end = cleaned.find("{"), cleaned.rfind("}")
#         if start != -1 and end != -1 and end > start:
#             try:
#                 return json.loads(cleaned[start:end + 1])
#             except json.JSONDecodeError:
#                 return None
#     return None


# async def extract_with_vlm(
#     image_bytes: bytes,
#     media_type: str = "image/png",
# ) -> Optional[tuple[str, list[dict]]]:
#     """
#     Send the image to the local VLM and return (document_type, fields), or
#     None on any failure. Never raises — the caller degrades to deterministic.
#     """
#     if not VLM_ENABLED:
#         return None

#     b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
#     data_uri = f"data:{media_type};base64,{b64}"

#     payload = {
#         "model": VLM_MODEL,
#         "max_tokens": 1500,
#         "temperature": 0,  # deterministic extraction, no creativity
#         "messages": [
#             {"role": "system", "content": _SYSTEM_PROMPT},
#             {"role": "user", "content": [
#                 {"type": "text", "text": "Extract all fields from this immigration document."},
#                 {"type": "image_url", "image_url": {"url": data_uri}},
#             ]},
#         ],
#     }

#     try:
#         async with httpx.AsyncClient(timeout=120.0) as client:
#             resp = await client.post(
#                 f"{VLM_BASE_URL}/chat/completions",
#                 json=payload,
#                 headers={"content-type": "application/json"},
#             )
#         if resp.status_code != 200:
#             print(f"[VLM] non-200 from local model: {resp.status_code} {resp.text[:200]}")
#             return None
#         content = resp.json()["choices"][0]["message"]["content"]
#     except Exception as e:  # network down, timeout, bad shape — all non-fatal
#         print(f"[VLM] local model call failed ({type(e).__name__}): {e}")
#         return None 

#     data = _parse_json_blob(content)
#     if not isinstance(data, dict):
#         print("[VLM] could not parse JSON from model reply")
#         return None

#     doc_type = str(data.get("document_type", "other")).strip() or "other"
#     fields = _sanitize_fields(data.get("fields", []))
#     return doc_type, fields


"""
vlm_fallback.py
===============

OPTIONAL local vision-model fallback for fuzzy documents that have no fixed
format — offer letters, salary slips, W2s, degree certificates, green cards.
The deterministic layer can't anchor those, so if it comes up empty we hand
the image to a self-hosted VLM (Qwen2.5-VL served by Ollama) and ask for the
same JSON your Claude prompt asked for.

This is a drop-in for the *understanding* step only. It is disabled by default
because a 7B VLM really wants a GPU to be fast enough for interactive use.
Enable it with env:

    VLM_ENABLED=true
    VLM_BASE_URL=http://localhost:11434/v1     # Ollama's OpenAI-compatible API
    VLM_MODEL=qwen2.5vl:7b
    VLM_TIMEOUT_SECONDS=120                    # optional, defaults to 120

Serve the model first:
    ollama pull qwen2.5vl:7b
    ollama serve            # exposes http://localhost:11434

Design note: every failure path returns None. The endpoint treats None as
"VLM gave nothing" and falls back to whatever the deterministic layer produced,
so a down/parse-failed VLM never breaks OCR — it just means less coverage on
the fuzzy docs.

TRUST POLICY (important — read before changing):
--------------------------------------------------
VLM confidence scores are the model's own self-assessment, not a validated
checksum like the deterministic layer's MRZ/Verhoeff checks. A VLM saying
"99% confident" is a guess, not a guarantee. Your DB auto-confirms anything
with confidence >= 90 and needs_review=False — so an overconfident VLM
field could otherwise skip human review entirely on a legal filing. To
prevent that, this module UNCONDITIONALLY caps VLM-sourced confidence
below the auto-confirm threshold and forces needs_review=True on every
field, regardless of what the model itself claims. Do not remove this cap
without a deliberate, separate decision — it's the same "human sees it
before it touches a filing" principle the deterministic layer already
enforces for real checksum failures.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import re
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

VLM_ENABLED = os.getenv("VLM_ENABLED", "false").lower() in ("1", "true", "yes")
VLM_BASE_URL = os.getenv("VLM_BASE_URL", "http://localhost:11434/v1").rstrip("/")
VLM_MODEL = os.getenv("VLM_MODEL", "qwen2.5vl:7b")
VLM_TIMEOUT_SECONDS = float(os.getenv("VLM_TIMEOUT_SECONDS", "120"))

# Never let a VLM field auto-confirm, no matter what the model claims.
# Your DB's auto-confirm rule is `confidence >= 90 and not needs_review` —
# this cap keeps VLM output permanently below that threshold.
_MAX_VLM_CONFIDENCE = 85


# ─────────────────────────────────────────────────────────────────────────────
# PER-DOCUMENT-TYPE FIELD SPECS
# Structured, not prose — add a new fuzzy type by adding one dict entry here,
# not by editing a paragraph of English inside the system prompt.
# ─────────────────────────────────────────────────────────────────────────────

FIELD_SPECS: dict[str, list[str]] = {
    "offer_letter": [
        "employee_name", "job_title", "employer_name", "ctc_or_salary",
        "start_date", "offer_date", "probation_period",
        "signatory_name", "signatory_title",
    ],
    "salary_slip": [
        "employee_name", "employer_name", "pay_period", "gross_pay",
        "net_pay", "total_deductions", "pay_date",
    ],
    "w2": [
        "employee_name", "employer_name", "employer_ein", "wages_tips_income",
        "federal_income_tax_withheld", "tax_year",
    ],
    "form_16": [
        "employee_name", "employer_name", "employer_tan", "assessment_year",
        "gross_salary", "tax_deducted",
    ],
    "degree": [
        "student_name", "degree_name", "institution_name",
        "graduation_year", "grade_or_gpa",
    ],
    "green_card": [
        "full_name", "uscis_number", "category", "date_of_birth",
        "card_expires", "resident_since",
    ],
}

_DEFAULT_FIELDS = [
    "document_title", "name", "date", "reference_number", "issuing_organization",
]


def _build_system_prompt() -> str:
    """Builds the prompt from FIELD_SPECS so extending coverage never means
    hand-editing prose — just add a dict entry above."""
    lines = [
        "You are a document OCR extractor for an immigration application platform.",
        "",
        "Extract ALL relevant fields from the document image.",
        "Return ONLY a JSON object — no explanation, no markdown, no backticks.",
        "",
        "Format:",
        "{",
        '  "document_type": "' + " | ".join(sorted({"passport", "aadhaar", "pan_card",
            "i797", "i94", "ead_card", *FIELD_SPECS.keys(), "other"})) + '",',
        '  "fields": [',
        '    { "field_name": "job_title", "extracted_value": "Software Engineer", '
        '"confidence_score": 85, "needs_review": true }',
        "  ]",
        "}",
        "",
        "Rules:",
        "- field_name MUST be snake_case (lowercase, underscores, no spaces) — "
        'e.g. "job_title" not "Job Title".',
        "- confidence_score: your honest self-assessment 0-100, but every field WILL "
        "be treated as needing human review regardless of this score — this is not "
        "a shortcut past review, just your best-effort signal for the reviewer.",
        "- Extract every field visible — name, dates, numbers, codes, addresses, amounts.",
        "- If a field is partially visible or unclear, still extract it and note low confidence.",
        "",
        "Expected fields by document type (extract these specifically when present, "
        "plus anything else visibly relevant):",
    ]
    for doc_type, fields in FIELD_SPECS.items():
        lines.append(f"- {doc_type}: {', '.join(fields)}")
    lines.append(f"- (any other/unrecognized type): {', '.join(_DEFAULT_FIELDS)}")
    return "\n".join(lines)


_SYSTEM_PROMPT = _build_system_prompt()


# ─────────────────────────────────────────────────────────────────────────────
# FIELD NAME NORMALIZATION
# The deterministic layer emits snake_case (passport_number, given_names).
# VLM output should match that convention for consistency across the app —
# enforce it here rather than trusting the model's compliance with the prompt.
# ─────────────────────────────────────────────────────────────────────────────

def _to_snake_case(name: str) -> str:
    name = name.strip()
    name = re.sub(r"[^\w\s]", "", name)          # drop punctuation
    name = re.sub(r"\s+", "_", name)              # spaces → underscores
    name = re.sub(r"(?<!^)(?=[A-Z])", "_", name)   # camelCase → snake_case
    return name.lower().strip("_") or "unnamed_field"


def _sanitize_fields(raw_fields) -> list[dict]:
    """
    Force VLM output into the exact OCRField shape; drop anything malformed.
    Applies the confidence cap and forced needs_review per the trust policy
    documented at the top of this file — this is NOT optional cleanup, it's
    the safety boundary between "model guess" and "auto-confirmed data."
    """
    clean: list[dict] = []
    if not isinstance(raw_fields, list):
        return clean
    for f in raw_fields:
        if not isinstance(f, dict):
            continue
        name = _to_snake_case(str(f.get("field_name", "")))
        value = str(f.get("extracted_value", "")).strip()
        if not name or not value:
            continue
        try:
            conf = int(round(float(f.get("confidence_score", 70))))
        except (TypeError, ValueError):
            conf = 70
        conf = max(0, min(_MAX_VLM_CONFIDENCE, conf))  # capped — see trust policy
        clean.append({
            "field_name": name,
            "extracted_value": value,
            "confidence_score": conf,
            "needs_review": True,  # always — see trust policy at top of file
        })
    return clean


def _parse_json_blob(text: str) -> Optional[dict]:
    """Parse the model's reply, tolerating ```json fences / stray prose."""
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(cleaned[start:end + 1])
            except json.JSONDecodeError:
                return None
    return None


async def _call_vlm_once(payload: dict) -> Optional[str]:
    """One HTTP attempt. Returns the raw content string, or None on failure."""
    try:
        async with httpx.AsyncClient(timeout=VLM_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                f"{VLM_BASE_URL}/chat/completions",
                json=payload,
                headers={"content-type": "application/json"},
            )
        if resp.status_code != 200:
            logger.warning("VLM non-200 response: %s %s", resp.status_code, resp.text[:300])
            return None
        return resp.json()["choices"][0]["message"]["content"]
    except httpx.TimeoutException:
        logger.warning("VLM call timed out after %.0fs", VLM_TIMEOUT_SECONDS)
        return None
    except Exception as e:
        logger.warning("VLM call failed (%s): %s", type(e).__name__, e)
        return None


async def extract_with_vlm(
    image_bytes: bytes,
    media_type: str = "image/png",
) -> Optional[tuple[str, list[dict]]]:
    """
    Send the image to the local VLM and return (document_type, fields), or
    None on any failure. Never raises — the caller degrades to deterministic.

    Retries the JSON parse ONCE with a stricter follow-up if the first reply
    doesn't parse — cheap insurance against a model that ignored the
    "JSON only" instruction on the first try.
    """
    if not VLM_ENABLED:
        return None

    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    data_uri = f"data:{media_type};base64,{b64}"

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": [
            {"type": "text", "text": "Extract all fields from this immigration document."},
            {"type": "image_url", "image_url": {"url": data_uri}},
        ]},
    ]

    payload = {
        "model": VLM_MODEL,
        "max_tokens": 1500,
        "temperature": 0,  # deterministic extraction, no creativity
        "messages": messages,
    }

    content = await _call_vlm_once(payload)
    data = _parse_json_blob(content) if content else None

    if not isinstance(data, dict):
        # One retry, telling it plainly that the first reply didn't parse.
        logger.info("VLM reply didn't parse as JSON, retrying once with a stricter prompt")
        messages.append({"role": "assistant", "content": content or ""})
        messages.append({
            "role": "user",
            "content": "Your last reply was not valid JSON. Reply with ONLY the JSON "
                        "object, nothing else — no markdown fences, no explanation.",
        })
        payload["messages"] = messages
        content = await _call_vlm_once(payload)
        data = _parse_json_blob(content) if content else None

    if not isinstance(data, dict):
        logger.warning("VLM reply could not be parsed as JSON after retry")
        return None

    doc_type = _to_snake_case(str(data.get("document_type", "other")).strip() or "other")
    fields = _sanitize_fields(data.get("fields", []))
    return doc_type, fields