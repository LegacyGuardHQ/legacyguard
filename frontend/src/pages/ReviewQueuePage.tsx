import React from 'react';
import PagePlaceholder from '../components/PagePlaceholder';
import { usePageTitle } from '../hooks/usePageTitle';

export default function ReviewQueuePage() {
  usePageTitle('Needs review');
  return (
    <PagePlaceholder
      eyebrow="Discovery"
      title="Needs review"
      description="The findings review queue will be implemented in a later Phase 4 increment."
    />
  );
}
