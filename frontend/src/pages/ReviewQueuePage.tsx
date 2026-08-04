import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useDiscoveryReviewQueue, useUpdateFindingStatus } from '../hooks/useDiscoveryReviewQueue';
import { usePageTitle } from '../hooks/usePageTitle';
import type { DiscoveryReviewStatus } from '../types/discovery';

const PAGE_SIZE = 10;
const REVIEW_PANEL_ID = 'review-queue-panel';

const REVIEW_TABS: ReadonlyArray<{
  status: DiscoveryReviewStatus;
  label: string;
  id: string;
}> = [
  { status: 'PENDING_REVIEW', label: 'Pending Review', id: 'review-tab-pending' },
  { status: 'CONFIRMED', label: 'Confirmed', id: 'review-tab-confirmed' },
  { status: 'DISMISSED', label: 'Dismissed', id: 'review-tab-dismissed' },
];

function formatCategory(category: string): string {
  return category
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
}

export default function ReviewQueuePage() {
  usePageTitle('Review queue');
  const [activeTab, setActiveTab] = useState<DiscoveryReviewStatus>('PENDING_REVIEW');
  const [page, setPage] = useState(1);

  const scansQuery = useDiscoveryReviewQueue(page, PAGE_SIZE, activeTab);
  const updateMutation = useUpdateFindingStatus();
  const activeTabConfig = REVIEW_TABS.find((tab) => tab.status === activeTab) ?? REVIEW_TABS[0];

  const handleTabChange = (status: DiscoveryReviewStatus) => {
    updateMutation.reset();
    setActiveTab(status);
    setPage(1);
  };

  const handleTabKeyDown = (
    event: React.KeyboardEvent<HTMLButtonElement>,
    currentStatus: DiscoveryReviewStatus
  ) => {
    const currentIndex = REVIEW_TABS.findIndex((tab) => tab.status === currentStatus);
    let nextIndex: number | null = null;

    if (event.key === 'ArrowRight') nextIndex = (currentIndex + 1) % REVIEW_TABS.length;
    if (event.key === 'ArrowLeft') nextIndex = (currentIndex - 1 + REVIEW_TABS.length) % REVIEW_TABS.length;
    if (event.key === 'Home') nextIndex = 0;
    if (event.key === 'End') nextIndex = REVIEW_TABS.length - 1;

    if (nextIndex === null) return;

    event.preventDefault();
    const nextTab = REVIEW_TABS[nextIndex];
    handleTabChange(nextTab.status);
    document.getElementById(nextTab.id)?.focus();
  };

  const handleUpdateStatus = (findingId: string, newStatus: DiscoveryReviewStatus) => {
    updateMutation.reset();
    updateMutation.mutate({ findingId, reviewStatus: newStatus });
  };

  const handlePageChange = (nextPage: number) => {
    updateMutation.reset();
    setPage(nextPage);
  };

  const totalPages = scansQuery.data?.total_pages || 1;
  const items = scansQuery.data?.items || [];
  const totalCount = scansQuery.data?.total_count || 0;

  return (
    <main className="dashboard-container">
      <header className="page-header">
        <span className="eyebrow">Discovery</span>
        <h1 className="page-title">Review queue</h1>
        <p className="page-description">
          Review automated rule-engine discovery findings. Inspect signal strength and update status to confirm or dismiss findings.
        </p>
      </header>

      <div className="filter-row">
        <div className="tab-nav" role="tablist" aria-label="Review status filters">
          {REVIEW_TABS.map((tab) => (
            <button
              key={tab.status}
              id={tab.id}
              type="button"
              className={`tab-button ${activeTab === tab.status ? 'active' : ''}`}
              onClick={() => handleTabChange(tab.status)}
              onKeyDown={(event) => handleTabKeyDown(event, tab.status)}
              aria-controls={REVIEW_PANEL_ID}
              aria-selected={activeTab === tab.status}
              role="tab"
              tabIndex={activeTab === tab.status ? 0 : -1}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <section
        id={REVIEW_PANEL_ID}
        className="review-tab-panel"
        role="tabpanel"
        aria-labelledby={activeTabConfig.id}
        aria-busy={scansQuery.isPending || scansQuery.isFetching || updateMutation.isPending}
        tabIndex={0}
      >
        {updateMutation.isError && (
          <div className="card mutation-error" role="alert">
            Unable to update this finding. Please try again.
          </div>
        )}

        {scansQuery.isPending && (
          <div className="card loading-card" role="status" aria-live="polite">
            <div className="loading-spinner" aria-hidden="true" />
            <p>Loading discovery review queue...</p>
          </div>
        )}

        {scansQuery.isError && (
          <div className="card error-card" role="alert">
            <h3>Unable to load the review queue</h3>
            <p>Please try again. Your saved findings have not been changed.</p>
            <button type="button" className="btn btn-secondary" onClick={() => scansQuery.refetch()}>
              Retry
            </button>
          </div>
        )}

        {!scansQuery.isPending && !scansQuery.isError && (
          <>
            {items.length === 0 ? (
              <div className="card empty-card">
                <h3>No findings found</h3>
                <p>
                  {activeTab === 'PENDING_REVIEW' && 'There are no findings currently awaiting review.'}
                  {activeTab === 'CONFIRMED' && 'No findings have been confirmed yet.'}
                  {activeTab === 'DISMISSED' && 'No findings have been dismissed.'}
                </p>
              </div>
            ) : (
              <div className="queue-list" role="feed" aria-label={`${activeTabConfig.label} findings`}>
                {items.map((finding) => (
                  <article key={finding.finding_id} className="card queue-item-card">
                    <div className="queue-item-header">
                      <div>
                        <span className="badge category-badge">{formatCategory(finding.category)}</span>
                        <span className="date-text">
                          Detected: {new Date(finding.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      <Link to={`/discovery/findings/${finding.finding_id}`} className="btn-link">
                        View finding details &rarr;
                      </Link>
                    </div>

                    <div className="signal-strength-box">
                      <div className="signal-header">
                        <span className="signal-label">Detection confidence signal strength:</span>
                        <strong className="signal-score">{finding.confidence_score.toFixed(0)}%</strong>
                      </div>
                      <p className="signal-explanation">
                        Rule-based detection signal strength. It is not certainty, account ownership determination, financial verification, or proof of ownership.
                      </p>
                    </div>

                    <div className="queue-action-toolbar">
                      <span className="current-status-label">
                        Status: <strong>{activeTabConfig.label}</strong>
                      </span>

                      <div className="action-buttons">
                        {activeTab === 'PENDING_REVIEW' && (
                          <>
                            <button
                              type="button"
                              className="btn btn-success"
                              onClick={() => handleUpdateStatus(finding.finding_id, 'CONFIRMED')}
                              disabled={updateMutation.isPending}
                            >
                              Confirm
                            </button>
                            <button
                              type="button"
                              className="btn btn-danger"
                              onClick={() => handleUpdateStatus(finding.finding_id, 'DISMISSED')}
                              disabled={updateMutation.isPending}
                            >
                              Dismiss
                            </button>
                          </>
                        )}

                        {activeTab === 'CONFIRMED' && (
                          <>
                            <button
                              type="button"
                              className="btn btn-secondary"
                              onClick={() => handleUpdateStatus(finding.finding_id, 'PENDING_REVIEW')}
                              disabled={updateMutation.isPending}
                            >
                              Reopen
                            </button>
                            <button
                              type="button"
                              className="btn btn-danger"
                              onClick={() => handleUpdateStatus(finding.finding_id, 'DISMISSED')}
                              disabled={updateMutation.isPending}
                            >
                              Dismiss
                            </button>
                            <span className="disabled-action-label" title="Manual asset creation will be implemented in Phase 4B.7">
                              Asset creation (Phase 4B.7)
                            </span>
                          </>
                        )}

                        {activeTab === 'DISMISSED' && (
                          <>
                            <button
                              type="button"
                              className="btn btn-secondary"
                              onClick={() => handleUpdateStatus(finding.finding_id, 'PENDING_REVIEW')}
                              disabled={updateMutation.isPending}
                            >
                              Reopen
                            </button>
                            <button
                              type="button"
                              className="btn btn-success"
                              onClick={() => handleUpdateStatus(finding.finding_id, 'CONFIRMED')}
                              disabled={updateMutation.isPending}
                            >
                              Confirm
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            )}

            {totalPages > 1 && (
              <nav className="pagination-container" aria-label="Review queue pagination">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => handlePageChange(Math.max(page - 1, 1))}
                  disabled={page === 1 || scansQuery.isFetching}
                >
                  Previous
                </button>
                <span className="pagination-info">
                  Page {page} of {totalPages} ({totalCount} items)
                </span>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => handlePageChange(Math.min(page + 1, totalPages))}
                  disabled={page >= totalPages || scansQuery.isFetching}
                >
                  Next
                </button>
              </nav>
            )}
          </>
        )}
      </section>
    </main>
  );
}
