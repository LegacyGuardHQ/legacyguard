import type { Meta, StoryObj } from '@storybook/react';

const meta = {
  title: 'Components/Button',
  tags: ['autodocs'],
  parameters: {
    layout: 'centered',
  },
} satisfies Meta<any>;

export default meta;
type Story = StoryObj<typeof meta>;

/**
 * Primary button for main call-to-action. Use sparingly—only one per section.
 */
export const Primary: Story = {
  render: () => (
    <button className="primary-button">
      Confirm Finding
    </button>
  ),
};

/**
 * Primary button in hover state.
 */
export const PrimaryHover: Story = {
  render: () => (
    <button className="primary-button" style={{ opacity: 0.9 }}>
      Confirm Finding
    </button>
  ),
};

/**
 * Primary button in disabled state.
 */
export const PrimaryDisabled: Story = {
  render: () => (
    <button className="primary-button" disabled>
      Confirm Finding
    </button>
  ),
};

/**
 * Secondary button for standard actions. Can be used multiple times.
 */
export const Secondary: Story = {
  render: () => (
    <button className="secondary-button">
      Cancel
    </button>
  ),
};

/**
 * Secondary button in hover state.
 */
export const SecondaryHover: Story = {
  render: () => (
    <button className="secondary-button" style={{ backgroundColor: '#0f1e2e', borderColor: 'rgba(95, 212, 232, 0.4)' }}>
      Cancel
    </button>
  ),
};

/**
 * Secondary button in disabled state.
 */
export const SecondaryDisabled: Story = {
  render: () => (
    <button className="secondary-button" disabled>
      Cancel
    </button>
  ),
};

/**
 * Link button for minimal-style actions, usually inline or supplementary.
 */
export const Link: Story = {
  render: () => (
    <button className="link-button">
      View Details
    </button>
  ),
};

/**
 * Link button in hover state.
 */
export const LinkHover: Story = {
  render: () => (
    <button className="link-button" style={{ textDecoration: 'underline' }}>
      View Details
    </button>
  ),
};

/**
 * Link button in disabled state.
 */
export const LinkDisabled: Story = {
  render: () => (
    <button className="link-button" disabled>
      View Details
    </button>
  ),
};

/**
 * Multiple buttons grouped together with proper spacing.
 */
export const ButtonGroup: Story = {
  render: () => (
    <div className="action-buttons">
      <button className="primary-button">Confirm</button>
      <button className="secondary-button">Dismiss</button>
      <button className="link-button">Learn More</button>
    </div>
  ),
};

/**
 * All button types displayed together for comparison.
 */
export const AllVariants: Story = {
  render: () => (
    <div style={{ display: 'grid', gap: '2rem' }}>
      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
        <button className="primary-button">Primary</button>
        <button className="secondary-button">Secondary</button>
        <button className="link-button">Link</button>
      </div>
      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
        <button className="primary-button" disabled>Primary Disabled</button>
        <button className="secondary-button" disabled>Secondary Disabled</button>
        <button className="link-button" disabled>Link Disabled</button>
      </div>
    </div>
  ),
};
