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

Serve the model first:
    ollama pull qwen2.5vl:7b
    ollama serve            # exposes http://localhost:11434

Design note: every failure path returns None. The endpoint treats None as
"VLM gave nothing" and falls back to whatever the deterministic layer produced,
so a down/parse-failed VLM never breaks OCR — it just means less coverage on
the fuzzy docs.
"""

from __future__ import annotations

import base64
import json
import os
from typing import Optional

import httpx


VLM_ENABLED = os.getenv("VLM_ENABLED", "false").lower() in ("1", "true", "yes")
VLM_BASE_URL = os.getenv("VLM_BASE_URL", "http://localhost:11434/v1").rstrip("/")
VLM_MODEL = os.getenv("VLM_MODEL", "qwen2.5vl:7b")


# Reuses your existing extraction instructions + document_type vocabulary so
# downstream code sees the same values it does today.
_SYSTEM_PROMPT = """You are a document OCR extractor for an immigration application platform.

Extract ALL relevant fields from the document image.
Return ONLY a JSON object — no explanation, no markdown, no backticks.

Format:
{
  "document_type": "passport | aadhaar | pan_card | i797 | i94 | ead_card | green_card | offer_letter | salary_slip | w2 | form_16 | degree | other",
  "fields": [
    { "field_name": "Passport Number", "extracted_value": "X11000344", "confidence_score": 99, "needs_review": false }
  ]
}

Rules:
- confidence_score: 99 if clearly readable, 85 if slightly unclear, 70 if guessed, 50 if uncertain
- needs_review: true if confidence_score < 80
- Extract every field visible — name, dates, numbers, codes, addresses, amounts
- For salary documents extract: gross pay, net pay, deductions, pay period, employer name
- For offer letters extract: job title, salary/CTC, start date, employer, location
- For degree certificates extract: name, degree, institution, year, grade/GPA
- For Indian documents handle both English and transliterated fields
- If a field is partially visible or unclear, still extract it and set needs_review: true"""


def _sanitize_fields(raw_fields) -> list[dict]:
    """Force VLM output into the exact OCRField shape; drop anything malformed."""
    clean: list[dict] = []
    if not isinstance(raw_fields, list):
        return clean
    for f in raw_fields:
        if not isinstance(f, dict):
            continue
        name = str(f.get("field_name", "")).strip()
        value = str(f.get("extracted_value", "")).strip()
        if not name or not value:
            continue
        try:
            conf = int(round(float(f.get("confidence_score", 70))))
        except (TypeError, ValueError):
            conf = 70
        conf = max(0, min(100, conf))
        review = f.get("needs_review")
        if not isinstance(review, bool):
            review = conf < 80
        clean.append({
            "field_name": name,
            "extracted_value": value,
            "confidence_score": conf,
            "needs_review": review,
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
        # last resort: grab the outermost { ... }
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(cleaned[start:end + 1])
            except json.JSONDecodeError:
                return None
    return None


async def extract_with_vlm(
    image_bytes: bytes,
    media_type: str = "image/png",
) -> Optional[tuple[str, list[dict]]]:
    """
    Send the image to the local VLM and return (document_type, fields), or
    None on any failure. Never raises — the caller degrades to deterministic.
    """
    if not VLM_ENABLED:
        return None

    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    data_uri = f"data:{media_type};base64,{b64}"

    payload = {
        "model": VLM_MODEL,
        "max_tokens": 1500,
        "temperature": 0,  # deterministic extraction, no creativity
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": [
                {"type": "text", "text": "Extract all fields from this immigration document."},
                {"type": "image_url", "image_url": {"url": data_uri}},
            ]},
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{VLM_BASE_URL}/chat/completions",
                json=payload,
                headers={"content-type": "application/json"},
            )
        if resp.status_code != 200:
            print(f"[VLM] non-200 from local model: {resp.status_code} {resp.text[:200]}")
            return None
        content = resp.json()["choices"][0]["message"]["content"]
    except Exception as e:  # network down, timeout, bad shape — all non-fatal
        print(f"[VLM] local model call failed ({type(e).__name__}): {e}")
        return None 

    data = _parse_json_blob(content)
    if not isinstance(data, dict):
        print("[VLM] could not parse JSON from model reply")
        return None

    doc_type = str(data.get("document_type", "other")).strip() or "other"
    fields = _sanitize_fields(data.get("fields", []))
    return doc_type, fields