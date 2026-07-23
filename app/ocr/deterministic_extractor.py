"""
deterministic_extractor.py
===========================

Local, dependency-free field extraction for immigration documents.
No LLM, no external API calls. Pure regex + label anchoring + checksum
validation (MRZ check digits for passports, Verhoeff for Aadhaar).

This is the "trust anchor" layer: for fields with a fixed, known format
(passport number, USCIS receipt number, A-number, category codes, dates)
a regex CANNOT invent a value that isn't in the text, and a checksum
CANNOT pass on a misread digit. That is exactly what you want feeding a
legal filing.

Public API
----------
    detect_document_type(text) -> str
    extract_fields(text, mrz_lines=None, doc_type_hint=None) -> ExtractionResult

`extract_fields` returns fields already in the shape your backend expects:

    {
        "field_name":       "passport_number",
        "extracted_value":  "L898902C3",
        "confidence_score": 99,      # int 0-100
        "needs_review":     False,   # your DB auto-confirms when >=90 and not needs_review
    }

So the Celery task can hand `result.fields` straight to your
POST /documents/:id/ocr-fields payload with no reshaping.

Confidence policy (deliberately conservative)
---------------------------------------------
    99  checksum-validated value (MRZ digit passes, Aadhaar Verhoeff passes)
    97  format matches AND a known-good anchor confirms it (valid receipt prefix)
    95  clean regex match + passed a sanity check (a real, plausible date)
    ~80 regex matched but something is soft (unknown prefix, ambiguous date)
    ~70 label-anchored free text (names, employer) — always needs_review

Anything below 90 (or flagged) comes back with needs_review=True, so a human
sees it before it touches a filing. Fields we can't find at all are simply
not emitted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field
from datetime import date, datetime, timezone
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# OUTPUT SHAPE
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Field:
    field_name: str
    extracted_value: str
    confidence_score: int
    needs_review: bool

    def as_dict(self) -> dict:
        return {
            "field_name": self.field_name,
            "extracted_value": self.extracted_value,
            "confidence_score": int(self.confidence_score),
            "needs_review": bool(self.needs_review),
        }


@dataclass
class ExtractionResult:
    document_type: str            # detected type, e.g. "i797" — compare to expected_doc_type
    fields: list[dict] = dc_field(default_factory=list)
    detection_confidence: int = 0  # how sure we are about document_type

    def field_dicts(self) -> list[dict]:
        return self.fields


def _mk(field_name: str, value: str, confidence: int, needs_review: bool | None = None) -> Field:
    """Build a Field, auto-deriving needs_review from confidence if not given."""
    value = (value or "").strip()
    if needs_review is None:
        needs_review = confidence < 90
    return Field(field_name, value, confidence, needs_review)


# ─────────────────────────────────────────────────────────────────────────────
# TEXT NORMALISATION
# PaddleOCR output is noisy: broken lines, doubled spaces, stray punctuation.
# We keep the original (for case-sensitive values like names) and an UPPER copy
# with collapsed whitespace (for matching keywords / patterns).
# ─────────────────────────────────────────────────────────────────────────────

def _normalise(text: str) -> tuple[str, str]:
    # Collapse whitespace ONCE, then derive the upper copy from the same string
    # so character offsets line up between the two (case-preserved + uppercase).
    collapsed = re.sub(r"[ \t]+", " ", text or "")
    collapsed = re.sub(r"\n{2,}", "\n", collapsed)
    return collapsed, collapsed.upper()


# ─────────────────────────────────────────────────────────────────────────────
# CHECKSUMS
# ─────────────────────────────────────────────────────────────────────────────

def mrz_check_digit(data: str) -> int:
    """ICAO 9303 check digit: weights 7,3,1 repeating; A=10..Z=35, '<'=0."""
    weights = (7, 3, 1)
    total = 0
    for i, ch in enumerate(data):
        if ch.isdigit():
            val = int(ch)
        elif "A" <= ch <= "Z":
            val = ord(ch) - 55          # A=10 ... Z=35
        else:                            # '<' or anything else
            val = 0
        total += val * weights[i % 3]
    return total % 10


# --- Verhoeff (used by India's Aadhaar) --------------------------------------
_V_D = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
    (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
    (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
    (4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
    (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
    (6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
    (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
    (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
    (9, 8, 7, 6, 5, 4, 3, 2, 1, 0),
)
_V_P = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
    (5, 8, 0, 9, 1, 6, 7, 3, 2, 4),
    (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
    (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
    (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
    (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
    (7, 0, 4, 6, 9, 1, 3, 2, 5, 8),
)


def verhoeff_valid(number: str) -> bool:
    digits = [int(d) for d in re.sub(r"\D", "", number)]
    c = 0
    for i, d in enumerate(reversed(digits)):
        c = _V_D[c][_V_P[i % 8][d]]
    return c == 0


# ─────────────────────────────────────────────────────────────────────────────
# DATE PARSING (dependency-free)
# Normalises to ISO YYYY-MM-DD. These are US docs, so numeric ambiguity
# (both parts <= 12) defaults to US MM/DD but is flagged ambiguous.
# ─────────────────────────────────────────────────────────────────────────────

_MONTHS = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
    "JANUARY": 1, "FEBRUARY": 2, "MARCH": 3, "APRIL": 4, "JUNE": 6,
    "JULY": 7, "AUGUST": 8, "SEPTEMBER": 9, "OCTOBER": 10,
    "NOVEMBER": 11, "DECEMBER": 12,
}


@dataclass
class ParsedDate:
    iso: str
    ambiguous: bool = False


def _valid_ymd(y: int, m: int, d: int) -> bool:
    try:
        date(y, m, d)
        return True
    except ValueError:
        return False


def parse_date(raw: str) -> Optional[ParsedDate]:
    """Parse a single date token. Returns None if it isn't a sane date."""
    if not raw:
        return None
    s = raw.strip().upper().replace(".", " ")

    # 1) Month-name forms: "January 15, 2024" / "15 JAN 2024" / "15-JAN-2024"
    m = re.search(r"([A-Z]{3,9})\s*[- ]?\s*(\d{1,2})\s*,?\s*(\d{4})", s)
    if m and m.group(1) in _MONTHS:
        mon, day, year = _MONTHS[m.group(1)], int(m.group(2)), int(m.group(3))
        if _valid_ymd(year, mon, day):
            return ParsedDate(f"{year:04d}-{mon:02d}-{day:02d}")
    m = re.search(r"(\d{1,2})\s*[- ]?\s*([A-Z]{3,9})\s*[- ]?\s*(\d{4})", s)
    if m and m.group(2) in _MONTHS:
        day, mon, year = int(m.group(1)), _MONTHS[m.group(2)], int(m.group(3))
        if _valid_ymd(year, mon, day):
            return ParsedDate(f"{year:04d}-{mon:02d}-{day:02d}")

    # 2) ISO: 2024-01-15
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if _valid_ymd(y, mo, d):
            return ParsedDate(f"{y:04d}-{mo:02d}-{d:02d}")

    # 3) Numeric with / or -  →  a/b/YYYY
    m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", s)
    if m:
        a, b, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        # Disambiguate a=month/b=day (US) vs a=day/b=month
        if a > 12 and b <= 12:                 # a must be day
            day, mon, ambig = a, b, False
        elif b > 12 and a <= 12:               # b must be day
            mon, day, ambig = a, b, False
        else:                                   # both <=12 → assume US MM/DD, flag it
            mon, day, ambig = a, b, True
        if _valid_ymd(year, mon, day):
            return ParsedDate(f"{year:04d}-{mon:02d}-{day:02d}", ambiguous=ambig)

    return None


def _date_field(name: str, raw: str, base_conf: int = 95) -> Optional[Field]:
    pd = parse_date(raw)
    if not pd:
        return None
    if pd.ambiguous:
        return _mk(name, pd.iso, 75, needs_review=True)
    return _mk(name, pd.iso, base_conf)


# ─────────────────────────────────────────────────────────────────────────────
# MRZ (passport TD3: two lines of 44 chars)
# ─────────────────────────────────────────────────────────────────────────────

# valid MRZ chars, used to sniff MRZ lines out of raw OCR text
_MRZ_LINE = re.compile(r"^[A-Z0-9<]{30,44}$")


def _find_mrz_lines(upper_text: str) -> Optional[tuple[str, str]]:
    """Best-effort: pull two consecutive MRZ-looking lines from OCR text."""
    candidates = []
    for ln in upper_text.splitlines():
        cleaned = re.sub(r"\s", "", ln)
        if _MRZ_LINE.match(cleaned):
            candidates.append(cleaned.ljust(44, "<")[:44])
    # a real passport MRZ: line 1 starts with 'P'
    for i in range(len(candidates) - 1):
        if candidates[i].startswith("P"):
            return candidates[i], candidates[i + 1]
    if len(candidates) >= 2:
        return candidates[0], candidates[1]
    return None


def _yy_to_year(yy: int, is_expiry: bool) -> int:
    """Expand 2-digit year. Expiry → 20xx. DOB → pivot on current year."""
    if is_expiry:
        return 2000 + yy
    cur2 = datetime.now(timezone.utc).year % 100
    return (2000 + yy) if yy <= cur2 else (1900 + yy)


def _mrz_date(yymmdd: str, is_expiry: bool) -> Optional[str]:
    if not re.fullmatch(r"\d{6}", yymmdd):
        return None
    yy, mm, dd = int(yymmdd[:2]), int(yymmdd[2:4]), int(yymmdd[4:6])
    year = _yy_to_year(yy, is_expiry)
    return f"{year:04d}-{mm:02d}-{dd:02d}" if _valid_ymd(year, mm, dd) else None


def parse_mrz(line1: str, line2: str) -> list[Field]:
    """Parse a TD3 MRZ. Each field's confidence keys off its check digit."""
    fields: list[Field] = []
    l1 = line1.ljust(44, "<")[:44]
    l2 = line2.ljust(44, "<")[:44]

    # --- names from line 1: P<ISO SURNAME<<GIVEN<NAMES ---
    m = re.match(r"^P[<A-Z]?([A-Z]{3})(.+)$", l1)
    if m:
        names = m.group(2)
        if "<<" in names:
            surname_raw, given_raw = names.split("<<", 1)
        else:
            surname_raw, given_raw = names, ""
        surname = surname_raw.replace("<", " ").strip()
        given = given_raw.replace("<", " ").strip()
        if surname:
            fields.append(_mk("surname", surname, 90))
        if given:
            fields.append(_mk("given_names", given, 90))

    # --- line 2 fixed offsets ---
    passport_no = l2[0:9].replace("<", "").strip()
    cd_passport = l2[9]
    nationality = l2[10:13].replace("<", "").strip()
    dob_raw = l2[13:19]
    cd_dob = l2[19]
    sex = l2[20]
    exp_raw = l2[21:27]
    cd_exp = l2[27]

    def _validated(name, value, data, expected_cd, formatter=lambda v: v):
        if not value:
            return
        ok = str(mrz_check_digit(data)) == str(expected_cd)
        conf = 99 if ok else 75
        fields.append(_mk(name, formatter(value), conf, needs_review=not ok))

    _validated("passport_number", passport_no, l2[0:9], cd_passport)

    if nationality:
        fields.append(_mk("nationality", nationality, 96))

    dob_iso = _mrz_date(dob_raw, is_expiry=False)
    if dob_iso:
        ok = str(mrz_check_digit(dob_raw)) == str(cd_dob)
        fields.append(_mk("date_of_birth", dob_iso, 99 if ok else 75, needs_review=not ok))

    if sex in ("M", "F"):
        fields.append(_mk("sex", sex, 97))

    exp_iso = _mrz_date(exp_raw, is_expiry=True)
    if exp_iso:
        ok = str(mrz_check_digit(exp_raw)) == str(cd_exp)
        fields.append(_mk("expiry_date", exp_iso, 99 if ok else 75, needs_review=not ok))

    return fields


# ─────────────────────────────────────────────────────────────────────────────
# SHARED PATTERNS
# ─────────────────────────────────────────────────────────────────────────────

# USCIS receipt / EAD card numbers: 3-letter service centre + 10 digits.
USCIS_PREFIXES = {"EAC", "WAC", "LIN", "SRC", "MSC", "IOE", "YSC", "NBC", "NSC", "VSC", "TSC"}
RECEIPT_RE = re.compile(r"\b([A-Z]{3})[- ]?(\d{10})\b")
A_NUMBER_RE = re.compile(r"\bA[-\s]?(\d{8,9})\b")
CATEGORY_RE = re.compile(r"\b([ABC]\d{2})\b")          # e.g. C09, A05, C08
I94_NUMBER_RE = re.compile(r"\b(\d{11})\b")
PAN_RE = re.compile(r"\b([A-Z]{5}\d{4}[A-Z])\b")
AADHAAR_RE = re.compile(r"\b(\d{4}\s?\d{4}\s?\d{4})\b")


def _first_receipt(upper: str) -> Optional[Field]:
    for pre, digits in RECEIPT_RE.findall(upper):
        if pre in USCIS_PREFIXES:
            return _mk("receipt_number", f"{pre}{digits}", 97)
    m = RECEIPT_RE.search(upper)               # matched format, unknown centre
    if m:
        return _mk("receipt_number", f"{m.group(1)}{m.group(2)}", 80, needs_review=True)
    return None


def _label_value(text: str, labels: list[str], stop: int = 60) -> Optional[str]:
    """
    Grab the text right after a label, on the same line.
    e.g. label 'PETITIONER' → returns what follows it, up to `stop` chars.

    Uses a case-insensitive regex capture on ONE string, so there are no
    offset problems and the returned value keeps its original casing.
    `(.+)` stops at the end of the line (no DOTALL), which is exactly where
    the value ends on these forms. Labels are tried in order — list the most
    specific first (e.g. "EMPLOYER BUSINESS NAME" before "EMPLOYER").
    """
    for label in labels:
        pattern = re.escape(label) + r"\s*[:.\-]?\s*(.+)"
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            value = m.group(1).splitlines()[0][:stop].strip(" :\t-").strip()
            if value:
                return value
    return None


# ─────────────────────────────────────────────────────────────────────────────
# PER-DOCUMENT EXTRACTORS
# Each returns a list[Field]. They deliberately over-extract candidates;
# the confidence policy decides what auto-confirms vs needs review.
# ─────────────────────────────────────────────────────────────────────────────

def extract_passport(original: str, upper: str, mrz_lines) -> list[Field]:
    fields: list[Field] = []
    lines = mrz_lines or _find_mrz_lines(upper)
    if lines:
        fields.extend(parse_mrz(lines[0], lines[1]))
    # visual-zone fallback only if MRZ gave nothing
    if not any(f.field_name == "passport_number" for f in fields):
        m = re.search(r"PASSPORT\s*(?:NO|NUMBER|#)?\s*[:.]?\s*([A-Z0-9]{6,9})", upper)
        if m:
            fields.append(_mk("passport_number", m.group(1), 70, needs_review=True))
    return fields


def extract_i797(original: str, upper: str, _mrz) -> list[Field]:
    fields: list[Field] = []
    r = _first_receipt(upper)
    if r:
        fields.append(r)

    for label, name in [("NOTICE DATE", "notice_date"),
                        ("RECEIVED DATE", "received_date")]:
        val = _label_value(original, [label], stop=30)
        if val and (f := _date_field(name, val)):
            fields.append(f)

    # "VALID FROM 01/15/2024 TO 01/14/2027"
    m = re.search(r"VALID\s+FROM\s+(.{6,20}?)\s+TO\s+(.{6,20})", upper)
    if m:
        if f := _date_field("valid_from", m.group(1)):
            fields.append(f)
        if f := _date_field("valid_to", m.group(2)):
            fields.append(f)

    for label, name, conf in [("PETITIONER", "petitioner", 70),
                              ("BENEFICIARY", "beneficiary", 70),
                              ("CASE TYPE", "case_type", 80),
                              ("NOTICE TYPE", "notice_type", 80)]:
        val = _label_value(original, [label])
        if val:
            fields.append(_mk(name, val, conf))
    return fields


def extract_i94(original: str, upper: str, _mrz) -> list[Field]:
    fields: list[Field] = []
    val = _label_value(original,
                       ["ADMISSION (I-94) RECORD NUMBER", "I-94 RECORD NUMBER",
                        "ADMISSION RECORD NUMBER", "RECORD NUMBER"], stop=20)
    num = None
    if val:
        mm = re.search(r"\d{11}", val)
        if mm:
            num = mm.group(0)
    if not num:
        mm = I94_NUMBER_RE.search(upper)
        num = mm.group(1) if mm else None
    if num:
        fields.append(_mk("i94_number", num, 92 if val else 80,
                          needs_review=not bool(val)))

    coa = _label_value(original, ["CLASS OF ADMISSION"], stop=15)
    if coa:
        fields.append(_mk("class_of_admission", coa, 88))

    admit = _label_value(original, ["ADMIT UNTIL DATE", "ADMIT UNTIL"], stop=20)
    if admit:
        if "D/S" in admit.upper():
            fields.append(_mk("admit_until", "D/S", 90))
        elif f := _date_field("admit_until", admit):
            fields.append(f)
    return fields


def extract_ead(original: str, upper: str, _mrz) -> list[Field]:
    fields: list[Field] = []
    m = A_NUMBER_RE.search(upper)
    if m:
        fields.append(_mk("uscis_number", f"A{m.group(1)}", 93))

    cat = None
    lbl = _label_value(original, ["CATEGORY"], stop=8)
    if lbl:
        cm = CATEGORY_RE.search(lbl.upper())
        if cm:
            cat = cm.group(1)
    if not cat:
        cm = CATEGORY_RE.search(upper)
        cat = cm.group(1) if cm else None
    if cat:
        fields.append(_mk("category_code", cat, 90 if lbl else 78,
                          needs_review=not bool(lbl)))

    for label, name in [("CARD EXPIRES", "card_expires"),
                        ("VALID FROM", "valid_from")]:
        val = _label_value(original, [label], stop=20)
        if val and (f := _date_field(name, val)):
            fields.append(f)

    # EAD carries a card number in receipt-number format too
    r = _first_receipt(upper)
    if r:
        r.field_name = "card_number"
        fields.append(r)
    return fields


def extract_lca(original: str, upper: str, _mrz) -> list[Field]:
    fields: list[Field] = []
    m = re.search(r"\b([IG]-\d{3}-\d{5}-\d{6})\b", upper)   # e.g. I-200-XXXXX-XXXXXX
    if m:
        fields.append(_mk("case_number", m.group(1), 95))

    emp = _label_value(original,
                       ["EMPLOYER BUSINESS NAME", "EMPLOYER NAME", "EMPLOYER"], stop=80)
    if emp:
        fields.append(_mk("employer_name", emp, 72))

    soc = _label_value(original, ["SOC CODE", "SOC/O*NET CODE"], stop=15)
    if soc:
        sm = re.search(r"\d{2}-?\d{4}", soc)
        if sm:
            fields.append(_mk("soc_code", sm.group(0), 88))

    wage = _label_value(original, ["WAGE RATE OF PAY FROM", "WAGE RATE", "WAGE"], stop=30)
    if wage:
        wm = re.search(r"[\d,]+(?:\.\d{2})?", wage)
        if wm:
            fields.append(_mk("wage_rate", wm.group(0), 80))
    return fields


def extract_india(original: str, upper: str, _mrz) -> list[Field]:
    fields: list[Field] = []

    # Aadhaar: 12 digits, Verhoeff-checked → high confidence when it passes
    for m in AADHAAR_RE.finditer(upper):
        digits = re.sub(r"\s", "", m.group(1))
        if len(digits) == 12:
            ok = verhoeff_valid(digits)
            pretty = f"{digits[0:4]} {digits[4:8]} {digits[8:12]}"
            fields.append(_mk("aadhaar_number", pretty, 99 if ok else 70,
                              needs_review=not ok))
            break

    pm = PAN_RE.search(upper)
    if pm:
        fields.append(_mk("pan_number", pm.group(1), 95))
    return fields


# ─────────────────────────────────────────────────────────────────────────────
# DOCUMENT TYPE DETECTION
# ─────────────────────────────────────────────────────────────────────────────

_SIGNATURES: dict[str, list[str]] = {
    "passport":  ["PASSPORT", "P<", "MRZ"],
    "i797":      ["I-797", "NOTICE OF ACTION", "RECEIPT NUMBER", "USCIS"],
    "i94":       ["I-94", "ARRIVAL/DEPARTURE", "ADMIT UNTIL", "CLASS OF ADMISSION"],
    "ead":       ["EMPLOYMENT AUTHORIZATION", "I-766", "CARD EXPIRES", "USCIS#"],
    "lca":       ["LABOR CONDITION APPLICATION", "ETA-9035", "ETA 9035",
                  "PREVAILING WAGE", "OCCUPATIONAL CLASSIFICATION"],
    "aadhaar":   ["AADHAAR", "UNIQUE IDENTIFICATION", "GOVERNMENT OF INDIA", "VID"],
    "pan":       ["INCOME TAX DEPARTMENT", "PERMANENT ACCOUNT NUMBER"],
}

_EXTRACTORS = {
    "passport": extract_passport,
    "i797":     extract_i797,
    "i94":      extract_i94,
    "ead":      extract_ead,
    "lca":      extract_lca,
    "aadhaar":  extract_india,
    "pan":      extract_india,
}


def detect_document_type(text: str) -> tuple[str, int]:
    """Return (doc_type, confidence 0-100). 'unknown' if nothing scores."""
    _, upper = _normalise(text)
    scores: dict[str, int] = {}
    for doc_type, sigs in _SIGNATURES.items():
        hits = sum(1 for s in sigs if s in upper)
        if hits:
            scores[doc_type] = hits
    # structural boosts
    if _find_mrz_lines(upper):
        scores["passport"] = scores.get("passport", 0) + 2
    if PAN_RE.search(upper):
        scores["pan"] = scores.get("pan", 0) + 1
    if not scores:
        return "unknown", 0
    best = max(scores, key=scores.get)
    conf = min(95, 55 + scores[best] * 12)
    return best, conf


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def extract_fields(
    text: str,
    mrz_lines: Optional[tuple[str, str]] = None,
    doc_type_hint: Optional[str] = None,
) -> ExtractionResult:
    """
    Main entry point for the microservice.

    Parameters
    ----------
    text          : full OCR text from PaddleOCR.
    mrz_lines     : optional (line1, line2) if passporteye already gave you the MRZ.
    doc_type_hint : optional expected_doc_type from your upload flow. Used to break
                    ties, never to override a confident detection (so you can still
                    catch the "user uploaded the wrong doc" case).

    Returns ExtractionResult with `.fields` as a list of dicts ready for
    POST /documents/:id/ocr-fields.
    """
    original, upper = _normalise(text)
    detected, det_conf = detect_document_type(text)

    # apply hint only if detection is weak/unknown
    doc_type = detected
    if doc_type == "unknown" and doc_type_hint:
        doc_type = doc_type_hint.lower().strip()
    elif doc_type_hint and doc_type_hint.lower().strip() == doc_type:
        det_conf = min(99, det_conf + 5)

    extractor = _EXTRACTORS.get(doc_type)
    fields: list[Field] = extractor(original, upper, mrz_lines) if extractor else []

    # de-dupe by field_name, keeping the highest-confidence hit
    best: dict[str, Field] = {}
    for f in fields:
        if f.field_name not in best or f.confidence_score > best[f.field_name].confidence_score:
            best[f.field_name] = f

    return ExtractionResult(
        document_type=doc_type,
        detection_confidence=det_conf,
        fields=[f.as_dict() for f in best.values()],
    )