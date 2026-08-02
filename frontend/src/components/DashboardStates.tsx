import React from 'react';

export function LoadingState() {
  return (
    <section className="dashboard-state" aria-live="polite" aria-busy="true">
      <span className="state-symbol" aria-hidden="true">◌</span>
      <h2>Securely loading your discovery activity.</h2>
      <p>We’re preparing your private activity summary.</p>
    </section>
  );
}

export function EmptyState() {
  return (
    <section className="dashboard-state" aria-labelledby="empty-dashboard-title">
      <span className="state-symbol" aria-hidden="true">○</span>
      <h2 id="empty-dashboard-title">No discovery activity yet</h2>
      <p>
        Activity will appear here after supported documents are uploaded and discovery processing completes.
        There is nothing to review on this page right now.
      </p>
    </section>
  );
}

type ErrorStateProps = {
  onRetry: () => void;
  isRetrying: boolean;
};

export function ErrorState({ onRetry, isRetrying }: ErrorStateProps) {
  return (
    <section className="dashboard-state dashboard-error" role="alert">
      <span className="state-symbol" aria-hidden="true">!</span>
      <h2>We couldn’t load your discovery activity.</h2>
      <p>Check your connection and try again. Your saved information has not been changed.</p>
      <button className="secondary-button" type="button" onClick={onRetry} disabled={isRetrying}>
        {isRetrying ? 'Trying again…' : 'Try again'}
      </button>
    </section>
  );
}
