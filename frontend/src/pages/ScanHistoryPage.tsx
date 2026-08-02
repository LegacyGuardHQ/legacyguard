import React from 'react';
import PagePlaceholder from '../components/PagePlaceholder';
import { usePageTitle } from '../hooks/usePageTitle';

export default function ScanHistoryPage() {
  usePageTitle('Scan history');
  return (
    <PagePlaceholder
      eyebrow="Discovery"
      title="Scan history"
      description="Paginated scan history will be implemented in a later Phase 4 increment."
    />
  );
}
