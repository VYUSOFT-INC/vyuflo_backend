// // src/types/ocr.types.ts
// // Types for OCR fields — used by DocumentViewer and useOCR hook

// export interface OCRField {
//   id:               string;       // UUID from DB, or "f-0" local before save
//   field_name:       string;       // e.g. "Passport Number"
//   extracted_value:  string;       // e.g. "X11000344"
//   confidence_score: number;       // 0-100
//   needs_review:     boolean;      // true when confidence < 80
//   is_confirmed:     boolean;      // user confirmed this field
//   is_editing:       boolean;      // currently being edited (local UI state)
//   edit_value:       string;       // value in the edit input
// }

// // Shape returned by GET /documents/:id/ocr-fields
// export interface SavedOCRField {
//   id:               string;
//   document_id:      string;
//   field_name:       string;
//   extracted_value:  string | null;
//   confidence_score: number | null;
//   needs_review:     boolean;
//   is_confirmed:     boolean;
//   confirmed_at?:    string | null;
// }

// // Shape for POST /documents/:id/ocr-fields body
// export interface SaveOCRFieldsPayload {
//   fields: {
//     field_name:       string;
//     extracted_value:  string;
//     confidence_score: number;
//     needs_review:     boolean;
//   }[];
// }

// src/types/ocr.types.ts

export interface OCRField {
  id:               string;       // UUID from DB, or "f-0" local before save
  field_name:       string;
  extracted_value:  string;
  confidence_score: number;       // 0–100
  needs_review:     boolean;
  is_confirmed:     boolean;
  is_editing:       boolean;      // UI only
  edit_value:       string;       // value in the edit input
}

// Shape returned by GET /documents/:id/ocr-fields
export interface SavedOCRField {
  id:               string;
  document_id:      string;
  field_name:       string;
  extracted_value:  string | null;
  confidence_score: number | null;
  needs_review:     boolean;
  is_confirmed:     boolean;
  confirmed_at?:    string | null;
}

// Shape for POST /documents/:id/ocr-fields/save
// id is optional — omitted on first insert, sent on update
export interface SaveOCRFieldsPayload {
  fields: {
    id?:              string;     // ← present on re-open (real UUID), absent on first save
    field_name:       string;
    extracted_value:  string;
    confidence_score: number;
    needs_review:     boolean;
  }[];
}