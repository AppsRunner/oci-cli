import Fastify from 'fastify';
import multipart from '@fastify/multipart';
import { Queue, QueueEvents } from 'bullmq';
import type { OcrJobData, OcrJobResult } from '@lexbangla/core';
import { OCR_QUEUE_NAME, DocumentStatus } from '@lexbangla/core';
import { MinioStorageService } from '@lexbangla/ocr';
import { config } from './config';
import { InMemoryDocumentStore } from './store/document.store';
import { documentsRoute } from './routes/documents.route';

async function main(): Promise<void> {
  const fastify = Fastify({ logger: { level: 'info' } });

  await fastify.register(multipart, {
    limits: { fileSize: 50 * 1024 * 1024 }, // 50 MB
  });

  const storage = new MinioStorageService(config.minio);
  await storage.ensureBucket(config.minioBucket);

  const store = new InMemoryDocumentStore();

  const ocrQueue = new Queue<OcrJobData>(OCR_QUEUE_NAME, {
    connection: config.redis,
    defaultJobOptions: { removeOnComplete: 100, removeOnFail: 200 },
  });

  // Listen for OCR results to update the document store.
  const queueEvents = new QueueEvents(OCR_QUEUE_NAME, { connection: config.redis });

  queueEvents.on('completed', async ({ returnvalue }) => {
    try {
      const result = JSON.parse(returnvalue) as OcrJobResult;
      await store.update(result.documentId, {
        status: DocumentStatus.COMPLETED,
        extractedText: result.extractedText,
        pageCount: result.pageCount,
      });
      fastify.log.info({ documentId: result.documentId }, 'Document OCR completed');
    } catch (err) {
      fastify.log.error(err, 'Failed to apply OCR result');
    }
  });

  queueEvents.on('failed', async ({ jobId, failedReason }) => {
    try {
      const job = await ocrQueue.getJob(jobId);
      if (job) {
        await store.update(job.data.documentId, {
          status: DocumentStatus.FAILED,
          errorMessage: failedReason,
        });
      }
    } catch (err) {
      fastify.log.error(err, 'Failed to mark document as failed');
    }
  });

  await fastify.register(documentsRoute, {
    prefix: '/api/documents',
    store,
    storage,
    bucket: config.minioBucket,
    ocrQueue,
  });

  fastify.get('/health', async () => ({ status: 'ok', service: 'lexbangla-api' }));

  await fastify.listen({ port: config.port, host: config.host });

  const shutdown = async (): Promise<void> => {
    await queueEvents.close();
    await ocrQueue.close();
    await fastify.close();
    process.exit(0);
  };

  process.on('SIGTERM', shutdown);
  process.on('SIGINT', shutdown);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
