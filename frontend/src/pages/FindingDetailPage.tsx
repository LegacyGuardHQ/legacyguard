import React from 'react';
import { Link, useParams } from 'react-router-dom';
import { ApiError } from '../api/client';
import { useDiscoveryFindingDetail } from '../hooks/useDiscoveryFindingDetail';
import { useUpdateFindingStatus } from '../hooks/useDiscoveryReviewQueue';
import { usePageTitle } from '../hooks/usePageTitle';
import type { DiscoveryReviewStatus } from '../types/discovery';

function formatLabel(value: string): string {
  return value
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
}

function formatReviewStatus(status: DiscoveryReviewStatus): string {
  if (status === 'PENDING_REVIEW') return 'Pending Review';
  return formatLabel(status);
}

function formatTimestamp(value: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(
    new Date(value)
  );
}

type ReviewActionsProps = {
  findingId: string;
  status: DiscoveryReviewStatus;
  disabled: boolean;
  onUpdate: (findingId: string, status: DiscoveryReviewStatus) => void;
};

function ReviewActions({ findingId, status, disabled, onUpdate }: ReviewActionsProps) {
  return (
    <div className="action-buttons" role="group" aria-label="Finding review actions">
      {status === 'PENDING_REVIEW' ? (
        <>
          <button
            type="button"
            className="btn btn-success"
            onClick={() => onUpdate(findingId, 'CONFIRMED')}
            disabled={disabled}
          >
            Confirm
          </button>
          <button
            type="button"
            className="btn btn-danger"
            onClick={() => onUpdate(findingId, 'DISMISSED')}
            disabled={disabled}
          >
            Dismiss
          </button>
        </>
      ) : null}

      {status === 'CONFIRMED' ? (
        <>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => onUpdate(findingId, 'PENDING_REVIEW')}
            disabled={disabled}
          >
            Reopen
          </button>
          <button
            type="button"
            className="btn btn-danger"
            onClick={() => onUpdate(findingId, 'DISMISSED')}
            disabled={disabled}
          >
            Dismiss
          </button>
        </>
      ) : null}

      {status === 'DISMISSED' ? (
        <>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => onUpdate(findingId, 'PENDING_REVIEW')}
            disabled={disabled}
          >
            Reopen
          </button>
          <button
            type="button"
            className="btn btn-success"
            onClick={() => onUpdate(findingId, 'CONFIRMED')}
            disabled={disabled}
          >
            Confirm
          </button>
        </>
      ) : null}
    </div>
  );
}

export default function FindingDetailPage() {
  const { findingId = '' } = useParams<{ findingId: string }>();
  usePageTitle('Finding details');
  const findingQuery = useDiscoveryFindingDetail(findingId);
  const updateMutation = useUpdateFindingStatus();

  const handleUpdateStatus = (id: string, status: DiscoveryReviewStatus) => {
    updateMutation.reset();
    updateMutation.mutate({ findingId: id, reviewStatus: status });
  };

  if (!findingId) {
    return (
      <section className="dashboard-state dashboard-error" role="alert">
        <span className="state-symbol" aria-hidden="true">!</span>
        <h1>Finding unavailable</h1>
        <p>This finding could not be identified. Return to the review queue and choose a finding to inspect.</p>
        <Link className="text-link finding-state-link" to="/discovery/review">
          Back to Review Queue
        </Link>
      </section>
    );
  }

  if (findingQuery.isPending) {
    return (
      <section className="dashboard-state" role="status" aria-live="polite" aria-busy="true">
        <span className="state-symbol" aria-hidden="true">◌</span>
        <h1>Securely loading this finding.</h1>
        <p>We’re preparing privacy-safe finding and source document details.</p>
      </section>
    );
  }

  if (findingQuery.isError && !findingQuery.data) {
    const isUnavailable = findingQuery.error instanceof ApiError && findingQuery.error.status === 404;
    return (
      <section className="dashboard-state dashboard-error" role="alert">
        <span className="state-symbol" aria-hidden="true">!</span>
        <h1>{isUnavailable ? 'Finding unavailable' : 'Unable to load this finding'}</h1>
        <p>
          {isUnavailable
            ? 'This finding is unavailable or you do not have access to it.'
            : 'Check your connection and try again. Your saved finding has not been changed.'}
        </p>
        {!isUnavailable ? (
          <button
            className="secondary-button"
            type="button"
            onClick={() => findingQuery.refetch()}
            disabled={findingQuery.isFetching}
          >
            {findingQuery.isFetching ? 'Trying again…' : 'Try again'}
          </button>
        ) : null}
        <Link className="text-link finding-state-link" to="/discovery/review">
          Back to Review Queue
        </Link>
      </section>
    );
  }

  const finding = findingQuery.data;
  if (!finding) return null;

  const actionsDisabled = updateMutation.isPending || findingQuery.isFetching;

  return (
    <main className="finding-detail" aria-busy={actionsDisabled}>
      <header className="finding-detail-header">
        <div className="finding-detail-header-row">
          <div>
            <p className="eyebrow">Discovery finding</p>
            <h1>{formatLabel(finding.category)}</h1>
          </div>
          <span className={`finding-review-status review-status-${finding.review_status.toLowerCase()}`}>
            {formatReviewStatus(finding.review_status)}
          </span>
        </div>
        <p>
          Review privacy-safe metadata and rule-based signal strength before deciding how this finding should be classified.
        </p>
      </header>

      {updateMutation.isError ? (
        <div className="finding-feedback finding-feedback-error" role="alert">
          Unable to update this finding. Please try again.
        </div>
      ) : null}

      {updateMutation.isSuccess ? (
        <div className="finding-feedback finding-feedback-success" role="status" aria-live="polite">
          Finding status updated.
        </div>
      ) : null}

      <section className="finding-detail-card" aria-labelledby="finding-metadata-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Finding metadata</p>
            <h2 id="finding-metadata-title">Review context</h2>
          </div>
        </div>
        <dl className="finding-metadata-grid">
          <div>
            <dt>Category</dt>
            <dd>{formatLabel(finding.category)}</dd>
          </div>
          <div>
            <dt>Review status</dt>
            <dd>{formatReviewStatus(finding.review_status)}</dd>
          </div>
          <div>
            <dt>Signal strength</dt>
            <dd>{finding.confidence_score.toFixed(0)}%</dd>
          </div>
          <div>
            <dt>Created</dt>
            <dd>{formatTimestamp(finding.created_at)}</dd>
          </div>
        </dl>
        <p className="finding-signal-explanation">
          Signal strength reflects rule-based detection cues. It is not a probability, certainty, ownership determination, financial verification, or proof that an asset exists.
        </p>
      </section>

      <section className="finding-detail-card" aria-labelledby="source-document-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Privacy-safe source</p>
            <h2 id="source-document-title">Source document</h2>
          </div>
        </div>
        <dl className="finding-source-grid">
          <div>
            <dt>Document name</dt>
            <dd>{finding.document_name}</dd>
          </div>
          <div>
            <dt>Document type</dt>
            <dd>{formatLabel(finding.document_type)}</dd>
          </div>
          <div>
            <dt>Document reference</dt>
            <dd className="resource-id">{finding.document_id}</dd>
          </div>
          <div>
            <dt>Source scan</dt>
            <dd>
              <Link className="text-link" to={`/discovery/scans/${encodeURIComponent(finding.scan_id)}`}>
                View scan {finding.scan_id}
              </Link>
            </dd>
          </div>
        </dl>
        <p className="finding-privacy-note">
          This view does not display document contents, extracted text, matched terms, storage details, encryption references, or raw evidence.
        </p>
      </section>

      <section className="finding-detail-card finding-review-card" aria-labelledby="review-actions-title">
        <div>
          <p className="eyebrow">Human review</p>
          <h2 id="review-actions-title">Update review status</h2>
          <p>Choose the status that best reflects your review. Automated signals are not treated as proof.</p>
        </div>
        <ReviewActions
          findingId={finding.finding_id}
          status={finding.review_status}
          disabled={actionsDisabled}
          onUpdate={handleUpdateStatus}
        />
      </section>

      <footer className="finding-detail-footer">
        <Link className="text-link" to="/discovery/review">
          ← Back to Review Queue
        </Link>
      </footer>
    </main>
  );
}
