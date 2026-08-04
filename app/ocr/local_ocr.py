"""
local_ocr.py
============

The OCR half of the pipeline — turns an uploaded file (image or PDF) into
plain text, plus a checksum-validated passport MRZ when one is present.

Heavy libraries (paddleocr, passporteye) are imported *lazily* inside the
functions, so this module imports fine on a machine where they aren't
installed yet, and the PaddleOCR model is loaded only once per process.

Public API
----------
    run_ocr(content: bytes, ext: str) -> OCRText
    to_image_bytes(content: bytes, ext: str) -> tuple[bytes, str]   # for the VLM

`run_ocr` returns:
    .text             full concatenated OCR text (feed to extract_fields)
    .avg_confidence   mean PaddleOCR line confidence, 0-100 (a "is the scan
                      any good?" signal — low value is a reason to try the VLM)
    .passport_fields  list[field-dict] if passporteye read a passport MRZ,
                      else None. Already in your OCRField shape, so it can go
                      straight into the response.

Install on the server (once)
----------------------------
    pip install paddlepaddle==2.6.2 paddleocr==2.7.3 passporteye pymupdf
    # passporteye also needs the Tesseract binary:
    #   Ubuntu:  sudo apt-get install -y tesseract-ocr

If OCR ever SIGILLs inside the container, wipe the model cache and rebuild:
    docker compose exec backend rm -rf /root/.paddleocr
    docker compose up -d --build backend
"""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass
class OCRText:
    text: str
    avg_confidence: int
    passport_fields: Optional[list[dict]] = None


# ─────────────────────────────────────────────────────────────────────────────
# FILE → IMAGE PATHS  (PDF handled via PyMuPDF; images written to temp files
# so PaddleOCR + passporteye can both read a path uniformly)
# ─────────────────────────────────────────────────────────────────────────────

def _to_image_paths(content: bytes, ext: str) -> list[str]:
    ext = ext.lower().lstrip(".")
    paths: list[str] = []
    if ext == "pdf":
        import fitz  # type: ignore  # PyMuPDF (installed on the server, not the laptop)
        doc = fitz.open(stream=content, filetype="pdf")
        try:
            for page in doc:
                pix = page.get_pixmap(dpi=200)  # 200 DPI is plenty for OCR
                tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                pix.save(tmp.name)
                tmp.close()
                paths.append(tmp.name)
        finally:
            doc.close()
    else:
        suffix = ".jpg" if ext in ("jpg", "jpeg") else f".{ext}"
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        tmp.write(content)
        tmp.close()
        paths.append(tmp.name)
    return paths


def to_image_bytes(content: bytes, ext: str) -> tuple[bytes, str]:
    """
    Return the first page as image bytes + media type, for sending to the VLM.
    Images pass through unchanged; PDFs get their first page rendered to PNG.
    """
    ext = ext.lower().lstrip(".")
    if ext == "pdf":
        import fitz  # type: ignore  # PyMuPDF
        doc = fitz.open(stream=content, filetype="pdf")
        try:
            pix = doc[0].get_pixmap(dpi=200)
            return pix.tobytes("png"), "image/png"
        finally:
            doc.close()
    media = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
    return content, media


# ─────────────────────────────────────────────────────────────────────────────
# PADDLEOCR  (lazy singleton + version-tolerant result flattening)
# ─────────────────────────────────────────────────────────────────────────────

_engine = None

# Must be set before paddle / paddleocr are imported. oneDNN + SelfAttentionFusePass
# use AVX512 paths that SIGILL (and kill the whole uvicorn process) on many CPUs /
# Docker hosts. PIR executor flags similarly crash on ARM / older paddle builds.
def _configure_paddle_env() -> None:
    os.environ.setdefault("FLAGS_use_mkldnn", "0")
    os.environ.setdefault("FLAGS_enable_pir_api", "0")
    os.environ.setdefault("FLAGS_enable_pir_in_executor", "0")
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")


def _paddleocr_home() -> str:
    return os.path.expanduser(os.environ.get("PADDLEOCR_HOME", "~/.paddleocr"))


def _clear_corrupt_paddle_cache() -> None:
    """
    Incomplete downloads leave a dir without the .tar / inference files.
    PaddleOCR then raises FileNotFoundError, or loads a half-written model and
    dies with protobuf / SIGILL. Wipe the cache so the next init re-downloads.
    """
    import shutil

    home = _paddleocr_home()
    if os.path.isdir(home):
        shutil.rmtree(home, ignore_errors=True)


def _get_engine(*, _retried: bool = False):
    global _engine
    if _engine is not None:
        return _engine

    _configure_paddle_env()
    from paddleocr import PaddleOCR  # type: ignore

    # kwargs differ a lot across PaddleOCR versions (2.x vs 3.x), and newer
    # versions raise ValueError — not TypeError — on an unknown argument.
    # enable_mkldnn=False is required on CPU hosts without AVX512.
    last_err: Exception | None = None
    for kwargs in (
        {
            "use_angle_cls": True,
            "lang": "en",
            "use_gpu": False,
            "enable_mkldnn": False,
            "show_log": False,
        },
        {
            "use_angle_cls": True,
            "lang": "en",
            "use_gpu": False,
            "enable_mkldnn": False,
        },
        {"use_angle_cls": True, "lang": "en", "enable_mkldnn": False},
        {"lang": "en", "enable_mkldnn": False},
        {"lang": "en"},
        {},
    ):
        try:
            _engine = PaddleOCR(**kwargs)
            break
        except (TypeError, ValueError) as e:
            last_err = e
            continue
        except FileNotFoundError as e:
            # Mid-download / corrupt model cache — wipe once and retry.
            if not _retried:
                _engine = None
                _clear_corrupt_paddle_cache()
                return _get_engine(_retried=True)
            raise RuntimeError(
                f"PaddleOCR model cache is incomplete ({e}). "
                f"Delete {_paddleocr_home()} and retry."
            ) from e

    if _engine is None:
        raise RuntimeError(
            f"Could not initialise PaddleOCR with any known argument set: {last_err}"
        )
    return _engine


def _flatten(raw) -> tuple[list[str], list[float]]:
    """
    Walk PaddleOCR output and pull out (texts, scores), tolerant of the
    2.x list format  [[box, (text, score)], ...]  and the 3.x dict/predict
    format  {'rec_texts': [...], 'rec_scores': [...]}.
    """
    texts: list[str] = []
    scores: list[float] = []

    def walk(node):
        if node is None:
            return
        if isinstance(node, dict):
            if "rec_texts" in node:
                rt = node.get("rec_texts") or []
                rs = node.get("rec_scores") or []
                for i, t in enumerate(rt):
                    texts.append(str(t))
                    scores.append(float(rs[i]) if i < len(rs) else 0.0)
            return
        if isinstance(node, (list, tuple)):
            # a leaf detection: [box, (text, score)]
            if (
                len(node) == 2
                and isinstance(node[1], (list, tuple))
                and len(node[1]) == 2
                and isinstance(node[1][0], str)
            ):
                texts.append(node[1][0])
                try:
                    scores.append(float(node[1][1]))
                except (TypeError, ValueError):
                    scores.append(0.0)
            else:
                for x in node:
                    walk(x)

    walk(raw)
    return texts, scores


def _ocr_image(path: str) -> tuple[list[str], list[float]]:
    engine = _get_engine()
    try:
        raw = engine.ocr(path, cls=True)
    except (TypeError, ValueError):
        # 3.x dropped the `cls` argument — call without it
        raw = engine.ocr(path)
    return _flatten(raw)


# ─────────────────────────────────────────────────────────────────────────────
# PASSPORTEYE  (MRZ read → fields, using its built-in check-digit validation)
# ─────────────────────────────────────────────────────────────────────────────

def _yymmdd_to_iso(raw: Optional[str], is_expiry: bool) -> Optional[str]:
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if len(digits) != 6:
        return None
    yy, mm, dd = int(digits[:2]), int(digits[2:4]), int(digits[4:6])
    if is_expiry:
        year = 2000 + yy
    else:
        cur2 = datetime.now().year % 100
        year = (2000 + yy) if yy <= cur2 else (1900 + yy)
    try:
        date(year, mm, dd)
        return f"{year:04d}-{mm:02d}-{dd:02d}"
    except ValueError:
        return None


def _passport_fields_from_mrz(d: dict) -> list[dict]:
    """
    Convert a passporteye MRZ dict into field-dicts in the OCRField shape.
    Confidence keys off passporteye's own check-digit flags (valid_number,
    valid_date_of_birth, ...) — a failed check digit → needs_review.
    """
    out: list[dict] = []

    def add(name: str, value, conf: int, review: Optional[bool] = None):
        value = (str(value) if value is not None else "").strip()
        if not value or value == "<":
            return
        out.append({
            "field_name": name,
            "extracted_value": value,
            "confidence_score": int(conf),
            "needs_review": (conf < 90) if review is None else bool(review),
        })

    ok_num = bool(d.get("valid_number"))
    add("passport_number", d.get("number"), 99 if ok_num else 75, not ok_num)
    add("surname", d.get("surname"), 92)
    add("given_names", d.get("names"), 92)
    add("nationality", d.get("nationality"), 96)

    ok_dob = bool(d.get("valid_date_of_birth"))
    dob = _yymmdd_to_iso(d.get("date_of_birth"), is_expiry=False)
    if dob:
        add("date_of_birth", dob, 99 if ok_dob else 75, not ok_dob)

    sex = (d.get("sex") or "").upper()[:1]
    if sex in ("M", "F"):
        add("sex", sex, 97)

    ok_exp = bool(d.get("valid_expiration_date"))
    exp = _yymmdd_to_iso(d.get("expiration_date"), is_expiry=True)
    if exp:
        add("expiry_date", exp, 99 if ok_exp else 75, not ok_exp)

    return out


def _read_passport(path: str) -> Optional[list[dict]]:
    try:
        from passporteye import read_mrz  # type: ignore
    except ImportError:
        return None
    try:
        mrz = read_mrz(path)
    except Exception:
        return None
    if mrz is None:
        return None
    d = mrz.to_dict()
    # passporteye scores the read 0-100; below ~30 it's noise, not a passport
    if (d.get("valid_score") or 0) < 30:
        return None
    fields = _passport_fields_from_mrz(d)
    return fields or None


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def run_ocr(content: bytes, ext: str) -> OCRText:
    """
    OCR an uploaded file. Synchronous / CPU-bound — the FastAPI endpoint calls
    this via run_in_threadpool so it doesn't block the event loop.
    """
    paths = _to_image_paths(content, ext)
    try:
        all_text: list[str] = []
        all_scores: list[float] = []
        for p in paths:
            t, s = _ocr_image(p)
            all_text.extend(t)
            all_scores.extend(s)

        text = "\n".join(all_text)
        avg = round(sum(all_scores) / len(all_scores) * 100) if all_scores else 0

        # Only the first page is checked for a passport MRZ (that's where it is)
        passport_fields = _read_passport(paths[0]) if paths else None

        return OCRText(text=text, avg_confidence=avg, passport_fields=passport_fields)
    finally:
        for p in paths:
            try:
                os.remove(p)
            except OSError:
                pass