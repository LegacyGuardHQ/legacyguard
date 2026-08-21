import React, { useState } from 'react';
import { EmptyState, ErrorState, LoadingState } from '../components/DashboardStates';
import { useCreateDocument, useDocuments, useUploadDocument } from '../hooks/useDocuments';
import { usePageTitle } from '../hooks/usePageTitle';
import { documentTypes, type DiscoveryScanStatus, type DocumentType, type VaultDocument } from '../types/documents';

const MAX_DOCUMENT_BYTES = 20 * 1024 * 1024;
const acceptedFileTypes = '.pdf,.jpg,.jpeg,.png,.txt,.docx,.xlsx';
const allowedMimeTypes = new Map<string, string[]>([
  ['.pdf', ['application/pdf']],
  ['.jpg', ['image/jpeg']],
  ['.jpeg', ['image/jpeg']],
  ['.png', ['image/png']],
  ['.txt', ['text/plain']],
  ['.docx', ['application/vnd.openxmlformats-officedocument.wordprocessingml.document']],
  ['.xlsx', ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']],
]);

function displayEnum(value: string): string {
  return value.replace(/_/g, ' ').toLowerCase().replace(/^./, (character) => character.toUpperCase());
}

function displaySize(value: number | null): string {
  if (value === null) return 'File pending';
  if (value < 1024) return `${value} bytes`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function uploadSuccessMessage(status: DiscoveryScanStatus | null): string {
  if (status === 'COMPLETE') return 'Document uploaded securely. Discovery completed.';
  if (status === 'COMPLETED_WITH_WARNINGS') return 'Document uploaded securely. Discovery completed with limited results.';
  if (status === 'FAILED') return 'Document uploaded securely. Discovery needs attention, but your file remains saved.';
  if (status === 'PENDING' || status === 'RUNNING') return 'Document uploaded securely. Discovery has started.';
  return 'Document uploaded securely. Discovery could not be started, but your file remains saved.';
}

function validateFile(file: File): string | null {
  if (file.size === 0) return 'Choose a file that is not empty.';
  if (file.size > MAX_DOCUMENT_BYTES) return 'Choose a file that is 20 MB or smaller.';
  const normalizedName = file.name.toLowerCase();
  const suffixes = normalizedName.match(/\.[^.]+/g) || [];
  if (suffixes.length !== 1) return 'Choose a file with one supported extension.';
  const allowedMimes = allowedMimeTypes.get(suffixes[0]);
  if (!allowedMimes || !allowedMimes.includes(file.type)) return 'The file extension and type must match a supported document format.';
  return null;
}

function defaultDocumentName(fileName: string): string {
  return fileName.replace(/\.[^.]+$/, '').trim();
}

export default function DocumentsPage() {
  usePageTitle('Document Vault');
  const documents = useDocuments();
  const create = useCreateDocument();
  const upload = useUploadDocument();
  const [showForm, setShowForm] = useState(false);
  const [documentName, setDocumentName] = useState('');
  const [documentType, setDocumentType] = useState<DocumentType>('OTHER');
  const [file, setFile] = useState<File | null>(null);
  const [retryDocumentId, setRetryDocumentId] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [fileInputKey, setFileInputKey] = useState(0);

  const isSubmitting = create.isPending || upload.isPending;

  function resetForm() {
    setDocumentName('');
    setDocumentType('OTHER');
    setFile(null);
    setRetryDocumentId(null);
    setFormError(null);
    setFileInputKey((current) => current + 1);
  }

  function setFormVisible(visible: boolean) {
    setShowForm(visible);
    setFormError(null);
    if (visible) setSuccessMessage(null);
    if (!visible) resetForm();
  }

  function preparePendingUpload(document: VaultDocument) {
    resetForm();
    setDocumentName(document.document_name);
    setDocumentType(document.document_type);
    setRetryDocumentId(document.id);
    setSuccessMessage(null);
    setShowForm(true);
  }

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] || null;
    setFile(selected);
    setFormError(null);
    if (selected && !retryDocumentId && !documentName.trim()) setDocumentName(defaultDocumentName(selected.name));
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    setSuccessMessage(null);

    if (!documentName.trim()) {
      setFormError('Document name is required.');
      return;
    }
    if (!file) {
      setFormError('Choose a document file to upload.');
      return;
    }
    const fileError = validateFile(file);
    if (fileError) {
      setFormError(fileError);
      return;
    }

    let documentId = retryDocumentId;
    if (!documentId) {
      try {
        const created = await create.mutateAsync({ document_name: documentName.trim(), document_type: documentType });
        documentId = created.id;
        setRetryDocumentId(created.id);
      } catch {
        setFormError('Unable to create this document record. Your information has not been changed.');
        return;
      }
    }

    try {
      const result = await upload.mutateAsync({ documentId, file });
      setSuccessMessage(uploadSuccessMessage(result.discovery_scan?.status || null));
      resetForm();
      setShowForm(false);
    } catch {
      setFormError('The document record was saved, but the file could not be uploaded. Check the file and try again.');
    }
  }

  if (documents.isLoading) {
    return <LoadingState message="Loading your document vault" description="We’re retrieving your private document metadata." />;
  }

  if (documents.isError) {
    return (
      <ErrorState
        title="We couldn’t load your document vault."
        message="Check your connection and try again. Your saved documents have not been changed."
        onRetry={() => void documents.refetch()}
        isRetrying={documents.isFetching}
      />
    );
  }

  return (
    <section className="page-panel documents-page" aria-labelledby="documents-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Encrypted continuity records</p>
          <h1 id="documents-title">Document Vault</h1>
          <p>Store essential records securely and keep their review status visible without exposing document contents.</p>
        </div>
        <button className="primary-button" type="button" onClick={() => setFormVisible(!showForm)}>
          {showForm ? 'Cancel' : 'Upload document'}
        </button>
      </div>

      {successMessage && <div className="document-success" role="status" aria-live="polite">{successMessage}</div>}

      {showForm && (
        <form className="document-form" onSubmit={handleSubmit} noValidate>
          <h2>{retryDocumentId ? `Add file to ${documentName}` : 'Upload a document'}</h2>
          <p className="muted-text">Accepted: PDF, JPG, PNG, TXT, DOCX, or XLSX. Maximum size: 20 MB.</p>
          <div className="document-form-grid">
            <label>
              Document name <span aria-hidden="true">(required)</span>
              <input value={documentName} onChange={(event) => setDocumentName(event.target.value)} required aria-required="true" disabled={Boolean(retryDocumentId)} />
            </label>
            <label>
              Document type <span aria-hidden="true">(required)</span>
              <select value={documentType} onChange={(event) => setDocumentType(event.target.value as DocumentType)} disabled={Boolean(retryDocumentId)}>
                {documentTypes.map((value) => <option key={value} value={value}>{displayEnum(value)}</option>)}
              </select>
            </label>
            <label className="document-form-wide">
              Document file <span aria-hidden="true">(required)</span>
              <input key={fileInputKey} type="file" accept={acceptedFileTypes} onChange={handleFileChange} required aria-required="true" />
            </label>
          </div>
          {formError && <div className="error-message" role="alert">{formError}</div>}
          <button className="primary-button" type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Uploading securely…' : retryDocumentId ? 'Retry file upload' : 'Save and upload'}
          </button>
        </form>
      )}

      {documents.data?.length === 0 ? (
        <EmptyState
          title="Your document vault is empty"
          description="Upload an essential document to begin your private continuity record. Discovery runs after a successful file upload."
          action={{ label: 'Upload your first document', onClick: () => setFormVisible(true) }}
        />
      ) : (
        <ul className="document-list" aria-label="Vault documents">
          {documents.data?.map((document) => (
            <li className="document-card" key={document.id}>
              <div className="document-card-heading">
                <div>
                  <span className="category-badge">{displayEnum(document.document_type)}</span>
                  <h2>{document.document_name}</h2>
                </div>
                <span className={`document-verification verification-${document.verification_status.toLowerCase()}`}>
                  {displayEnum(document.verification_status)}
                </span>
              </div>
              <dl className="document-summary">
                <div><dt>File</dt><dd>{document.original_filename || 'Not uploaded'}</dd></div>
                <div><dt>Size</dt><dd>{displaySize(document.file_size)}</dd></div>
                <div><dt>Storage</dt><dd>{document.original_filename ? 'Stored securely' : 'File pending'}</dd></div>
                <div><dt>Status</dt><dd>{displayEnum(document.status)}</dd></div>
              </dl>
              {!document.original_filename && (
                <button className="secondary-button" type="button" onClick={() => preparePendingUpload(document)}>Add file</button>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
