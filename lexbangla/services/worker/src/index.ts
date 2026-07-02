import { Worker } from 'bullmq';
import type { OcrJobData, OcrJobResult } from '@lexbangla/core';
import { OCR_QUEUE_NAME } from '@lexbangla/core';
import { MinioStorageService, OcrService } from '@lexbangla/ocr';
import { config } from './config';
import { createDocumentProcessor } from './processors/document.processor';

async function main(): Promise<void> {
  const storage = new MinioStorageService(config.minio);
  const ocrService = new OcrService();

  const processor = createDocumentProcessor(storage, ocrService);

  const worker = new Worker<OcrJobData, OcrJobResult>(OCR_QUEUE_NAME, processor, {
    connection: config.redis,
    concurrency: config.worker.concurrency,
  });

  worker.on('active', (job) => {
    console.log(`[worker] Processing job ${job.id} — document: ${job.data.documentId}`);
  });

  worker.on('completed', (job) => {
    console.log(`[worker] Completed job ${job.id}`);
  });

  worker.on('failed', (job, err) => {
    console.error(`[worker] Failed job ${job?.id}: ${err.message}`);
  });

  console.log(
    `[worker] Listening on queue "${OCR_QUEUE_NAME}" ` +
      `(concurrency: ${config.worker.concurrency})`,
  );

  const shutdown = async (): Promise<void> => {
    await worker.close();
    process.exit(0);
  };

  process.on('SIGTERM', shutdown);
  process.on('SIGINT', shutdown);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
