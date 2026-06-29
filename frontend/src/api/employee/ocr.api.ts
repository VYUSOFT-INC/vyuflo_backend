
// src/api/ocr.api.ts
 
import axios from "../axios";
import type { SavedOCRField, SaveOCRFieldsPayload } from "../../types/employee/ocr.types";
 
const ocrApi = {
 
  // ── GET /documents/:id/ocr-fields ────────────────────────────────────────
  // Called first when Document Viewer opens.
  // Returns [] if OCR has not run yet → frontend calls OCR service.
  // Returns fields if already extracted → load instantly, skip OCR service.
  getFields: async (documentId: string): Promise<SavedOCRField[]> => {
    const res = await axios.get(`/documents/${documentId}/ocr-fields`);
    return Array.isArray(res.data) ? res.data : [];
  },
 
  // ── POST /documents/:id/ocr-fields/save ──────────────────────────────────
  // Smart upsert — one endpoint for both flows:
  //   No existing DB fields → INSERT (first open after OCR)
  //   Existing DB fields    → UPDATE by field id (re-open / user edits)
  // Always confirms all fields and sets document status = "verified".
  saveFields: async (
    documentId: string,
    payload:    SaveOCRFieldsPayload,
  ): Promise<SavedOCRField[]> => {
    const res = await axios.post(`/documents/${documentId}/ocr-fields/save`, payload);
    return Array.isArray(res.data) ? res.data : [];
  },
 
};
 
export default ocrApi;