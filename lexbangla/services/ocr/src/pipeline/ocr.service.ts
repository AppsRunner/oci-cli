import pdfParse from 'pdf-parse';
import { createWorker } from 'tesseract.js';

export interface OcrResult {
  text: string;
  pageCount: number;
  language: string;
}

// Minimum character count to consider a PDF as text-bearing (not image-only).
const MIN_TEXT_LENGTH = 100;

export class OcrService {
  async processBuffer(buffer: Buffer, mimeType: string, language = 'ben+eng'): Promise<OcrResult> {
    if (mimeType === 'application/pdf') {
      return this.processPdf(buffer, language);
    }
    return this.processImage(buffer, language);
  }

  private async processPdf(buffer: Buffer, language: string): Promise<OcrResult> {
    const parsed = await pdfParse(buffer);
    const text = parsed.text.trim();

    // Searchable PDF: return embedded text directly.
    if (text.length >= MIN_TEXT_LENGTH) {
      return { text, pageCount: parsed.numpages, language };
    }

    // Image-based PDF: fall back to Tesseract OCR.
    const ocrText = await this.runTesseract(buffer, language);
    return { text: ocrText, pageCount: parsed.numpages, language };
  }

  private async processImage(buffer: Buffer, language: string): Promise<OcrResult> {
    const text = await this.runTesseract(buffer, language);
    return { text, pageCount: 1, language };
  }

  private async runTesseract(buffer: Buffer, language: string): Promise<string> {
    // Tesseract supports Bengali ('ben') and English ('eng').
    // Use combined 'ben+eng' for mixed-script documents.
    const worker = await createWorker(language);
    try {
      const { data } = await worker.recognize(buffer);
      return data.text.trim();
    } finally {
      await worker.terminate();
    }
  }
}
