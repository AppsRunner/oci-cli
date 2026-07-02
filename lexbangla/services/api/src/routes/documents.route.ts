import type { FastifyPluginAsync } from 'fastify';
import { randomUUID } from 'crypto';
import type { Queue } from 'bullmq';
import type { DocumentRepository, OcrJobData } from '@lexbangla/core';
import { OCR_QUEUE_NAME } from '@lexbangla/core';
import type { MinioStorageService } from '@lexbangla/ocr';

interface DocumentRouteOptions {
  store: DocumentRepository;
  storage: MinioStorageService;
  bucket: string;
  ocrQueue: Queue<OcrJobData>;
}

export const documentsRoute: FastifyPluginAsync<DocumentRouteOptions> = async (
  fastify,
  { store, storage, bucket, ocrQueue },
) => {
  /** POST /api/documents/upload — accept a PDF or image, store in MinIO, enqueue OCR. */
  fastify.post('/upload', async (request, reply) => {
    const part = await request.file();
    if (!part) {
      return reply.status(400).send({ error: 'No file provided' });
    }

    const allowedTypes = new Set([
      'application/pdf',
      'image/png',
      'image/jpeg',
      'image/tiff',
      'image/webp',
    ]);
    if (!allowedTypes.has(part.mimetype)) {
      await part.file.resume(); // drain the stream
      return reply.status(415).send({ error: `Unsupported file type: ${part.mimetype}` });
    }

    // Buffer the upload.
    const chunks: Buffer[] = [];
    for await (const chunk of part.file) {
      chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk as string));
    }
    const buffer = Buffer.concat(chunks);

    const id = randomUUID();
    const ext = part.filename.split('.').pop() ?? 'bin';
    const storageKey = `documents/${id}.${ext}`;
    const language =
      (request.query as Record<string, string | undefined>).language ?? 'ben+eng';

    // Upload to MinIO.
    await storage.putObject(bucket, storageKey, buffer, buffer.length, part.mimetype);

    // Persist document record.
    const doc = await store.create({
      id,
      originalName: part.filename,
      filename: `${id}.${ext}`,
      mimeType: part.mimetype,
      sizeBytes: buffer.length,
      storageBucket: bucket,
      storageKey,
      language,
    });

    // Enqueue OCR job.
    await ocrQueue.add(
      OCR_QUEUE_NAME,
      {
        documentId: id,
        originalName: doc.originalName,
        filename: doc.filename,
        mimeType: doc.mimeType,
        sizeBytes: doc.sizeBytes,
        storageKey,
        storageBucket: bucket,
        language,
      },
      { attempts: 3, backoff: { type: 'exponential', delay: 2000 } },
    );

    return reply.status(202).send(doc);
  });

  /** GET /api/documents/:id — fetch a single document by ID. */
  fastify.get<{ Params: { id: string } }>('/:id', async (request, reply) => {
    const doc = await store.findById(request.params.id);
    if (!doc) return reply.status(404).send({ error: 'Document not found' });
    return doc;
  });

  /** GET /api/documents — list documents with optional pagination. */
  fastify.get<{ Querystring: { limit?: string; offset?: string } }>('/', async (request) => {
    const limit = Math.min(Number(request.query.limit ?? 20), 100);
    const offset = Number(request.query.offset ?? 0);
    const items = await store.list(limit, offset);
    return { items, total: items.length };
  });
};
