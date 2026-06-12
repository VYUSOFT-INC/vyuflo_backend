// // src/hooks/useOCR.ts

// import { useState, useCallback } from "react";
// import ocrApi from "../api/ocr.api";
// import type { OCRField } from "../types/ocr.types";

// const OCR_BASE = import.meta.env.VITE_API_BASE_URL;

// // ── Map DB field → local OCRField (adds UI-only fields) ───────────────────────
// function mapSavedField(f: {
//   id: string;
//   field_name: string;
//   extracted_value: string | null;
//   confidence_score: number | null;
//   needs_review: boolean;
//   is_confirmed: boolean;
// }): OCRField {
//   return {
//     id:               f.id,
//     field_name:       f.field_name,
//     extracted_value:  f.extracted_value ?? "",
//     confidence_score: f.confidence_score ?? 0,
//     needs_review:     f.needs_review,
//     is_confirmed:     f.is_confirmed,
//     is_editing:       false,
//     edit_value:       f.extracted_value ?? "",
//   };
// }

// function calcAvg(fields: OCRField[]): number {
//   if (!fields.length) return 0;
//   return Math.round(fields.reduce((s, f) => s + f.confidence_score, 0) / fields.length);
// }

// // ─────────────────────────────────────────────────────────────────────────────
// export function useOCR(documentId: string | undefined) {
//   const [fields,        setFields]      = useState<OCRField[]>([]);
//   const [avgConfidence, setAvgConf]     = useState(0);
//   const [isLoading,     setIsLoading]   = useState(false);
//   const [error,         setError]       = useState<string | null>(null);
//   const [source,        setSource]      = useState<"db" | "ocr" | null>(null);

//   // ── Main load function — called once file blob is ready ───────────────────
//   const loadFields = useCallback(async (blob: Blob, fileName: string) => {
//     if (!documentId) return;
//     setIsLoading(true);
//     setError(null);

//     try {
//       // ── Step 1: Check DB first ────────────────────────────────────────────
//       const saved = await ocrApi.getFields(documentId);

//       if (saved.length > 0) {
//         // ✅ Already extracted — load from DB instantly, never call OCR
//         const mapped = saved.map(mapSavedField);
//         setFields(mapped);
//         setAvgConf(calcAvg(mapped));
//         setSource("db");
//         setIsLoading(false);
//         return;
//       }

//       // ── Step 2: No DB fields — call OCR service (port 8002) ──────────────
//       const safeName = fileName && /\.(jpg|jpeg|png|pdf)$/i.test(fileName)
//         ? fileName
//         : `document_${Date.now()}.jpg`;

//       const form = new FormData();
//       form.append("file", blob, safeName);

//       const res = await fetch(`${OCR_BASE}/ocr/extract`, {
//         method: "POST",
//         body:   form,
//       });

//       if (!res.ok) {
//         const text = await res.text();
//         throw new Error(`OCR service error ${res.status}: ${text}`);
//       }

//       const data = await res.json() as {
//         document_type: string;
//         fields: { field_name: string; extracted_value: string; confidence_score: number; needs_review: boolean }[];
//       };

//       const mapped: OCRField[] = data.fields.map((f, i) => ({
//         id:               `f-${i}`,         // temporary local ID until saved to DB
//         field_name:       f.field_name,
//         extracted_value:  f.extracted_value,
//         confidence_score: f.confidence_score,
//         needs_review:     f.needs_review,
//         is_confirmed:     f.confidence_score >= 90 && !f.needs_review,
//         is_editing:       false,
//         edit_value:       f.extracted_value,
//       }));

//       setFields(mapped);
//       setAvgConf(calcAvg(mapped));
//       setSource("ocr");

//       // ── Step 3: Save to DB — so next open loads from DB ──────────────────
//       try {
//         const saved2 = await ocrApi.saveFields(documentId, {
//           fields: mapped.map(f => ({
//             field_name:       f.field_name,
//             extracted_value:  f.extracted_value,
//             confidence_score: f.confidence_score,
//             needs_review:     f.needs_review,
//           })),
//         });
//         // Update IDs to real DB UUIDs
//         if (saved2.length === mapped.length) {
//           setFields(saved2.map(mapSavedField));
//         }
//       } catch (saveErr) {
//         // Non-fatal — fields shown in UI even if save to DB fails
//         console.warn("[useOCR] Failed to save fields to DB:", saveErr);
//       }

//     } catch (e) {
//       setError(e instanceof Error ? e.message : "OCR extraction failed.");
//     } finally {
//       setIsLoading(false);
//     }
//   }, [documentId]);

//   // ── Approve All — saves to DB, updates document status ───────────────────
//   const confirmAll = useCallback(async () => {
//     // 1. Update local state immediately
//     setFields(prev => prev.map(f => ({
//       ...f, is_confirmed: true, needs_review: false, is_editing: false,
//     })));

//     // 2. Save to backend
//     if (documentId) {
//       try {
//         await ocrApi.confirmAll(documentId);
//       } catch (e) {
//         console.warn("[useOCR] confirmAll backend call failed:", e);
//       }
//     }
//   }, [documentId]);

//   // ── Confirm single field — saves edit to DB ───────────────────────────────
//   const confirmField = useCallback(async (id: string) => {
//     const field = fields.find(f => f.id === id);
//     if (!field) return;

//     // Update local state immediately
//     setFields(prev => prev.map(f =>
//       f.id === id ? { ...f, is_confirmed: true, needs_review: false, is_editing: false } : f
//     ));

//     // Save to backend — only if ID is a real UUID (not local "f-0")
//     if (documentId && !id.startsWith("f-")) {
//       try {
//         await ocrApi.updateField(documentId, id, field.edit_value || field.extracted_value, true);
//       } catch (e) {
//         console.warn("[useOCR] confirmField backend call failed:", e);
//       }
//     }
//   }, [documentId, fields]);

//   // ── Save edited field ─────────────────────────────────────────────────────
//   const saveEdit = useCallback(async (id: string) => {
//     const field = fields.find(f => f.id === id);
//     if (!field) return;

//     // Update local state immediately
//     setFields(prev => prev.map(f =>
//       f.id === id
//         ? { ...f, is_editing: false, extracted_value: f.edit_value, needs_review: false }
//         : f
//     ));

//     // Save to backend if real UUID
//     if (documentId && !id.startsWith("f-")) {
//       try {
//         await ocrApi.updateField(documentId, id, field.edit_value, false);
//       } catch (e) {
//         console.warn("[useOCR] saveEdit backend call failed:", e);
//       }
//     }
//   }, [documentId, fields]);

//   // ── Local UI actions (no backend call) ───────────────────────────────────
//   const startEdit = useCallback((id: string) => {
//     setFields(prev => prev.map(f =>
//       f.id === id ? { ...f, is_editing: true, edit_value: f.extracted_value } : f
//     ));
//   }, []);

//   const cancelEdit = useCallback((id: string) => {
//     setFields(prev => prev.map(f =>
//       f.id === id ? { ...f, is_editing: false } : f
//     ));
//   }, []);

//   const updateEditValue = useCallback((id: string, value: string) => {
//     setFields(prev => prev.map(f =>
//       f.id === id ? { ...f, edit_value: value } : f
//     ));
//   }, []);

//   return {
//     fields,
//     avgConfidence,
//     isLoading,
//     error,
//     source,             // "db" | "ocr" | null — for debugging
//     loadFields,         // call when blob is ready
//     confirmAll,
//     confirmField,
//     saveEdit,
//     startEdit,
//     cancelEdit,
//     updateEditValue,
//     setError,
//   };
// }

// src/hooks/useOCR.ts

import { useState, useCallback } from "react";
import ocrApi from "../../api/employee/ocr.api";
import type { OCRField } from "../../types/employee/ocr.types";

//const OCR_BASE = import.meta.env.VITE_API_BASE_URL;

// ── Map DB field → local OCRField (adds UI-only fields) ──────────────────────
function mapSavedField(f: {
  id: string;
  field_name: string;
  extracted_value: string | null;
  confidence_score: number | null;
  needs_review: boolean;
  is_confirmed: boolean;
}): OCRField {
  return {
    id:               f.id,
    field_name:       f.field_name,
    extracted_value:  f.extracted_value ?? "",
    confidence_score: f.confidence_score ?? 0,
    needs_review:     f.needs_review,
    is_confirmed:     f.is_confirmed,
    is_editing:       false,
    edit_value:       f.extracted_value ?? "",
  };
}

function calcAvg(fields: OCRField[]): number {
  if (!fields.length) return 0;
  return Math.round(fields.reduce((s, f) => s + f.confidence_score, 0) / fields.length);
}

// ─────────────────────────────────────────────────────────────────────────────
export function useOCR(documentId: string | undefined) {
  const [fields,        setFields]  = useState<OCRField[]>([]);
  const [avgConfidence, setAvgConf] = useState(0);
  const [isLoading,     setIsLoading] = useState(false);
  const [error,         setError]   = useState<string | null>(null);
  const [source,        setSource]  = useState<"db" | "ocr" | null>(null);

  // ── Main load function — called once file blob is ready ───────────────────
  const loadFields = useCallback(async (blob: Blob, fileName: string) => {
    if (!documentId) return;
    setIsLoading(true);
    setError(null);

    try {
      // ── Step 1: Check DB first ────────────────────────────────────────────
      const saved = await ocrApi.getFields(documentId);

      if (saved.length > 0) {
        // ✅ Already extracted — load from DB instantly, never call OCR
        const mapped = saved.map(mapSavedField);
        setFields(mapped);
        setAvgConf(calcAvg(mapped));
        setSource("db");
        setIsLoading(false);
        return;
      }

      // ── Step 2: No DB fields — call OCR service ───────────────────────────
      const safeName = fileName && /\.(jpg|jpeg|png|pdf)$/i.test(fileName)
        ? fileName
        : `document_${Date.now()}.jpg`;

      const form = new FormData();
      form.append("file", blob, safeName);

      // ✅ Correct (relative path → goes through Vite proxy)
       const res = await fetch('/api/v1/ocr/extract', {
        method: 'POST',
        body: form,
         });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`OCR service error ${res.status}: ${text}`);
      }

      const data = await res.json() as {
        document_type: string;
        fields: { field_name: string; extracted_value: string; confidence_score: number; needs_review: boolean }[];
      };

      const mapped: OCRField[] = data.fields.map((f, i) => ({
        id:               `f-${i}`,   // temporary local ID until saved to DB
        field_name:       f.field_name,
        extracted_value:  f.extracted_value,
        confidence_score: f.confidence_score,
        needs_review:     f.needs_review,
        is_confirmed:     false,
        is_editing:       false,
        edit_value:       f.extracted_value,
      }));

      setFields(mapped);
      setAvgConf(calcAvg(mapped));
      setSource("ocr");

    } catch (e) {
      setError(e instanceof Error ? e.message : "OCR extraction failed.");
    } finally {
      setIsLoading(false);
    }
  }, [documentId]);

  // ── Submit / Update — single call to POST /ocr-fields/save ───────────────
  // Works for both flows:
  //   source="ocr"  → no existing fields in DB → backend INSERTs all
  //   source="db"   → fields exist in DB       → backend UPDATEs by field id
  const submitFields = useCallback(async () => {
    if (!documentId || !fields.length) return;

    const snapshot = fields; // capture current state

    // 1. Optimistic UI update
    setFields(prev => prev.map(f => ({
      ...f, is_confirmed: true, needs_review: false, is_editing: false,
    })));

    // 2. One API call — backend decides insert vs update
    try {
      const saved = await ocrApi.saveFields(documentId, {
        fields: snapshot.map(f => ({
          id:               f.id.startsWith("f-") ? undefined : f.id,  // omit temp IDs
          field_name:       f.field_name,
          extracted_value:  f.edit_value || f.extracted_value,          // use edited value
          confidence_score: f.confidence_score,
          needs_review:     false,
        })),
      });

      // Update local fields with real DB UUIDs (important after first insert)
      if (saved.length === snapshot.length) {
        setFields(saved.map(mapSavedField).map(f => ({
          ...f, is_confirmed: true, needs_review: false,
        })));
        setAvgConf(calcAvg(saved.map(mapSavedField)));
      }
    } catch (e) {
      console.warn("[useOCR] submitFields failed:", e);
    }
  }, [documentId, fields]);

  // ── Confirm single field — local state only (no separate API call) ────────
  const confirmField = useCallback((id: string) => {
    setFields(prev => prev.map(f =>
      f.id === id ? { ...f, is_confirmed: true, needs_review: false, is_editing: false } : f
    ));
  }, []);

  // ── Save edited field — local state only ─────────────────────────────────
  const saveEdit = useCallback((id: string) => {
    setFields(prev => prev.map(f =>
      f.id === id
        ? { ...f, is_editing: false, extracted_value: f.edit_value, needs_review: false }
        : f
    ));
  }, []);

  // ── Local UI actions (no backend call) ───────────────────────────────────
  const startEdit = useCallback((id: string) => {
    setFields(prev => prev.map(f =>
      f.id === id ? { ...f, is_editing: true, edit_value: f.extracted_value } : f
    ));
  }, []);

  const cancelEdit = useCallback((id: string) => {
    setFields(prev => prev.map(f =>
      f.id === id ? { ...f, is_editing: false } : f
    ));
  }, []);

  const updateEditValue = useCallback((id: string, value: string) => {
    setFields(prev => prev.map(f =>
      f.id === id ? { ...f, edit_value: value } : f
    ));
  }, []);

  return {
    fields,
    avgConfidence,
    isLoading,
    error,
    source,           // "db" | "ocr" | null
    loadFields,       // call when blob is ready
    submitFields,     // Submit (first open) or Update (re-open) — one function, one API
    confirmField,     // local state toggle only
    saveEdit,         // local state only — persisted on submitFields
    startEdit,
    cancelEdit,
    updateEditValue,
    setError,
  };
}