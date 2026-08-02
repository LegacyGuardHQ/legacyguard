import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { EmptyState, ErrorState, LoadingState } from '../components/DashboardStates';
import StatusBadge from '../components/StatusBadge';
import { useDiscoveryScans } from '../hooks/useDiscoveryScans';
import { usePageTitle } from '../hooks/usePageTitle';

const PAGE_SIZE = 10;

function formatTimestamp(value: string | null) {
  if (!value) return 'Not completed';
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
}

export default function ScanHistoryPage() {
  usePageTitle('Scan history');
  const [page, setPage] = useState(1);
  const scansQuery = useDiscoveryScans(page, PAGE_SIZE);

  return (
    <div className="scan-history">
      <header className="overview-header">
        <p className="eyebrow">Discovery</p>
        <h1>Scan history</h1>
        <p>Review the processing record for your discovery scans. Results can surface items worth checking, but they do not confirm ownership or completeness.</p>
      </header>
      {scansQuery.isPending ? <LoadingState /> : null}
      {scansQuery.isError ? <ErrorState onRetry={() => void scansQuery.refetch()} isRetrying={scansQuery.isFetching} /> : null}
      {scansQuery.data?.total_count === 0 ? <EmptyState /> : null}
      {scansQuery.data && scansQuery.data.total_count > 0 ? (
        <section className="scan-history-panel" aria-labelledby="scan-history-list-title">
          <div className="section-heading">
            <div><p className="eyebrow">Processing record</p><h2 id="scan-history-list-title">Your scans</h2></div>
            <p className="scan-count">{scansQuery.data.total_count} total</p>
          </div>
          <ul className="scan-history-list">
            {scansQuery.data.items.map((scan) => (
              <li key={scan.scan_id}>
                <Link className="scan-history-link" to={`/discovery/scans/${encodeURIComponent(scan.scan_id)}`}>
                  <div className="scan-history-primary"><strong>Scan {scan.scan_id}</strong><span>Created {formatTimestamp(scan.created_at)}</span></div>
                  <StatusBadge status={scan.status} />
                  <dl className="scan-history-details">
                    <div><dt>Documents processed</dt><dd>{scan.documents_processed}</dd></div>
                    <div><dt>Completed</dt><dd>{formatTimestamp(scan.completed_at)}</dd></div>
                  </dl>
                  <span className="link-direction">View scan details →</span>
                </Link>
              </li>
            ))}
          </ul>
          <nav className="pagination" aria-label="Scan history pages">
            <button className="secondary-button" type="button" onClick={() => setPage((value) => value - 1)} disabled={page <= 1 || scansQuery.isFetching}>Previous</button>
            <span aria-live="polite">Page {scansQuery.data.page} of {scansQuery.data.total_pages}</span>
            <button className="secondary-button" type="button" onClick={() => setPage((value) => value + 1)} disabled={page >= scansQuery.data.total_pages || scansQuery.isFetching}>Next</button>
          </nav>
        </section>
      ) : null}
    </div>
  );
}
