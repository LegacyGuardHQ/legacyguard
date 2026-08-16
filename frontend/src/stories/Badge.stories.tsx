import type { Meta, StoryObj } from '@storybook/react';

const meta = {
  title: 'Components/Badge',
  tags: ['autodocs'],
  parameters: {
    layout: 'centered',
  },
} satisfies Meta<any>;

export default meta;
type Story = StoryObj<typeof meta>;

/**
 * Status badge showing the current state of a scan or finding.
 */
export const StatusPending: Story = {
  render: () => (
    <span className="status-badge status-pending">
      Pending
    </span>
  ),
};

/**
 * Status badge for running/in-progress operations.
 */
export const StatusRunning: Story = {
  render: () => (
    <span className="status-badge status-running">
      Running
    </span>
  ),
};

/**
 * Status badge for completed operations.
 */
export const StatusComplete: Story = {
  render: () => (
    <span className="status-badge status-complete">
      Completed
    </span>
  ),
};

/**
 * Status badge for warnings.
 */
export const StatusWarning: Story = {
  render: () => (
    <span className="status-badge status-warning">
      Review Required
    </span>
  ),
};

/**
 * Status badge for errors.
 */
export const StatusError: Story = {
  render: () => (
    <span className="status-badge status-error">
      Failed
    </span>
  ),
};

/**
 * All status badge variants displayed together.
 */
export const AllStatuses: Story = {
  render: () => (
    <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
      <span className="status-badge status-pending">Pending</span>
      <span className="status-badge status-running">Running</span>
      <span className="status-badge status-complete">Completed</span>
      <span className="status-badge status-warning">Review Required</span>
      <span className="status-badge status-error">Failed</span>
    </div>
  ),
};

/**
 * Standard tag/chip badge for categorization.
 */
export const Badge: Story = {
  render: () => (
    <span className="badge">
      Account Verified
    </span>
  ),
};

/**
 * Badge with multiple tags in a group.
 */
export const BadgeGroup: Story = {
  render: () => (
    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
      <span className="badge">Database</span>
      <span className="badge">Legacy</span>
      <span className="badge">Critical</span>
      <span className="badge">Deprecated</span>
    </div>
  ),
};

/**
 * Success badge variant.
 */
export const BadgeSuccess: Story = {
  render: () => (
    <span className="badge badge-success">
      Verified
    </span>
  ),
};

/**
 * Error badge variant.
 */
export const BadgeError: Story = {
  render: () => (
    <span className="badge badge-error">
      Invalid
    </span>
  ),
};

/**
 * Warning badge variant.
 */
export const BadgeWarning: Story = {
  render: () => (
    <span className="badge badge-warning">
      Attention
    </span>
  ),
};

/**
 * All badge variants displayed together for comparison.
 */
export const AllBadges: Story = {
  render: () => (
    <div style={{ display: 'grid', gap: '1.5rem' }}>
      <div>
        <h4 style={{ color: '#e8eef8', margin: '0 0 0.75rem 0' }}>Default</h4>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <span className="badge">Tag One</span>
          <span className="badge">Tag Two</span>
          <span className="badge">Tag Three</span>
        </div>
      </div>
      <div>
        <h4 style={{ color: '#e8eef8', margin: '0 0 0.75rem 0' }}>Success</h4>
        <span className="badge badge-success">Success Badge</span>
      </div>
      <div>
        <h4 style={{ color: '#e8eef8', margin: '0 0 0.75rem 0' }}>Error</h4>
        <span className="badge badge-error">Error Badge</span>
      </div>
      <div>
        <h4 style={{ color: '#e8eef8', margin: '0 0 0.75rem 0' }}>Warning</h4>
        <span className="badge badge-warning">Warning Badge</span>
      </div>
    </div>
  ),
};

/**
 * Alert/message badge for errors.
 */
export const AlertError: Story = {
  render: () => (
    <div className="alert alert-error" role="alert" style={{ maxWidth: '500px' }}>
      <div className="alert-icon">⚠️</div>
      <div className="alert-content">
        <h4>Processing Failed</h4>
        <p>Unable to process document. Please check the file format and try again.</p>
      </div>
    </div>
  ),
};

/**
 * Alert/message badge for success.
 */
export const AlertSuccess: Story = {
  render: () => (
    <div className="alert alert-success" role="alert" style={{ maxWidth: '500px' }}>
      <div className="alert-icon">✓</div>
      <div className="alert-content">
        <h4>Processing Complete</h4>
        <p>Document successfully processed. 3 findings were identified.</p>
      </div>
    </div>
  ),
};

/**
 * Alert/message badge for warnings.
 */
export const AlertWarning: Story = {
  render: () => (
    <div className="alert alert-warning" role="alert" style={{ maxWidth: '500px', backgroundColor: 'rgba(245, 185, 127, 0.15)', borderColor: 'rgba(245, 185, 127, 0.45)', color: '#f5b97f' }}>
      <div className="alert-icon">⚡</div>
      <div className="alert-content">
        <h4>Review Required</h4>
        <p>1 finding requires manual review before confirmation.</p>
      </div>
    </div>
  ),
};

/**
 * Alert/message badge for information.
 */
export const AlertInfo: Story = {
  render: () => (
    <div className="alert alert-info" role="alert" style={{ maxWidth: '500px', backgroundColor: 'rgba(95, 212, 232, 0.08)', borderColor: 'rgba(95, 212, 232, 0.3)', color: '#72d9ea' }}>
      <div className="alert-icon">ℹ️</div>
      <div className="alert-content">
        <h4>Privacy Notice</h4>
        <p>Your data is encrypted and never shared with third parties.</p>
      </div>
    </div>
  ),
};

/**
 * All alert variants displayed together.
 */
export const AllAlerts: Story = {
  render: () => (
    <div style={{ display: 'grid', gap: '1rem', maxWidth: '500px' }}>
      <div className="alert alert-error" role="alert">
        <div className="alert-icon">⚠️</div>
        <div className="alert-content">
          <h4>Error Message</h4>
          <p>Something went wrong during processing.</p>
        </div>
      </div>
      <div className="alert alert-success" role="alert">
        <div className="alert-icon">✓</div>
        <div className="alert-content">
          <h4>Success Message</h4>
          <p>Operation completed successfully.</p>
        </div>
      </div>
    </div>
  ),
};
