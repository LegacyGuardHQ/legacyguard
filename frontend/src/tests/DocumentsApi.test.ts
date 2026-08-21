import { beforeEach, describe, expect, it, vi } from 'vitest';
import { uploadDocument } from '../api/documents';

describe('document upload API', () => {
  beforeEach(() => {
    sessionStorage.setItem('legacyguard.access_token', 'synthetic-token');
  });

  it('lets the browser set the multipart boundary and preserves authentication', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      id: 'document-1',
      document_type: 'OTHER',
      document_name: 'Record',
      original_filename: 'record.txt',
      mime_type: 'text/plain',
      file_size: 6,
      upload_status: 'COMPLETED',
      updated_at: '2026-08-20T12:00:00Z',
      discovery_scan: null,
    }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
    vi.stubGlobal('fetch', fetchMock);

    await uploadDocument('document/unsafe', new File(['record'], 'record.txt', { type: 'text/plain' }));

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toBe('http://localhost:8000/documents/document%2Funsafe/upload');
    const options = fetchMock.mock.calls[0][1] as RequestInit;
    const headers = options.headers as Headers;
    expect(headers.get('Authorization')).toBe('Bearer synthetic-token');
    expect(headers.has('Content-Type')).toBe(false);
    expect(options.body).toBeInstanceOf(FormData);
  });
});
