import React from 'react';
import PagePlaceholder from '../components/PagePlaceholder';
import { usePageTitle } from '../hooks/usePageTitle';

export default function DiscoveryOverviewPage() {
  usePageTitle('Discovery overview');
  return (
    <PagePlaceholder
      eyebrow="Discovery"
      title="Discovery overview"
      description="Dashboard metrics and recent discovery activity will be implemented in Phase 4B."
    />
  );
}
