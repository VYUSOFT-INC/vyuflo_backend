#!/usr/bin/env python3
"""
verify_local_ocr.py
===================

Smoke-test the local OCR pipeline on a real document, WITHOUT the web server.
Run this on the box after installing the deps to confirm PaddleOCR +
passporteye + the extractor all work together on your actual scans.

Run from the backend/ project root (so the `app.ocr.*` imports resolve):

    python -m app.ocr.verify_local_ocr path/to/passport.jpg
    python -m app.ocr.verify_local_ocr path/to/i797.pdf

If the extracted fields look right here, the /ocr/extract endpoint will too —
it runs this exact pipeline.
"""

import sys


def _check_deps() -> bool:
    missing = []
    for mod, pkg in [("fitz", "pymupdf"), ("paddleocr", "paddleocr")]:
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    try:
        __import__("passporteye")
    except ImportError:
        print("NOTE: passporteye not installed — passport MRZ reading will be "
              "skipped (everything else still works).\n")
    if missing:
        print("Missing required packages:", " ".join(missing))
        print("Install with:")
        print("    pip install paddlepaddle paddleocr passporteye pymupdf")
        print("passporteye also needs Tesseract:")
        print("    sudo apt-get install -y tesseract-ocr")
        return False
    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python verify_local_ocr.py <file.jpg|.png|.pdf>")
        return
    if not _check_deps():
        return

    path = sys.argv[1]
    ext = path.rsplit(".", 1)[-1].lower()
    with open(path, "rb") as fh:
        content = fh.read()

    from app.ocr.local_ocr import run_ocr
    from app.ocr.deterministic_extractor import extract_fields

    print(f"OCR-ing {path} ...\n")
    ocr = run_ocr(content, ext)

    print(f"  avg OCR confidence : {ocr.avg_confidence}/100")
    print(f"  text length        : {len(ocr.text)} chars")
    print("  --- first 400 chars of raw OCR text ---")
    preview = ocr.text[:400].replace("\n", "\n  ")
    print("  " + preview + "\n")

    if ocr.passport_fields:
        print("  PASSPORT MRZ (via passporteye, check-digit validated):")
        for f in ocr.passport_fields:
            flag = "  <-- REVIEW" if f["needs_review"] else ""
            print(f"    {f['field_name']:18} = {f['extracted_value']:26} "
                  f"conf={f['confidence_score']}{flag}")
        return

    result = extract_fields(ocr.text)
    print(f"  detected type : {result.document_type} "
          f"(detection conf {result.detection_confidence})")
    print("  extracted fields:")
    if not result.fields:
        print("    (none — likely a fuzzy doc type; the endpoint would send "
              "this to the VLM if VLM_ENABLED=true)")
    for f in result.fields:
        flag = "  <-- REVIEW" if f["needs_review"] else ""
        print(f"    {f['field_name']:18} = {f['extracted_value']:26} "
              f"conf={f['confidence_score']}{flag}")


if __name__ == "__main__":
    main()