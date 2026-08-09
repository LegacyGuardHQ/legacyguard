import React from 'react';
import { Link, useParams } from 'react-router-dom';
import { ApiError } from '../api/client';
import { useDiscoveryFindingDetail } from '../hooks/useDiscoveryFindingDetail';
import { useManualAssetConversion } from '../hooks/useManualAssetConversion';
import { useUpdateFindingStatus } from '../hooks/useDiscoveryReviewQueue';
import { usePageTitle } from '../hooks/usePageTitle';
import type {
  DiscoveryReviewStatus,
  ManualAssetConversionDetails,
  ManualAssetConversionRequest,
} from '../types/discovery';

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

function getReviewStatusDescription(status: DiscoveryReviewStatus): string {
  if (status === 'PENDING_REVIEW') {
    return 'This finding is still waiting for your review and should not be treated as confirmed.';
  }
  if (status === 'CONFIRMED') {
    return 'You confirmed this finding as a reviewed signal. It remains an unverified signal, not proof.';
  }
  return 'You dismissed this finding for now. It will stay out of the active review queue until you reopen it.';
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

type ConversionFormFields = {
  asset_name: string;
  asset_category: string;
  institution: string;
  description: string;
  estimated_value: string;
  ownership_type: string;
  account_number: string;
  policy_number: string;
  notes: string;
  claim_instructions: string;
};

function trimmedValue(formData: FormData, name: keyof ConversionFormFields): string {
  return String(formData.get(name) ?? '').trim();
}

function buildConversionPayload(formData: FormData):
  | { payload: ManualAssetConversionRequest; error: null }
  | { payload: null; error: string } {
  const assetName = trimmedValue(formData, 'asset_name');
  const assetCategory = trimmedValue(formData, 'asset_category');
  if (!assetName || !assetCategory) {
    return { payload: null, error: 'Asset name and category are required.' };
  }

  const estimatedValueText = trimmedValue(formData, 'estimated_value');
  const estimatedValue = estimatedValueText ? Number(estimatedValueText) : undefined;
  if (estimatedValue !== undefined && (!Number.isFinite(estimatedValue) || estimatedValue < 0)) {
    return { payload: null, error: 'Estimated value must be zero or greater.' };
  }

  const payload: ManualAssetConversionRequest = {
    asset_name: assetName,
    asset_category: assetCategory,
  };
  const optionalFields = ['institution', 'description', 'ownership_type'] as const;
  optionalFields.forEach((field) => {
    const value = trimmedValue(formData, field);
    if (value) payload[field] = value;
  });
  if (estimatedValue !== undefined) payload.estimated_value = estimatedValue;

  const details: ManualAssetConversionDetails = {};
  const detailFields = ['account_number', 'policy_number', 'notes', 'claim_instructions'] as const;
  detailFields.forEach((field) => {
    const value = trimmedValue(formData, field);
    if (value) details[field] = value;
  });
  if (Object.keys(details).length > 0) payload.details = details;

  return { payload, error: null };
}

function ManualAssetConversion({ findingId }: { findingId: string }) {
  const conversionMutation = useManualAssetConversion(findingId);
  const [validationError, setValidationError] = React.useState<string | null>(null);

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (conversionMutation.isPending || conversionMutation.isSuccess) return;

    setValidationError(null);
    conversionMutation.reset();
    const result = buildConversionPayload(new FormData(event.currentTarget));
    if (!result.payload) {
      setValidationError(result.error);
      return;
    }
    conversionMutation.mutate(result.payload);
  };

  let mutationError = 'Unable to create this asset. Please try again.';
  if (conversionMutation.error instanceof ApiError && conversionMutation.error.status === 409) {
    mutationError = conversionMutation.error.detail === 'An asset has already been created from this finding'
      ? 'An asset has already been created from this finding.'
      : 'This finding is no longer eligible for asset conversion.';
  }

  if (conversionMutation.isSuccess) {
    return (
      <section className="finding-detail-card conversion-card" aria-labelledby="conversion-title">
        <div>
          <p className="eyebrow">Manual asset conversion</p>
          <h2 id="conversion-title">Asset created for review</h2>
          <p>
            This asset remains unverified and requires your review before it should be relied upon.
          </p>
        </div>
        <p>
          This asset was created from a confirmed discovery finding and should still be reviewed before it is relied upon.
        </p>
        <dl className="conversion-result" aria-live="polite">
          <div>
            <dt>Asset reference</dt>
            <dd className="resource-id">{conversionMutation.data.id}</dd>
          </div>
          <div>
            <dt>Verification status</dt>
            <dd>{formatLabel(conversionMutation.data.verification_status)}</dd>
          </div>
        </dl>
      </section>
    );
  }

  return (
    <section className="finding-detail-card conversion-card" aria-labelledby="conversion-title">
      <div>
        <p className="eyebrow">Manual asset conversion</p>
        <h2 id="conversion-title">Create an asset for review</h2>
        <p>
          This user-initiated step creates an unverified asset that still requires review. Account and policy details are optional; enter them only when useful.
        </p>
      </div>

      {validationError ? <div className="finding-feedback finding-feedback-error" role="alert">{validationError}</div> : null}
      {conversionMutation.isError ? (
        <div className="finding-feedback finding-feedback-error" role="alert">{mutationError}</div>
      ) : null}

      <form className="conversion-form" onSubmit={handleSubmit} noValidate>
        <div className="conversion-field">
          <label htmlFor="asset-name">Asset name <span aria-hidden="true">*</span></label>
          <input id="asset-name" name="asset_name" type="text" required disabled={conversionMutation.isPending} />
        </div>
        <div className="conversion-field">
          <label htmlFor="asset-category">Asset category <span aria-hidden="true">*</span></label>
          <input id="asset-category" name="asset_category" type="text" required disabled={conversionMutation.isPending} />
        </div>
        <div className="conversion-field">
          <label htmlFor="asset-institution">Institution <span className="optional-label">Optional</span></label>
          <input id="asset-institution" name="institution" type="text" disabled={conversionMutation.isPending} />
        </div>
        <div className="conversion-field">
          <label htmlFor="asset-value">Estimated value <span className="optional-label">Optional</span></label>
          <input id="asset-value" name="estimated_value" type="number" min="0" step="any" disabled={conversionMutation.isPending} />
        </div>
        <div className="conversion-field conversion-field-wide">
          <label htmlFor="asset-description">Description <span className="optional-label">Optional</span></label>
          <textarea id="asset-description" name="description" rows={3} disabled={conversionMutation.isPending} />
        </div>
        <div className="conversion-field">
          <label htmlFor="asset-ownership">Ownership type <span className="optional-label">Optional</span></label>
          <input id="asset-ownership" name="ownership_type" type="text" disabled={conversionMutation.isPending} />
        </div>
        <div className="conversion-field">
          <label htmlFor="asset-account-number">Account number <span className="optional-label">Optional</span></label>
          <input id="asset-account-number" name="account_number" type="text" disabled={conversionMutation.isPending} />
        </div>
        <div className="conversion-field">
          <label htmlFor="asset-policy-number">Policy number <span className="optional-label">Optional</span></label>
          <input id="asset-policy-number" name="policy_number" type="text" disabled={conversionMutation.isPending} />
        </div>
        <div className="conversion-field conversion-field-wide">
          <label htmlFor="asset-notes">Notes <span className="optional-label">Optional</span></label>
          <textarea id="asset-notes" name="notes" rows={3} disabled={conversionMutation.isPending} />
        </div>
        <div className="conversion-field conversion-field-wide">
          <label htmlFor="asset-claim-instructions">Claim instructions <span className="optional-label">Optional</span></label>
          <textarea id="asset-claim-instructions" name="claim_instructions" rows={3} disabled={conversionMutation.isPending} />
        </div>
        <div className="conversion-submit-row">
          <button className="btn btn-success" type="submit" disabled={conversionMutation.isPending}>
            {conversionMutation.isPending ? 'Creating asset…' : 'Create asset for review'}
          </button>
        </div>
      </form>
    </section>
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
          <p>Finding status updated.</p>
          <p>{getReviewStatusDescription(finding.review_status)}</p>
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

      {finding.review_status === 'CONFIRMED' ? (
        <ManualAssetConversion findingId={finding.finding_id} />
      ) : null}

      <footer className="finding-detail-footer">
        <Link className="text-link" to="/discovery/review">
          ← Back to Review Queue
        </Link>
      </footer>
    </main>
  );
}
