import React, { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { EmptyState, ErrorState, LoadingState } from '../components/DashboardStates';
import StatusBadge from '../components/StatusBadge';
import {
  useDiscoveryScan,
  useDiscoveryScanDocuments,
  useDiscoveryScanFindings,
  useDiscoveryScanReport,
  useDiscoveryScanSummary,
} from '../hooks/useDiscoveryScanDetail';
import { usePageTitle } from '../hooks/usePageTitle';

const FINDINGS_PAGE_SIZE = 10;

function formatTimestamp(value: string | null) {
  if (!value) return 'Not completed';
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
}

function formatCategory(category: string) {
  return category
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
}

function formatReviewStatus(status: string) {
  if (status === 'PENDING_REVIEW') return 'Pending review';
  if (status === 'CONFIRMED') return 'Confirmed';
  if (status === 'DISMISSED') return 'Dismissed';
  return formatCategory(status);
}

function formatDocumentWarning(warningCode: string | null) {
  if (!warningCode) return null;
  if (warningCode === 'UNSUPPORTED_EXTRACTION') {
    return 'Content format limitation';
  }
  if (warningCode === 'PROCESSING_FAILED') {
    return 'Processing encountered an issue';
  }
  return 'Processing notice';
}

function formatLifecycleMessage(
  status: string,
  lifecycleState: string,
  recoveredFromStale: boolean,
  processingOutcomeMessage?: string | null,
  backgroundJobMessage?: string | null,
) {
  if (backgroundJobMessage) {
    return backgroundJobMessage;
  }

  if (processingOutcomeMessage) {
    return processingOutcomeMessage;
  }

  if (recoveredFromStale) {
    if (status === 'COMPLETE' || status === 'COMPLETED_WITH_WARNINGS') {
      return 'Completed successfully';
    }
    return 'Recovered from a stale running state';
  }

  if (lifecycleState === 'QUEUED') return 'Queued for processing';
  if (lifecycleState === 'RUNNING') return 'Discovery processing is active';
  if (lifecycleState === 'COMPLETED') return 'Completed successfully';
  if (lifecycleState === 'COMPLETED_WITH_WARNINGS') return 'Completed with warnings';
  if (lifecycleState === 'FAILED') return 'Failed';
  return 'Processing status available';
}

function formatActiveBannerMessage(backgroundJobState: string) {
  if (backgroundJobState === 'RETRYING') {
    return 'Discovery processing is retrying in the background. Updating details automatically...';
  }
  if (backgroundJobState === 'QUEUED') {
    return 'Discovery processing is queued in the background. Updating details automatically...';
  }
  return 'Discovery processing is active. Updating details automatically...';
}

export default function ScanDetailPage() {
  const { scanId = '' } = useParams<{ scanId: string }>();
  usePageTitle('Scan details');
  const [findingsPage, setFindingsPage] = useState(1);

  const scanQuery = useDiscoveryScan(scanId);
  const scanStatus = scanQuery.data?.status;

  const summaryQuery = useDiscoveryScanSummary(scanId, scanStatus);
  const reportQuery = useDiscoveryScanReport(scanId, scanStatus);
  const documentsQuery = useDiscoveryScanDocuments(scanId, scanStatus);
  const findingsQuery = useDiscoveryScanFindings(scanId, findingsPage, FINDINGS_PAGE_SIZE, scanStatus);

  if (scanQuery.isPending) {
    return <LoadingState />;
  }

  if (scanQuery.isError) {
    return (
      <ErrorState
        onRetry={() => {
          void scanQuery.refetch();
          void summaryQuery.refetch();
          void reportQuery.refetch();
          void documentsQuery.refetch();
          void findingsQuery.refetch();
        }}
        isRetrying={scanQuery.isFetching}
      />
    );
  }

  const scan = scanQuery.data;
  if (!scan) {
    return <EmptyState />;
  }

  const isScanActive = scan.status === 'PENDING' || scan.status === 'RUNNING';
  const lifecycleMessage = formatLifecycleMessage(
    scan.status,
    scan.lifecycle_state,
    scan.recovered_from_stale,
    scan.processing_outcome_message,
    scan.background_job_message,
  );
  const activeBannerMessage = formatActiveBannerMessage(scan.background_job_state);

  return (
    <div className="scan-detail">
      {/* 1. High-level Scan Info Header */}
      <header className="overview-header">
        <p className="eyebrow">Discovery scan</p>
        <h1>Scan {scan.scan_id}</h1>
        <p>
          Detailed processing records, document status, and privacy-safe findings for this scan. Results surface items
          worth checking, but do not confirm account ownership or completeness.
        </p>
      </header>

      {/* 2. Status & Timeline Section */}
      <section className="scan-detail-card" aria-labelledby="status-timeline-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Scan status</p>
            <h2 id="status-timeline-title">Processing timeline</h2>
          </div>
          <StatusBadge status={scan.status} />
        </div>

        {isScanActive ? (
          <div className="active-scan-banner" role="status" aria-live="polite">
            <span className="spinner-dot" aria-hidden="true">●</span>
            <span>{activeBannerMessage}</span>
          </div>
        ) : null}

        <div className="trust-note" aria-live="polite">
          <p>
            <strong>Lifecycle:</strong> {lifecycleMessage}
          </p>
          <p>
            <strong>Background job:</strong> {scan.background_job_state}
          </p>
          {scan.retry_count > 0 ? (
            <p>
              <strong>Retries:</strong> {scan.retry_count}
            </p>
          ) : null}
          {scan.failure_count > 0 ? (
            <p>
              <strong>Failures:</strong> {scan.failure_count}
            </p>
          ) : null}
          {scan.last_failure_at ? (
            <p>
              <strong>Last failure:</strong> {formatTimestamp(scan.last_failure_at)}
            </p>
          ) : null}
        </div>

        {scan.recovered_from_stale ? (
          <div className="trust-note" aria-live="polite">
            <p>
              <strong>Recovery notice:</strong>{' '}
              {scan.status === 'COMPLETE' || scan.status === 'COMPLETED_WITH_WARNINGS'
                ? 'Recovered and completed'
                : 'Recovered from a stale running state'}
            </p>
            {scan.recovered_at ? (
              <p>
                <strong>Recovered at:</strong> {formatTimestamp(scan.recovered_at)}
              </p>
            ) : null}
          </div>
        ) : null}

        <dl className="timeline-grid">
          <div>
            <dt>Scan ID</dt>
            <dd className="resource-id">{scan.scan_id}</dd>
          </div>
          <div>
            <dt>Created</dt>
            <dd>{formatTimestamp(scan.created_at)}</dd>
          </div>
          <div>
            <dt>Completed</dt>
            <dd>{formatTimestamp(scan.completed_at)}</dd>
          </div>
          <div>
            <dt>Documents tracked</dt>
            <dd>{scan.documents_processed}</dd>
          </div>
        </dl>
      </section>

      {/* 3. Summary Section */}
      {summaryQuery.data ? (
        <section className="scan-detail-card" aria-labelledby="scan-summary-title">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Scan breakdown</p>
              <h2 id="scan-summary-title">Findings summary</h2>
            </div>
            <span className="total-badge">{summaryQuery.data.total_findings} total findings</span>
          </div>

          <div className="summary-grid">
            <div className="summary-card">
              <h3>By category</h3>
              {Object.keys(summaryQuery.data.categories).length === 0 ? (
                <p className="muted-text">No findings by category recorded.</p>
              ) : (
                <dl className="summary-list">
                  {Object.entries(summaryQuery.data.categories).map(([cat, count]) => (
                    <div key={cat} className="summary-row">
                      <dt>{formatCategory(cat)}</dt>
                      <dd>{count}</dd>
                    </div>
                  ))}
                </dl>
              )}
            </div>

            <div className="summary-card">
              <h3>By review status</h3>
              {Object.keys(summaryQuery.data.review_statuses).length === 0 ? (
                <p className="muted-text">No findings by review status recorded.</p>
              ) : (
                <dl className="summary-list">
                  {Object.entries(summaryQuery.data.review_statuses).map(([statusKey, count]) => (
                    <div key={statusKey} className="summary-row">
                      <dt>{formatCategory(statusKey)}</dt>
                      <dd>{count}</dd>
                    </div>
                  ))}
                </dl>
              )}
            </div>
          </div>

          <div className="trust-note">
            <p>
              <strong>Trust & Privacy Notice:</strong> Signal strength indicators are rule-based detection cues. They
              do not guarantee asset existence or ownership. Structured human review is required before taking any action.
            </p>
          </div>
        </section>
      ) : null}

      {/* 4. Privacy-Safe Report Section */}
      {reportQuery.data ? (
        <section className="scan-detail-card" aria-labelledby="safe-report-title">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Privacy-safe contract</p>
              <h2 id="safe-report-title">Scan report summary</h2>
            </div>
          </div>
          <p className="report-copy">
            This report summarizes high-level counts without storing or displaying unencrypted document content, raw text,
            storage locations, or matched keyword evidence.
          </p>
          <dl className="report-metrics-grid">
            <div>
              <dt>Status</dt>
              <dd><StatusBadge status={reportQuery.data.status} /></dd>
            </div>
            <div>
              <dt>Total findings</dt>
              <dd>{reportQuery.data.total_findings}</dd>
            </div>
            <div>
              <dt>Documents processed</dt>
              <dd>{reportQuery.data.documents_processed}</dd>
            </div>
            <div>
              <dt>Completed timestamp</dt>
              <dd>{formatTimestamp(reportQuery.data.completed_at)}</dd>
            </div>
          </dl>
        </section>
      ) : null}

      {/* 5. Document Processing Section */}
      <section className="scan-detail-card" aria-labelledby="document-tracking-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Document tracking</p>
            <h2 id="document-tracking-title">Processed documents</h2>
          </div>
          {documentsQuery.data ? <span className="scan-count">{documentsQuery.data.length} documents</span> : null}
        </div>

        {documentsQuery.isPending ? (
          <p className="muted-text">Loading document tracking details…</p>
        ) : documentsQuery.data && documentsQuery.data.length > 0 ? (
          <ul className="document-list">
            {documentsQuery.data.map((doc) => {
              const warningLabel = formatDocumentWarning(doc.warning_code);
              return (
                <li key={doc.document_id} className="document-item">
                  <div className="document-main">
                    <strong>{doc.document_name}</strong>
                    <span className="document-type">{doc.document_type}</span>
                  </div>
                  <div className="document-status-col">
                    <span className={`doc-status-badge status-${doc.status.toLowerCase()}`}>
                      {formatCategory(doc.status)}
                    </span>
                    {warningLabel ? <span className="warning-pill">{warningLabel}</span> : null}
                  </div>
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="muted-text">No document tracking records found for this scan.</p>
        )}
      </section>

      {/* 6. Findings Section */}
      <section className="scan-detail-card" aria-labelledby="findings-list-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Evidence findings</p>
            <h2 id="findings-list-title">Findings list</h2>
          </div>
          {findingsQuery.data ? (
            <span className="scan-count">{findingsQuery.data.total_count} findings</span>
          ) : null}
        </div>

        {findingsQuery.isPending ? (
          <p className="muted-text">Loading evidence findings…</p>
        ) : findingsQuery.data && findingsQuery.data.items.length > 0 ? (
          <>
            <ul className="findings-list">
              {findingsQuery.data.items.map((finding) => (
                <li key={finding.finding_id} className="finding-item">
                  <div className="finding-main">
                    <strong>{formatCategory(finding.category)}</strong>
                    <span className="finding-id">ID: {finding.finding_id}</span>
                  </div>
                  <div className="finding-meta">
                    <span className="confidence-signal">
                      Signal strength: {(finding.confidence_score * 100).toFixed(0)}%
                    </span>
                    <span className={`status-badge status-${finding.review_status.toLowerCase()}`}>
                      {formatReviewStatus(finding.review_status)}
                    </span>
                  </div>
                </li>
              ))}
            </ul>

            {findingsQuery.data.total_pages > 1 ? (
              <nav className="pagination" aria-label="Scan findings pages">
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => setFindingsPage((prev) => prev - 1)}
                  disabled={findingsPage <= 1 || findingsQuery.isFetching}
                >
                  Previous
                </button>
                <span aria-live="polite">
                  Page {findingsQuery.data.page} of {findingsQuery.data.total_pages}
                </span>
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => setFindingsPage((prev) => prev + 1)}
                  disabled={findingsPage >= findingsQuery.data.total_pages || findingsQuery.isFetching}
                >
                  Next
                </button>
              </nav>
            ) : null}
          </>
        ) : (
          <p className="muted-text">No findings recorded for this scan.</p>
        )}
      </section>

      <footer className="scan-detail-footer">
        <Link className="text-link" to="/discovery/scans">
          ← Back to Scan history
        </Link>
      </footer>
    </div>
  );
}
