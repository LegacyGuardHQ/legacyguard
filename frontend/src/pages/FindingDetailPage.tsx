import React from 'react';
import { useParams } from 'react-router-dom';
import PagePlaceholder from '../components/PagePlaceholder';
import { usePageTitle } from '../hooks/usePageTitle';

export default function FindingDetailPage() {
  const { findingId } = useParams<{ findingId: string }>();
  usePageTitle('Finding details');
  return (
    <PagePlaceholder
      eyebrow="Discovery finding"
      title="Finding details"
      description="Safe finding context and review actions will be implemented in a later Phase 4 increment."
      resourceId={findingId}
    />
  );
}
