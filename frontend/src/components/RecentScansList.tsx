import React from 'react';
import { Link } from 'react-router-dom';
import type { DiscoveryScanSummary } from '../types/discovery';
import StatusBadge from './StatusBadge';

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: 'medium',
  timeStyle: 'short',
});

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Date unavailable' : dateFormatter.format(date);
}

export default function RecentScansList({ scans }: { scans: DiscoveryScanSummary[] }) {
  return (
    <section className="recent-scans" aria-labelledby="recent-scans-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Latest activity</p>
          <h2 id="recent-scans-title">Recent scans</h2>
        </div>
        <Link className="text-link" to="/discovery/scans">View scan history</Link>
      </div>
      <ul className="recent-scan-list">
        {scans.map((scan) => (
          <li key={scan.scan_id}>
            <Link className="recent-scan-link" to={`/discovery/scans/${encodeURIComponent(scan.scan_id)}`}>
              <span className="recent-scan-main">
                <strong>Scan from {formatDate(scan.created_at)}</strong>
                <span>{scan.documents_processed.toLocaleString()} documents processed</span>
              </span>
              <StatusBadge status={scan.status} />
              <span className="link-direction" aria-hidden="true">View →</span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
