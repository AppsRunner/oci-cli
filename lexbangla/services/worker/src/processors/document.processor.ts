import type { Job } from 'bullmq';
import type { OcrJobData, OcrJobResult } from '@lexbangla/core';
import type { MinioStorageService, OcrService } from '@lexbangla/ocr';

export function createDocumentProcessor(storage: MinioStorageService, ocrService: OcrService) {
  return async function processDocument(job: Job<OcrJobData>): Promise<OcrJobResult> {
    const { documentId, originalName, storageKey, storageBucket, mimeType, language } = job.data;

    console.log(`[processor] Starting OCR for document ${documentId} (${originalName})`);
    await job.updateProgress(10);

    const buffer = await storage.getObject(storageBucket, storageKey);
    await job.updateProgress(40);

    const result = await ocrService.processBuffer(buffer, mimeType, language);
    await job.updateProgress(90);

    console.log(
      `[processor] OCR done for ${documentId}: ${result.pageCount} page(s), ` +
        `${result.text.length} chars extracted`,
    );

    return {
      documentId,
      extractedText: result.text,
      pageCount: result.pageCount,
    };
  };
}
