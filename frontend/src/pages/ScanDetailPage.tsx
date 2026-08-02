import React from 'react';
import { useParams } from 'react-router-dom';
import PagePlaceholder from '../components/PagePlaceholder';
import { usePageTitle } from '../hooks/usePageTitle';

export default function ScanDetailPage() {
  const { scanId } = useParams<{ scanId: string }>();
  usePageTitle('Scan details');
  return (
    <PagePlaceholder
      eyebrow="Discovery scan"
      title="Scan details"
      description="Status, report, document tracking, and findings will be implemented in later Phase 4 increments."
      resourceId={scanId}
    />
  );
}
