export const INGEST_QUEUE_NAME = 'document:ingest' as const;
export const REINGEST_QUEUE_NAME = 'document:reingest' as const;

export interface IngestJobData {
  sourceUrl: string;
  sourceType: 'url' | 'path' | 'storage';
  storageKey?: string;
  storageBucket?: string;
  language: string;
  triggeredBy: 'manual' | 'scheduled';
  scheduleKey?: string;
}

export interface IngestJobResult {
  sourceUrl: string;
  documentIds: string[];
  processedAt: string;
}
