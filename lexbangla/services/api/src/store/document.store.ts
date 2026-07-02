import type {
  Document,
  CreateDocumentInput,
  UpdateDocumentInput,
  DocumentRepository,
} from '@lexbangla/core';
import { DocumentStatus } from '@lexbangla/core';

/**
 * In-memory DocumentRepository for development.
 * Replace with a PostgreSQL / TypeORM implementation for production.
 */
export class InMemoryDocumentStore implements DocumentRepository {
  private readonly docs = new Map<string, Document>();

  async create(input: CreateDocumentInput): Promise<Document> {
    const now = new Date();
    const doc: Document = {
      language: 'ben+eng',
      ...input,
      status: DocumentStatus.PENDING,
      createdAt: now,
      updatedAt: now,
    };
    this.docs.set(doc.id, doc);
    return { ...doc };
  }

  async findById(id: string): Promise<Document | null> {
    const doc = this.docs.get(id);
    return doc ? { ...doc } : null;
  }

  async update(id: string, input: UpdateDocumentInput): Promise<Document> {
    const doc = this.docs.get(id);
    if (!doc) throw new Error(`Document ${id} not found`);
    const updated: Document = { ...doc, ...input, updatedAt: new Date() };
    this.docs.set(id, updated);
    return { ...updated };
  }

  async list(limit = 20, offset = 0): Promise<Document[]> {
    return [...this.docs.values()]
      .sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime())
      .slice(offset, offset + limit)
      .map((d) => ({ ...d }));
  }
}
