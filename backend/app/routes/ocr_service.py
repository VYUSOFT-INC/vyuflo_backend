# ocr_service/router.py

import base64
import httpx
from fastapi import APIRouter, File, UploadFile, HTTPException
from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    raise RuntimeError("ANTHROPIC_API_KEY not set in .env file")


ocr_router = APIRouter()

CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL   = "claude-opus-4-5"

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

    # Encode image to base64
    b64_image  = base64.standard_b64encode(content).decode("utf-8")
    media_type = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"

    # Call Claude API
    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": 1500,
        "system": SYSTEM_PROMPT,
        "messages": [
            {
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
            }
        ],
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            CLAUDE_API_URL,
            headers={
                "x-api-key":  ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type":      "application/json",
            },
            json=payload,
        )

    if response.status_code != 200:
        raise HTTPException(500, f"Claude API error: {response.text}")

    # Parse response
    import json
    raw_text = response.json()["content"][0]["text"]

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        # Strip markdown if Claude wrapped in backticks
        clean = raw_text.strip().removeprefix("```json").removesuffix("```").strip()
        data  = json.loads(clean)

    return OCRResponse(
        filename      = filename,
        document_type = data.get("document_type", "unknown"),
        fields        = [OCRField(**f) for f in data.get("fields", [])],
    )