export enum DocumentStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed',
}

export interface Document {
  id: string;
  originalName: string;
  filename: string;
  mimeType: string;
  sizeBytes: number;
  status: DocumentStatus;
  storageBucket: string;
  storageKey: string;
  language: string;
  extractedText?: string;
  pageCount?: number;
  errorMessage?: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface CreateDocumentInput {
  id: string;
  originalName: string;
  filename: string;
  mimeType: string;
  sizeBytes: number;
  storageBucket: string;
  storageKey: string;
  language?: string;
}

export interface UpdateDocumentInput {
  status?: DocumentStatus;
  extractedText?: string;
  pageCount?: number;
  errorMessage?: string;
}
