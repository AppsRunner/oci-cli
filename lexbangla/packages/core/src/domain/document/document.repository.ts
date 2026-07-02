import type { Document, CreateDocumentInput, UpdateDocumentInput } from './document.entity';

export interface DocumentRepository {
  create(input: CreateDocumentInput): Promise<Document>;
  findById(id: string): Promise<Document | null>;
  update(id: string, input: UpdateDocumentInput): Promise<Document>;
  list(limit?: number, offset?: number): Promise<Document[]>;
}
