export const OCR_QUEUE_NAME = 'document:ocr' as const;

export interface OcrJobData {
  documentId: string;
  originalName: string;
  filename: string;
  mimeType: string;
  sizeBytes: number;
  storageKey: string;
  storageBucket: string;
  language: string;
}

export interface OcrJobResult {
  documentId: string;
  extractedText: string;
  pageCount: number;
}
