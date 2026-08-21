import { request } from './client';
import type { DocumentCreate, DocumentUploadResponse, VaultDocument } from '../types/documents';

export function fetchDocuments(): Promise<VaultDocument[]> {
  return request<VaultDocument[]>('/documents', {}, true);
}

export function createDocument(payload: DocumentCreate): Promise<VaultDocument> {
  return request<VaultDocument>('/documents', {
    method: 'POST',
    body: JSON.stringify(payload),
  }, true);
}

export function uploadDocument(documentId: string, file: File): Promise<DocumentUploadResponse> {
  const form = new FormData();
  form.append('file', file, file.name);
  return request<DocumentUploadResponse>(`/documents/${encodeURIComponent(documentId)}/upload`, {
    method: 'POST',
    body: form,
  }, true);
}
