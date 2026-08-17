import type { Meta, StoryObj } from '@storybook/react';

const meta = {
  title: 'Components/Card',
  tags: ['autodocs'],
  parameters: {
    layout: 'centered',
  },
} satisfies Meta<any>;

export default meta;
type Story = StoryObj<typeof meta>;

/**
 * Basic card container for content grouping with visual separation.
 */
export const Basic: Story = {
  render: () => (
    <div className="card" style={{ maxWidth: '400px' }}>
      <h2 className="card-title">Scan Results</h2>
      <p className="card-body">
        3 findings were discovered in your documents during the latest scan.
      </p>
    </div>
  ),
};

/**
 * Card in hover state showing interactive feedback.
 */
export const Hover: Story = {
  render: () => (
    <div className="card" style={{ maxWidth: '400px', borderColor: 'rgb(114, 217, 234)', backgroundColor: 'rgb(10, 23, 40)' }}>
      <h2 className="card-title">Scan Results</h2>
      <p className="card-body">
        3 findings were discovered in your documents during the latest scan.
      </p>
    </div>
  ),
};

/**
 * Card with multiple content sections.
 */
export const WithSections: Story = {
  render: () => (
    <div className="card" style={{ maxWidth: '500px' }}>
      <div className="card-header">
        <h2 className="card-title">Document Processing</h2>
      </div>
      <div className="card-body">
        <p>Status: <strong>Completed</strong></p>
        <p>Files processed: <strong>42</strong></p>
        <p>Duration: <strong>2 minutes 34 seconds</strong></p>
      </div>
    </div>
  ),
};

/**
 * Metric card for displaying key statistics and numbers.
 */
export const MetricCard: Story = {
  render: () => (
    <div className="metric-card">
      <p className="metric-label">Documents Processed</p>
      <div className="metric-value">42</div>
      <p className="metric-description">from latest scan</p>
    </div>
  ),
};

/**
 * Grid of metric cards for dashboard display.
 */
export const MetricCardGrid: Story = {
  render: () => (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', maxWidth: '800px' }}>
      <div className="metric-card">
        <p className="metric-label">Total Scans</p>
        <div className="metric-value">128</div>
      </div>
      <div className="metric-card">
        <p className="metric-label">Findings</p>
        <div className="metric-value">342</div>
      </div>
      <div className="metric-card">
        <p className="metric-label">Processed</p>
        <div className="metric-value">2.4K</div>
      </div>
    </div>
  ),
};

/**
 * Action card (clickable) with icon and description.
 */
export const ActionCard: Story = {
  render: () => (
    <a href="#" className="action-card" style={{ maxWidth: '400px', textDecoration: 'none' }}>
      <div className="action-card-icon">📊</div>
      <h3>View Scan</h3>
      <p>Check the latest discovery results and findings</p>
    </a>
  ),
};

/**
 * Action card in hover state.
 */
export const ActionCardHover: Story = {
  render: () => (
    <a href="#" className="action-card" style={{ maxWidth: '400px', textDecoration: 'none', borderColor: 'rgb(114, 217, 234)', backgroundColor: 'rgb(10, 25, 40)' }}>
      <div className="action-card-icon">📊</div>
      <h3>View Scan</h3>
      <p>Check the latest discovery results and findings</p>
    </a>
  ),
};

/**
 * Multiple action cards in a grid layout.
 */
export const ActionCardGrid: Story = {
  render: () => (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem', maxWidth: '800px' }}>
      <a href="#" className="action-card" style={{ textDecoration: 'none' }}>
        <div className="action-card-icon">🔍</div>
        <h3>Discovery</h3>
        <p>Scan and identify legacy systems</p>
      </a>
      <a href="#" className="action-card" style={{ textDecoration: 'none' }}>
        <div className="action-card-icon">📋</div>
        <h3>Review</h3>
        <p>Assess findings and plan actions</p>
      </a>
      <a href="#" className="action-card" style={{ textDecoration: 'none' }}>
        <div className="action-card-icon">✓</div>
        <h3>Confirm</h3>
        <p>Validate and document changes</p>
      </a>
      <a href="#" className="action-card" style={{ textDecoration: 'none' }}>
        <div className="action-card-icon">📊</div>
        <h3>Report</h3>
        <p>Generate and export results</p>
      </a>
    </div>
  ),
};

/**
 * Card with action buttons.
 */
export const CardWithActions: Story = {
  render: () => (
    <div className="card" style={{ maxWidth: '500px' }}>
      <h2 className="card-title">Pending Review</h2>
      <p className="card-body">
        1 finding requires manual review before confirmation.
      </p>
      <div style={{ marginTop: '1.5rem', display: 'flex', gap: '0.75rem' }}>
        <button className="btn-primary">Review Now</button>
        <button className="btn-secondary">Dismiss</button>
      </div>
    </div>
  ),
};
