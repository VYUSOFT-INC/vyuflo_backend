# ocr_service/router.py

import base64
import uuid
import httpx
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from pydantic import BaseModel
import os
from dotenv import load_dotenv

from app.core.dependencies import get_current_user

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    raise RuntimeError("ANTHROPIC_API_KEY not set in .env file")


ocr_router = APIRouter()

CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL   = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """
You are a document OCR extractor for an immigration application platform.

Extract ALL relevant fields from the document image.
Return ONLY a JSON object — no explanation, no markdown, no backticks.

Format:
{
  "document_type": "passport | aadhaar | pan_card | i797 | i94 | ead_card | green_card | offer_letter | salary_slip | w2 | form_16 | degree | other",
  "fields": [
    {
      "field_name": "Passport Number",
      "extracted_value": "X11000344",
      "confidence_score": 99,
      "needs_review": false
    }
  ]
}

Rules:
- confidence_score: 99 if clearly readable, 85 if slightly unclear, 70 if guessed, 50 if uncertain
- needs_review: true if confidence_score < 80
- Extract every field visible — name, dates, numbers, codes, addresses, amounts
- For passports always extract MRZ fields: passport number, surname, given names, nationality, DOB, sex, expiry
- For salary documents extract: gross pay, net pay, deductions, pay period, employer name
- For offer letters extract: job title, salary/CTC, start date, employer, location
- For Indian documents: handle both English and transliterated fields
- If a field is partially visible or unclear, still extract it and set needs_review: true
"""


class OCRField(BaseModel):
    field_name:       str
    extracted_value:  str
    confidence_score: int
    needs_review:     bool


class OCRResponse(BaseModel):
    filename:      str
    document_type: str
    fields:        list[OCRField]


# ocr_router.py
import asyncio
import httpx
import base64
from fastapi import APIRouter, File, UploadFile, HTTPException

MAX_RETRIES = 3
RETRY_DELAYS = [2, 5, 10]  # seconds between retries

@ocr_router.post("/ocr/extract", response_model=OCRResponse)
async def extract_ocr(
    file: UploadFile = File(...),
) -> OCRResponse:
    filename = file.filename or "upload"
    ext      = filename.rsplit(".", 1)[-1].lower()
    if ext not in ("jpg", "jpeg", "png", "pdf"):
        raise HTTPException(400, "Use JPG, PNG or PDF.")

    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(400, "Max 20MB.")

    b64_image  = base64.standard_b64encode(content).decode("utf-8")
    media_type = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"

    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": 1500,
        "system": SYSTEM_PROMPT,
        "messages": [{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type":       "base64",
                        "media_type": media_type,
                        "data":       b64_image,
                    },
                },
                {
                    "type": "text",
                    "text": "Extract all fields from this immigration document.",
                },
            ],
        }],
    }

    last_error = None

    async with httpx.AsyncClient(timeout=60.0) as client:
        for attempt in range(MAX_RETRIES):
            try:
                response = await client.post(
                    CLAUDE_API_URL,
                    headers={
                        "x-api-key":          ANTHROPIC_API_KEY,
                        "anthropic-version":  "2023-06-01",
                        "content-type":       "application/json",
                    },
                    json=payload,
                )

                # Overloaded — wait and retry
                if response.status_code == 529 or (
                    response.status_code == 200
                    and "overloaded_error" in response.text
                ):
                    wait = RETRY_DELAYS[attempt]
                    print(f"[OCR] Claude overloaded, retrying in {wait}s (attempt {attempt + 1}/{MAX_RETRIES})")
                    await asyncio.sleep(wait)
                    last_error = "Claude API overloaded"
                    continue

                if response.status_code != 200:
                    raise HTTPException(500, f"Claude API error: {response.text}")

                # Parse response
                import json
                raw_text = response.json()["content"][0]["text"]
                try:
                    data = json.loads(raw_text)
                except json.JSONDecodeError:
                    clean = raw_text.strip().removeprefix("```json").removesuffix("```").strip()
                    data  = json.loads(clean)

                return OCRResponse(
                    filename      = filename,
                    document_type = data.get("document_type", "unknown"),
                    fields        = [OCRField(**f) for f in data.get("fields", [])],
                )

            except httpx.TimeoutException:
                wait = RETRY_DELAYS[attempt]
                print(f"[OCR] Timeout, retrying in {wait}s (attempt {attempt + 1}/{MAX_RETRIES})")
                await asyncio.sleep(wait)
                last_error = "Claude API timeout"
                continue

    # All retries exhausted
    raise HTTPException(503, f"OCR service unavailable after {MAX_RETRIES} attempts: {last_error}")