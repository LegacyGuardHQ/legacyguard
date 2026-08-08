import React from 'react';
import { Link } from 'react-router-dom';
import { EmptyState, ErrorState, LoadingState } from '../components/DashboardStates';
import MetricCard from '../components/MetricCard';
import RecentScansList from '../components/RecentScansList';
import SummaryList, { type SummaryItem } from '../components/SummaryList';
import { scanStatusLabels } from '../components/StatusBadge';
import { usePageTitle } from '../hooks/usePageTitle';
import { useDiscoveryDashboard } from '../hooks/useDiscoveryDashboard';
import type { DiscoveryReviewStatus, DiscoveryScanStatus } from '../types/discovery';

const scanStatusOrder: DiscoveryScanStatus[] = [
  'PENDING',
  'RUNNING',
  'COMPLETE',
  'COMPLETED_WITH_WARNINGS',
  'FAILED',
];

const scanStatusDescriptions: Record<DiscoveryScanStatus, string> = {
  PENDING: 'Queued and waiting to start.',
  RUNNING: 'Discovery processing is underway.',
  COMPLETE: 'Processing finished without recorded warnings.',
  COMPLETED_WITH_WARNINGS: 'Processing finished with items to note.',
  FAILED: 'Processing could not be completed.',
};

const reviewStatusOrder: DiscoveryReviewStatus[] = ['PENDING_REVIEW', 'CONFIRMED', 'DISMISSED'];

const reviewStatusLabels: Record<DiscoveryReviewStatus, string> = {
  PENDING_REVIEW: 'Needs review',
  CONFIRMED: 'Confirmed',
  DISMISSED: 'Dismissed',
};

const reviewStatusDescriptions: Record<DiscoveryReviewStatus, string> = {
  PENDING_REVIEW: 'Still needs your review and should not be treated as confirmed.',
  CONFIRMED: 'Reviewed and confirmed as a signal, not as proof.',
  DISMISSED: 'Set aside for now and can be reopened later.',
};

function formatCategoryLabel(category: string): string {
  return category
    .toLowerCase()
    .split('_')
    .filter(Boolean)
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(' ');
}

export default function DiscoveryOverviewPage() {
  usePageTitle('Discovery overview');
  const dashboardQuery = useDiscoveryDashboard();

  let content: React.ReactNode;
  if (dashboardQuery.isPending) {
    content = <LoadingState />;
  } else if (dashboardQuery.isError) {
    content = (
      <ErrorState
        isRetrying={dashboardQuery.isFetching}
        onRetry={() => { void dashboardQuery.refetch(); }}
      />
    );
  } else {
    const dashboard = dashboardQuery.data;
    const isEmpty = dashboard.total_scans === 0
      && dashboard.total_findings === 0
      && dashboard.recent_scans.length === 0;

    if (isEmpty) {
      content = <EmptyState />;
    } else {
      const scanItems: SummaryItem[] = scanStatusOrder.map((status) => ({
        key: status,
        label: scanStatusLabels[status],
        value: dashboard.scans_by_status[status],
        description: scanStatusDescriptions[status],
      }));
      const reviewItems: SummaryItem[] = reviewStatusOrder.map((status) => ({
        key: status,
        label: reviewStatusLabels[status],
        value: dashboard.findings_by_review_status[status],
        description: reviewStatusDescriptions[status],
      }));
      const categoryItems: SummaryItem[] = Object.entries(dashboard.findings_by_category)
        .map(([category, value]) => ({ key: category, label: formatCategoryLabel(category), value }))
        .sort((left, right) => left.label.localeCompare(right.label));

      content = (
        <>
          <section className="metric-grid" aria-label="Discovery totals">
            <MetricCard
              label="Total scans"
              value={dashboard.total_scans}
              description="Discovery scans recorded for your account."
            />
            <MetricCard
              label="Total findings"
              value={dashboard.total_findings}
              description="Signals identified for human review—not guarantees or verified assets."
            />
            <MetricCard
              label="Needs review"
              value={dashboard.pending_reviews}
              description="Findings waiting for your attention."
            />
          </section>

          {dashboard.pending_reviews > 0 && (
            <aside className="review-guidance" aria-label="Pending review guidance">
              <div>
                <strong>{dashboard.pending_reviews.toLocaleString()} findings need your review</strong>
                <p>Review each signal before treating it as confirmed information.</p>
              </div>
              <Link className="secondary-button action-link" to="/discovery/review">Open review queue</Link>
            </aside>
          )}

          <div className="summary-grid">
            <SummaryList title="Scan status" items={scanItems} />
            <SummaryList title="Review status" items={reviewItems} />
          </div>

          <SummaryList title="Findings by category" items={categoryItems} />
          <RecentScansList scans={dashboard.recent_scans} />
        </>
      );
    }
  }

  return (
    <div className="discovery-overview">
      <header className="overview-header">
        <p className="eyebrow">Discovery</p>
        <h1>Discovery overview</h1>
        <p>
          A private summary of document discovery activity. Findings are signals for your review and do not
          establish ownership, value, or certainty.
        </p>
      </header>
      {content}
    </div>
  );
}
