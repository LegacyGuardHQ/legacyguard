import React from 'react';

type SkeletonLoaderProps = {
  variant: 'page' | 'card' | 'list' | 'metric' | 'scan-detail';
  count?: number;
};

/**
 * SkeletonLoader Component
 *
 * Displays a skeleton/shimmer placeholder that matches the structure of content
 * being loaded. Improves perceived performance vs. spinners.
 *
 * @param variant - Type of skeleton to display
 * @param count - Number of items to show (for list variant)
 *
 * @example
 * // Full page skeleton
 * <SkeletonLoader variant="page" />
 *
 * // List with 3 items
 * <SkeletonLoader variant="list" count={3} />
 */
export default function SkeletonLoader({ variant, count = 1 }: SkeletonLoaderProps) {
  switch (variant) {
    case 'page':
      return <PageSkeleton />;
    case 'card':
      return <CardSkeleton />;
    case 'list':
      return <ListSkeleton count={count} />;
    case 'metric':
      return <MetricSkeleton />;
    case 'scan-detail':
      return <ScanDetailSkeleton />;
    default:
      return <CardSkeleton />;
  }
}

/**
 * Full page skeleton with header and content area
 * Used for: Dashboard overview, scan history pages
 */
function PageSkeleton() {
  return (
    <div className="skeleton-loader">
      {/* Header Section */}
      <header className="overview-header" style={{ pointerEvents: 'none' }}>
        <div>
          <div className="skeleton-element skeleton-line" style={{ width: '100px', marginBottom: '12px' }} />
          <div className="skeleton-element skeleton-line" style={{ width: '300px', height: '32px', marginBottom: '16px' }} />
          <div className="skeleton-element skeleton-line" style={{ width: '100%', maxWidth: '600px', height: '16px', marginBottom: '8px' }} />
          <div className="skeleton-element skeleton-line" style={{ width: '90%', maxWidth: '600px', height: '16px' }} />
        </div>
      </header>

      {/* Content Cards */}
      <div className="summary-grid">
        <CardSkeleton />
        <CardSkeleton />
      </div>

      {/* List Section */}
      <ListSkeleton count={3} />
    </div>
  );
}

/**
 * Single card skeleton with shimmer effect
 * Used for: Metric cards, module cards, individual content cards
 */
function CardSkeleton() {
  return (
    <div className="skeleton-loader" style={{ padding: '24px' }}>
      <div className="skeleton-element skeleton-line" style={{ width: '80px', marginBottom: '16px' }} />
      <div className="skeleton-element skeleton-line" style={{ width: '100%', height: '24px', marginBottom: '16px' }} />
      <div className="skeleton-element skeleton-line" style={{ width: '100%', height: '16px', marginBottom: '8px' }} />
      <div className="skeleton-element skeleton-line" style={{ width: '80%', height: '16px' }} />
    </div>
  );
}

/**
 * List skeleton with multiple items
 * Used for: Scan history, findings list, document tracking
 */
function ListSkeleton({ count }: { count: number }) {
  return (
    <div className="skeleton-loader" style={{ gap: '12px' }}>
      {Array.from({ length: count }).map((_, idx) => (
        <div
          key={idx}
          className="skeleton-element"
          style={{
            height: '72px',
            borderRadius: '12px',
            animation: `shimmer 2s infinite`,
            animationDelay: `${idx * 0.1}s`,
          }}
        />
      ))}
    </div>
  );
}

/**
 * Metric card skeleton
 * Used for: Dashboard metrics display
 */
function MetricSkeleton() {
  return (
    <div className="skeleton-loader" style={{ textAlign: 'center', padding: '24px', gap: '12px' }}>
      <div className="skeleton-element skeleton-line" style={{ width: '100px', height: '12px', margin: '0 auto', marginBottom: '12px' }} />
      <div className="skeleton-element skeleton-line" style={{ width: '80px', height: '32px', margin: '0 auto', marginBottom: '12px' }} />
      <div className="skeleton-element skeleton-line" style={{ width: '150px', height: '12px', margin: '0 auto' }} />
    </div>
  );
}

/**
 * Scan detail page skeleton
 * Used for: Complex scan detail pages with multiple sections
 */
function ScanDetailSkeleton() {
  return (
    <div className="skeleton-loader">
      {/* Header */}
      <header className="overview-header" style={{ pointerEvents: 'none', marginBottom: '24px' }}>
        <div>
          <div className="skeleton-element skeleton-line" style={{ width: '100px', marginBottom: '12px' }} />
          <div className="skeleton-element skeleton-line" style={{ width: '250px', height: '32px', marginBottom: '16px' }} />
          <div className="skeleton-element skeleton-line" style={{ width: '100%', maxWidth: '600px', height: '16px' }} />
        </div>
      </header>

      {/* Timeline/Status Section */}
      <div className="skeleton-element" style={{ height: '200px', borderRadius: '12px', marginBottom: '24px' }} />

      {/* Summary Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px', marginBottom: '24px' }}>
        <div className="skeleton-element" style={{ height: '120px', borderRadius: '12px' }} />
        <div className="skeleton-element" style={{ height: '120px', borderRadius: '12px' }} />
      </div>

      {/* Documents Section */}
      <div className="skeleton-element" style={{ height: '150px', borderRadius: '12px', marginBottom: '24px' }} />

      {/* Findings Section */}
      <div style={{ display: 'grid', gap: '12px' }}>
        {[1, 2, 3].map((idx) => (
          <div
            key={idx}
            className="skeleton-element"
            style={{
              height: '64px',
              borderRadius: '12px',
              animation: `shimmer 2s infinite`,
              animationDelay: `${idx * 0.1}s`,
            }}
          />
        ))}
      </div>
    </div>
  );
}
