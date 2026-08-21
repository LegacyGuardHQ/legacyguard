import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../api/client';
import DocumentsPage from '../pages/DocumentsPage';
import type { DocumentUploadResponse, VaultDocument } from '../types/documents';

const { fetchDocumentsMock, createDocumentMock, uploadDocumentMock } = vi.hoisted(() => ({
  fetchDocumentsMock: vi.fn(),
  createDocumentMock: vi.fn(),
  uploadDocumentMock: vi.fn(),
}));

vi.mock('../api/documents', () => ({
  fetchDocuments: fetchDocumentsMock,
  createDocument: createDocumentMock,
  uploadDocument: uploadDocumentMock,
}));

const pendingDocument: VaultDocument = {
  id: 'document-1',
  asset_id: null,
  beneficiary_id: null,
  document_type: 'ACCOUNT_STATEMENT',
  document_name: 'Retirement statement',
  original_filename: null,
  mime_type: null,
  file_size: null,
  status: 'ACTIVE',
  verification_status: 'UNKNOWN',
  verified_at: null,
  review_due_at: null,
  effective_date: null,
  expiration_date: null,
  archived_at: null,
  version_number: 1,
  created_at: '2026-08-20T12:00:00Z',
  updated_at: '2026-08-20T12:00:00Z',
};

const storedDocument: VaultDocument = {
  ...pendingDocument,
  original_filename: 'statement.pdf',
  mime_type: 'application/pdf',
  file_size: 2048,
  verification_status: 'NEEDS_REVIEW',
};

const uploadResult: DocumentUploadResponse = {
  id: storedDocument.id,
  document_type: storedDocument.document_type,
  document_name: storedDocument.document_name,
  original_filename: 'statement.pdf',
  mime_type: 'application/pdf',
  file_size: 2048,
  upload_status: 'COMPLETED',
  updated_at: storedDocument.updated_at,
  discovery_scan: { scan_id: 'scan-1', status: 'PENDING' },
};

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter><DocumentsPage /></MemoryRouter>
    </QueryClientProvider>,
  );
}

function pdfFile() {
  return new File(['%PDF-1.7 synthetic content'], 'statement.pdf', { type: 'application/pdf' });
}

async function openUploadForm(user: ReturnType<typeof userEvent.setup>) {
  await user.click(await screen.findByRole('button', { name: 'Upload document' }));
}

describe('DocumentsPage', () => {
  beforeEach(() => {
    fetchDocumentsMock.mockReset();
    createDocumentMock.mockReset();
    uploadDocumentMock.mockReset();
  });

  it('announces its loading state', () => {
    fetchDocumentsMock.mockReturnValue(new Promise(() => undefined));
    renderPage();

    expect(screen.getByRole('status')).toHaveTextContent('Loading your document vault');
  });

  it('renders privacy-safe document metadata and file state', async () => {
    fetchDocumentsMock.mockResolvedValue([{ ...storedDocument, checksum_sha256: 'private-checksum', storage_reference: 'C:\\private\\vault' }]);
    renderPage();

    expect(await screen.findByRole('heading', { name: 'Retirement statement' })).toBeInTheDocument();
    expect(screen.getByText('statement.pdf')).toBeInTheDocument();
    expect(screen.getByText('2.0 KB')).toBeInTheDocument();
    expect(screen.getByText('Needs review')).toBeInTheDocument();
    expect(screen.getByText('Stored securely')).toBeInTheDocument();
    expect(screen.queryByText(/private-checksum|private\\vault/i)).not.toBeInTheDocument();
  });

  it('offers an empty state with an accessible upload form and backend-aligned guidance', async () => {
    const user = userEvent.setup();
    fetchDocumentsMock.mockResolvedValue([]);
    renderPage();

    expect(await screen.findByRole('heading', { name: 'Your document vault is empty' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Upload your first document' }));
    expect(screen.getByRole('heading', { name: 'Upload a document' })).toBeInTheDocument();
    expect(screen.getByLabelText(/Document name/)).toBeRequired();
    expect(screen.getByLabelText(/Document type/)).toHaveValue('OTHER');
    expect(screen.getByLabelText(/Document file/)).toHaveAttribute('accept', '.pdf,.jpg,.jpeg,.png,.txt,.docx,.xlsx');
    expect(screen.getByText(/Maximum size: 20 MB/)).toBeInTheDocument();
  });

  it('validates required and unsupported files without creating metadata', async () => {
    const user = userEvent.setup({ applyAccept: false });
    fetchDocumentsMock.mockResolvedValue([]);
    renderPage();
    await openUploadForm(user);

    await user.click(screen.getByRole('button', { name: 'Save and upload' }));
    expect(screen.getByRole('alert')).toHaveTextContent('Document name is required.');

    await user.type(screen.getByLabelText(/Document name/), 'Unsafe file');
    await user.upload(screen.getByLabelText(/Document file/), new File(['content'], 'payload.exe', { type: 'application/octet-stream' }));
    await user.click(screen.getByRole('button', { name: 'Save and upload' }));
    expect(screen.getByRole('alert')).toHaveTextContent('supported document format');

    const oversized = pdfFile();
    Object.defineProperty(oversized, 'size', { value: 20 * 1024 * 1024 + 1 });
    await user.upload(screen.getByLabelText(/Document file/), oversized);
    await user.click(screen.getByRole('button', { name: 'Save and upload' }));
    expect(screen.getByRole('alert')).toHaveTextContent('20 MB or smaller');
    expect(createDocumentMock).not.toHaveBeenCalled();
    expect(uploadDocumentMock).not.toHaveBeenCalled();
  });

  it('creates metadata, uploads content, refreshes the list, and reports discovery separately', async () => {
    const user = userEvent.setup();
    fetchDocumentsMock.mockResolvedValueOnce([]).mockResolvedValue([storedDocument]);
    createDocumentMock.mockResolvedValue(pendingDocument);
    uploadDocumentMock.mockResolvedValue(uploadResult);
    renderPage();
    await openUploadForm(user);

    await user.selectOptions(screen.getByLabelText(/Document type/), 'ACCOUNT_STATEMENT');
    await user.upload(screen.getByLabelText(/Document file/), pdfFile());
    await user.click(screen.getByRole('button', { name: 'Save and upload' }));

    await waitFor(() => expect(createDocumentMock).toHaveBeenCalled());
    expect(createDocumentMock.mock.calls[0][0]).toEqual({ document_name: 'statement', document_type: 'ACCOUNT_STATEMENT' });
    expect(createDocumentMock.mock.calls[0][0]).not.toHaveProperty('user_id');
    expect(uploadDocumentMock.mock.calls[0][0]).toBe('document-1');
    expect(uploadDocumentMock.mock.calls[0][1]).toBeInstanceOf(File);
    expect(await screen.findByRole('status')).toHaveTextContent('Document uploaded securely. Discovery has started.');
    expect(await screen.findByRole('heading', { name: 'Retirement statement' })).toBeInTheDocument();
  });

  it('does not present discovery failure as a failed encrypted upload', async () => {
    const user = userEvent.setup();
    fetchDocumentsMock.mockResolvedValueOnce([]).mockResolvedValue([storedDocument]);
    createDocumentMock.mockResolvedValue(pendingDocument);
    uploadDocumentMock.mockResolvedValue({ ...uploadResult, discovery_scan: { scan_id: 'scan-1', status: 'FAILED' } });
    renderPage();
    await openUploadForm(user);
    await user.upload(screen.getByLabelText(/Document file/), pdfFile());
    await user.click(screen.getByRole('button', { name: 'Save and upload' }));

    expect(await screen.findByRole('status')).toHaveTextContent('Document uploaded securely. Discovery needs attention, but your file remains saved.');
  });

  it('keeps a failed file upload retryable without duplicating metadata', async () => {
    const user = userEvent.setup();
    fetchDocumentsMock.mockResolvedValueOnce([]).mockResolvedValue([pendingDocument]);
    createDocumentMock.mockResolvedValue(pendingDocument);
    uploadDocumentMock.mockRejectedValueOnce(new ApiError('C:\\private\\storage-secret.txt', 500)).mockResolvedValueOnce(uploadResult);
    renderPage();
    await openUploadForm(user);
    await user.upload(screen.getByLabelText(/Document file/), pdfFile());
    await user.click(screen.getByRole('button', { name: 'Save and upload' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('document record was saved, but the file could not be uploaded');
    expect(screen.queryByText(/storage-secret/i)).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Retry file upload' }));

    await waitFor(() => expect(uploadDocumentMock).toHaveBeenCalledTimes(2));
    expect(createDocumentMock).toHaveBeenCalledTimes(1);
    expect(await screen.findByRole('status')).toHaveTextContent('Document uploaded securely');
  });

  it('lets a user add content to an existing metadata-only document', async () => {
    const user = userEvent.setup();
    fetchDocumentsMock.mockResolvedValue([pendingDocument]);
    uploadDocumentMock.mockResolvedValue(uploadResult);
    renderPage();

    await user.click(await screen.findByRole('button', { name: 'Add file' }));
    expect(screen.getByRole('heading', { name: 'Add file to Retirement statement' })).toBeInTheDocument();
    expect(screen.getByLabelText(/Document name/)).toBeDisabled();
    await user.upload(screen.getByLabelText(/Document file/), pdfFile());
    await user.click(screen.getByRole('button', { name: 'Retry file upload' }));

    await waitFor(() => expect(uploadDocumentMock).toHaveBeenCalled());
    expect(createDocumentMock).not.toHaveBeenCalled();
  });

  it('shows a privacy-safe load failure and retries', async () => {
    const user = userEvent.setup();
    fetchDocumentsMock.mockRejectedValueOnce(new ApiError('C:\\private\\list-secret.txt', 500)).mockResolvedValueOnce([storedDocument]);
    renderPage();

    expect(await screen.findByRole('alert')).toHaveTextContent('We couldn’t load your document vault.');
    expect(screen.queryByText(/list-secret/i)).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByRole('heading', { name: 'Retirement statement' })).toBeInTheDocument();
  });
});
