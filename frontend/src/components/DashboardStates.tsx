import React from 'react';

type LoadingStateProps = {
  message?: string;
  description?: string;
  fullPage?: boolean;
};

/**
 * LoadingState Component
 *
 * Displays a branded loading state with animated spinner.
 * Provides aria-live updates for assistive technology.
 *
 * @param message - Primary loading message
 * @param description - Secondary descriptive text
 * @param fullPage - Whether this is full-page or section-level loading
 */
export function LoadingState({
  message = 'Securely loading your discovery activity.',
  description = "We're preparing your private activity summary.",
  fullPage = true,
}: LoadingStateProps) {
  return (
    <section
      className={`dashboard-state ${!fullPage ? 'section-loading' : ''}`}
      aria-live="polite"
      aria-busy="true"
      role="status"
    >
      <span className="loading-spinner" aria-hidden="true" />
      <h2>{message}</h2>
      <p>{description}</p>
    </section>
  );
}

type EmptyStateProps = {
  title?: string;
  description?: string;
  icon?: React.ReactNode;
  action?: {
    label: string;
    href?: string;
    onClick?: () => void;
  };
};

/**
 * EmptyState Component
 *
 * Displays a friendly empty state when no data is available.
 * Guides users toward next actions with CTA buttons or links.
 *
 * @param title - Main heading for empty state
 * @param description - Explanation of why nothing is shown
 * @param icon - Optional icon or illustration
 * @param action - Optional CTA button/link
 */
export function EmptyState({
  title = 'No discovery activity yet',
  description = 'Activity will appear here after supported documents are uploaded and discovery processing completes. There is nothing to review on this page right now.',
  icon,
  action,
}: EmptyStateProps) {
  return (
    <section
      className="dashboard-state"
      aria-labelledby="empty-state-title"
    >
      <span className="state-symbol" aria-hidden="true">
        {icon || '○'}
      </span>
      <h2 id="empty-state-title">{title}</h2>
      <p>{description}</p>
      {action && (
        <div style={{ marginTop: '24px' }}>
          {action.href ? (
            <a href={action.href} className="primary-button">
              {action.label}
            </a>
          ) : (
            <button className="primary-button" onClick={action.onClick}>
              {action.label}
            </button>
          )}
        </div>
      )}
    </section>
  );
}

type ErrorStateProps = {
  onRetry: () => void;
  isRetrying: boolean;
  title?: string;
  message?: string;
  errorCode?: string | number;
  supportLink?: string;
  showDetails?: boolean;
};

/**
 * ErrorState Component
 *
 * Displays an error state with recovery options.
 * Provides clear messaging and support resources.
 *
 * @param onRetry - Callback function to retry the failed action
 * @param isRetrying - Whether retry is currently in progress
 * @param title - Error title
 * @param message - Error description
 * @param errorCode - Error code for support reference
 * @param supportLink - Link to support or help documentation
 * @param showDetails - Whether to show error code and diagnostic info
 */
export function ErrorState({
  onRetry,
  isRetrying,
  title = "We couldn't load your discovery activity.",
  message = 'Check your connection and try again. Your saved information has not been changed.',
  errorCode,
  supportLink,
  showDetails = false,
}: ErrorStateProps) {
  return (
    <section
      className="dashboard-state dashboard-error"
      role="alert"
      aria-live="assertive"
    >
      <span className="state-symbol" aria-hidden="true">!</span>
      <h2>{title}</h2>
      <p>{message}</p>

      <div style={{ marginTop: '24px', display: 'flex', gap: '12px', flexWrap: 'wrap', justifyContent: 'center' }}>
        <button
          className="primary-button"
          type="button"
          onClick={onRetry}
          disabled={isRetrying}
          aria-busy={isRetrying}
        >
          {isRetrying ? 'Retrying…' : 'Try again'}
        </button>

        {supportLink && (
          <a
            href={supportLink}
            className="secondary-button"
            target="_blank"
            rel="noopener noreferrer"
          >
            Contact support
          </a>
        )}
      </div>

      {errorCode && showDetails && (
        <div
          style={{
            marginTop: '16px',
            padding: '12px',
            background: 'rgba(0, 0, 0, 0.2)',
            borderRadius: '8px',
            fontSize: '12px',
            fontFamily: 'monospace',
            color: 'var(--color-text-tertiary)',
          }}
        >
          Error code: {errorCode}
        </div>
      )}
    </section>
  );
}

/**
 * SectionLoadingState Component
 *
 * Minimal loading indicator for individual sections/cards.
 * Used when loading specific parts of a page, not the whole page.
 *
 * @param label - What is being loaded (e.g., "document tracking details")
 */
export function SectionLoadingState({ label }: { label: string }) {
  return (
    <p className="muted-text loading-section" role="status" aria-live="polite">
      <span className="loading-spinner-inline" aria-hidden="true" />
      Loading {label}…
    </p>
  );
}
