import React from 'react';
import type { DiscoveryScanStatus } from '../types/discovery';

export const scanStatusLabels: Record<DiscoveryScanStatus, string> = {
  PENDING: 'Queued',
  RUNNING: 'Processing',
  COMPLETE: 'Complete',
  COMPLETED_WITH_WARNINGS: 'Complete with warnings',
  FAILED: 'Failed',
};

export default function StatusBadge({ status }: { status: DiscoveryScanStatus }) {
  return (
    <span className={`status-badge status-${status.toLowerCase()}`}>
      {scanStatusLabels[status]}
    </span>
  );
}
