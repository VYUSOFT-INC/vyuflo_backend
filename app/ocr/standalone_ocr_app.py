# app/ocr/standalone_ocr_app.py
#
# STANDALONE test harness. Runs ONLY the OCR router, by itself, so you can
# test /ocr/extract in isolation before wiring it into your real main.py.
# This is NOT your production app — it's a throwaway for local testing, and it
# imports nothing from the rest of your backend (no DB, no auth, no middleware).
#
# Run it from the backend/ project root:
#
#     uvicorn app.ocr.standalone_ocr_app:app --port 8002 --reload
#
# Then either:
#   • open http://localhost:8002/docs  and upload a file in the browser, or
#   • curl -X POST http://localhost:8002/ocr/extract -F "file=@/path/to/passport.jpg"
#
# When it all looks good, delete this file and add the router to your real
# main.py instead (one line — see the message).

from fastapi import FastAPI

from app.ocr.ocr_service_router import ocr_router

app = FastAPI(title="VisaFlow OCR — standalone test")
app.include_router(ocr_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "ocr-standalone"}