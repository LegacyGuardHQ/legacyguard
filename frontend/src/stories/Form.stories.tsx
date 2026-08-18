import type { Meta, StoryObj } from '@storybook/react';

const meta = {
  title: 'Components/Form',
  tags: ['autodocs'],
  parameters: {
    layout: 'centered',
  },
} satisfies Meta<any>;

export default meta;
type Story = StoryObj<typeof meta>;

/**
 * Basic text input field with label.
 */
export const TextInput: Story = {
  render: () => (
    <div className="form-field" style={{ maxWidth: '400px' }}>
      <label htmlFor="name" className="form-label">Full Name</label>
      <input
        id="name"
        type="text"
        className="form-input"
        placeholder="Enter your name"
      />
      <p className="form-help">Enter your full name as it appears in your account.</p>
    </div>
  ),
};

/**
 * Text input in focused state.
 */
export const TextInputFocused: Story = {
  render: () => (
    <div className="form-field" style={{ maxWidth: '400px' }}>
      <label htmlFor="email" className="form-label">Email Address</label>
      <input
        id="email"
        type="email"
        className="form-input"
        placeholder="your@email.com"
        style={{
          borderColor: 'rgb(63, 180, 202)',
          outline: 'none',
          boxShadow: '0 0 0 2px rgba(63, 180, 202, 0.15)',
        }}
        autoFocus
      />
    </div>
  ),
};

/**
 * Text input in disabled state.
 */
export const TextInputDisabled: Story = {
  render: () => (
    <div className="form-field" style={{ maxWidth: '400px' }}>
      <label htmlFor="readonly" className="form-label">Account ID</label>
      <input
        id="readonly"
        type="text"
        className="form-input"
        value="ACC-12345-67890"
        disabled
      />
      <p className="form-help">This field cannot be edited.</p>
    </div>
  ),
};

/**
 * Text area for multi-line input.
 */
export const TextArea: Story = {
  render: () => (
    <div className="form-field" style={{ maxWidth: '400px' }}>
      <label htmlFor="description" className="form-label">Description</label>
      <textarea
        id="description"
        className="form-input"
        placeholder="Enter a description"
        rows={4}
      />
      <p className="form-help">Provide additional details about your finding.</p>
    </div>
  ),
};

/**
 * Select dropdown field.
 */
export const Select: Story = {
  render: () => (
    <div className="form-field" style={{ maxWidth: '400px' }}>
      <label htmlFor="priority" className="form-label">Priority Level</label>
      <select id="priority" className="form-input">
        <option>Select a priority</option>
        <option>Low</option>
        <option>Medium</option>
        <option>High</option>
        <option>Critical</option>
      </select>
    </div>
  ),
};

/**
 * Checkbox input field.
 */
export const Checkbox: Story = {
  render: () => (
    <div className="form-field" style={{ maxWidth: '400px' }}>
      <label style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer' }}>
        <input type="checkbox" style={{ width: '20px', height: '20px' }} />
        <span style={{ color: '#e8eef8' }}>I agree to the terms and conditions</span>
      </label>
    </div>
  ),
};

/**
 * Radio button group.
 */
export const RadioGroup: Story = {
  render: () => (
    <div className="form-field" style={{ maxWidth: '400px' }}>
      <fieldset style={{ border: 'none', padding: 0, margin: 0 }}>
        <legend className="form-label" style={{ marginBottom: '0.75rem' }}>Scan Type</legend>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer' }}>
            <input type="radio" name="scanType" defaultChecked />
            <span style={{ color: '#e8eef8' }}>Full Scan</span>
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer' }}>
            <input type="radio" name="scanType" />
            <span style={{ color: '#e8eef8' }}>Incremental Scan</span>
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer' }}>
            <input type="radio" name="scanType" />
            <span style={{ color: '#e8eef8' }}>Quick Scan</span>
          </label>
        </div>
      </fieldset>
    </div>
  ),
};

/**
 * Complete form with multiple input types.
 */
export const CompleteForm: Story = {
  render: () => (
    <form style={{ maxWidth: '500px' }}>
      <div style={{ display: 'grid', gap: '1.5rem' }}>
        <div className="form-field">
          <label htmlFor="docname" className="form-label">Document Name</label>
          <input
            id="docname"
            type="text"
            className="form-input"
            placeholder="e.g., Legacy Database Audit"
          />
        </div>

        <div className="form-field">
          <label htmlFor="doctype" className="form-label">Document Type</label>
          <select id="doctype" className="form-input">
            <option>Select a type</option>
            <option>Database Schema</option>
            <option>API Documentation</option>
            <option>System Architecture</option>
            <option>Code Repository</option>
          </select>
        </div>

        <div className="form-field">
          <label htmlFor="notes" className="form-label">Additional Notes</label>
          <textarea
            id="notes"
            className="form-input"
            placeholder="Add any additional context"
            rows={3}
          />
        </div>

        <fieldset style={{ border: 'none', padding: 0, margin: 0 }}>
          <legend className="form-label" style={{ marginBottom: '0.75rem' }}>Scan Options</legend>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer' }}>
              <input type="checkbox" defaultChecked />
              <span style={{ color: '#e8eef8' }}>Deep Analysis</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer' }}>
              <input type="checkbox" />
              <span style={{ color: '#e8eef8' }}>Generate Report</span>
            </label>
          </div>
        </fieldset>

        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button type="submit" className="btn-primary">Start Scan</button>
          <button type="reset" className="btn-secondary">Clear</button>
        </div>
      </div>
    </form>
  ),
};

/**
 * Form with error states.
 */
export const FormWithErrors: Story = {
  render: () => (
    <form style={{ maxWidth: '500px' }}>
      <div style={{ display: 'grid', gap: '1.5rem' }}>
        <div className="form-field">
          <label htmlFor="email-error" className="form-label">Email Address</label>
          <input
            id="email-error"
            type="email"
            className="form-input"
            value="invalid-email"
            style={{
              borderColor: '#ff6d6d',
              backgroundColor: 'rgba(108, 27, 36, 0.35)',
            }}
          />
          <p style={{ color: '#ffc7c7', fontSize: '0.82rem', margin: '0.5rem 0 0 0' }}>
            Please enter a valid email address.
          </p>
        </div>

        <div className="form-field">
          <label htmlFor="password-error" className="form-label">Password</label>
          <input
            id="password-error"
            type="password"
            className="form-input"
            placeholder="Enter password"
            style={{
              borderColor: '#ff6d6d',
              backgroundColor: 'rgba(108, 27, 36, 0.35)',
            }}
          />
          <p style={{ color: '#ffc7c7', fontSize: '0.82rem', margin: '0.5rem 0 0 0' }}>
            Password must be at least 8 characters long.
          </p>
        </div>

        <button type="submit" className="btn-primary" disabled>
          Submit
        </button>
      </div>
    </form>
  ),
};
