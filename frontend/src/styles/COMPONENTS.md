# Component Pattern Library

A comprehensive guide to building and styling reusable components in LegacyGuard using design tokens and best practices.

## Table of Contents

1. [Button Components](#button-components)
2. [Card Components](#card-components)
3. [Form Components](#form-components)
4. [Status & Badge Components](#status--badge-components)
5. [Navigation Components](#navigation-components)
6. [Message Components](#message-components)
7. [Layout Components](#layout-components)
8. [Creating New Components](#creating-new-components)
9. [Component Checklist](#component-checklist)

---

## Button Components

### Primary Button

**Purpose:** Main call-to-action buttons. Use sparingly—only one per section.

**Tokens Used:**
- Background: `--color-accent-gradient`
- Text: White (high contrast)
- Padding: `--spacing-md` vertical, `--spacing-lg` horizontal
- Radius: `--radius-lg`

**CSS Pattern:**

```css
.primary-button {
  background: var(--color-accent-gradient);
  color: white;
  padding: var(--spacing-md) var(--spacing-lg);
  border: none;
  border-radius: var(--radius-lg);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-extrabold);
  cursor: pointer;
  transition: var(--transition-normal);
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.primary-button:hover:not(:disabled) {
  opacity: 0.9;
  transform: translateY(-1px);
}

.primary-button:active:not(:disabled) {
  transform: translateY(0);
}

.primary-button:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring-color);
  outline-offset: var(--focus-ring-offset);
}

.primary-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
```

**React Example:**

```tsx
<button className="primary-button">
  Confirm Finding
</button>
```

**Usage Guidelines:**
- ✅ Use for primary actions (Submit, Save, Confirm)
- ❌ Don't use for secondary actions
- ❌ Don't use multiple primary buttons in sequence
- Always provide visual feedback on hover/active

---

### Secondary Button

**Purpose:** Standard actions and navigation. Can be used multiple times.

**Tokens Used:**
- Background: `--color-neutral-850`
- Text: `--color-text-primary`
- Border: Subtle primary color hint
- Padding: `--spacing-md` vertical, `--spacing-lg` horizontal

**CSS Pattern:**

```css
.secondary-button {
  background: var(--color-neutral-850);
  color: #e8eef8;
  border: var(--border-width-thin) solid rgba(95, 212, 232, 0.2);
  border-radius: var(--radius-lg);
  padding: var(--spacing-md) var(--spacing-lg);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-bold);
  cursor: pointer;
  transition: var(--transition-normal);
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.secondary-button:hover:not(:disabled) {
  background: var(--color-neutral-700);
  border-color: rgba(95, 212, 232, 0.4);
}

.secondary-button:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring-color);
  outline-offset: var(--focus-ring-offset);
}

.secondary-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
```

**React Example:**

```tsx
<button className="secondary-button">
  Cancel
</button>
```

**Usage Guidelines:**
- ✅ Use for secondary actions (Cancel, Close, Skip)
- ✅ Use for pagination controls
- ✅ Can use multiple secondary buttons
- Provides visual hierarchy with primary button

---

### Link Button (Text Button)

**Purpose:** Minimal-style actions, usually inline or supplementary.

**Tokens Used:**
- Text: `--color-primary-light`
- Background: Transparent
- No border

**CSS Pattern:**

```css
.link-button {
  background: transparent;
  color: var(--color-primary-light);
  border: none;
  padding: var(--spacing-md) var(--spacing-lg);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-extrabold);
  cursor: pointer;
  transition: var(--transition-normal);
  text-decoration: none;
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.link-button:hover:not(:disabled) {
  text-decoration: underline;
  color: var(--color-primary-lighter);
}

.link-button:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring-color);
  outline-offset: var(--focus-ring-offset);
}

.link-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
```

**React Example:**

```tsx
<button className="link-button">
  View Details
</button>
```

**Usage Guidelines:**
- ✅ Use for tertiary actions or inline actions
- ✅ Use in text/paragraph context
- ✅ Use for "Learn More" or similar
- ❌ Don't use for critical primary actions

---

### Button Group / Action Toolbar

**Purpose:** Multiple related actions grouped together.

**CSS Pattern:**

```css
.action-buttons {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  flex-wrap: wrap;
}

@media (max-width: 640px) {
  .action-buttons {
    flex-direction: column;
    width: 100%;
  }

  .action-buttons button {
    width: 100%;
  }
}
```

**React Example:**

```tsx
<div className="action-buttons">
  <button className="primary-button">Confirm</button>
  <button className="secondary-button">Dismiss</button>
  <button className="link-button">Learn More</button>
</div>
```

---

## Card Components

### Basic Card

**Purpose:** Container for related content with visual separation.

**Tokens Used:**
- Background: `--color-neutral-800`
- Border: `--border-color-default`
- Radius: `--radius-2xl`
- Shadow: `--shadow-md`
- Padding: `--spacing-lg` to `--spacing-2xl`

**CSS Pattern:**

```css
.card {
  background: var(--color-neutral-800);
  border: var(--border-width-thin) solid var(--border-color-default);
  border-radius: var(--radius-2xl);
  padding: var(--spacing-2xl);
  box-shadow: var(--shadow-md);
  transition: var(--transition-normal);
}

.card:hover {
  border-color: rgba(95, 212, 232, 0.3);
  background: var(--color-neutral-850);
  box-shadow: var(--shadow-lg);
}

.card h2 {
  margin: 0 0 var(--spacing-lg);
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
}

.card p {
  margin: var(--spacing-md) 0;
  color: var(--color-text-secondary);
  line-height: var(--line-height-relaxed);
}
```

**React Example:**

```tsx
<div className="card">
  <h2>Scan Results</h2>
  <p>3 findings were discovered in your documents.</p>
</div>
```

**Usage Guidelines:**
- ✅ Use for content grouping
- ✅ Use for metrics or status displays
- ✅ Provides visual hierarchy through borders and shadows
- Hover effect invites interaction

---

### Action Card (Clickable)

**Purpose:** Interactive card that functions as a link or button.

**CSS Pattern:**

```css
.action-card {
  background: var(--color-neutral-800);
  border: var(--border-width-thin) solid var(--border-color-default);
  border-radius: var(--radius-2xl);
  padding: var(--spacing-2xl);
  cursor: pointer;
  transition: var(--transition-normal);
  text-decoration: none;
  color: inherit;
  display: grid;
  gap: var(--spacing-lg);
}

.action-card:hover {
  border-color: var(--color-primary-light);
  background: var(--color-neutral-850);
  box-shadow: var(--shadow-lg);
}

.action-card:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring-color);
  outline-offset: var(--focus-ring-offset);
}

.action-card h3 {
  margin: 0;
  font-size: var(--font-size-lg);
  color: var(--color-text-primary);
}

.action-card p {
  margin: 0;
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
}

.action-card-icon {
  color: var(--color-primary-light);
  font-size: var(--font-size-2xl);
}
```

**React Example:**

```tsx
<a href="/discovery/scans" className="action-card">
  <div className="action-card-icon">📊</div>
  <h3>View Scan</h3>
  <p>Check the latest discovery results</p>
</a>
```

---

### Metric Card

**Purpose:** Display key numbers or statistics.

**CSS Pattern:**

```css
.metric-card {
  background: var(--color-neutral-800);
  border: var(--border-width-thin) solid #223850;
  border-radius: var(--radius-2xl);
  padding: var(--spacing-2xl);
  text-align: center;
}

.metric-label {
  margin: 0;
  color: var(--color-text-tertiary);
  font-weight: var(--font-weight-bold);
  font-size: var(--font-size-sm);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.metric-value {
  margin: var(--spacing-lg) 0;
  color: var(--color-text-primary);
  font-size: clamp(var(--font-size-2xl), 5vw, var(--font-size-4xl));
  font-weight: var(--font-weight-black);
  line-height: 1;
}

.metric-description {
  margin: var(--spacing-lg) 0 0;
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
  line-height: var(--line-height-snug);
}
```

**React Example:**

```tsx
<div className="metric-card">
  <p className="metric-label">Documents Processed</p>
  <div className="metric-value">42</div>
  <p className="metric-description">from latest scan</p>
</div>
```

**Usage Guidelines:**
- ✅ Use for key metrics and statistics
- ✅ Use in dashboards
- Simple, focused data display

---

## Form Components

### Form Field (Input + Label)

**Purpose:** Standard text input with label and optional help text.

**Tokens Used:**
- Background: `--color-neutral-850`
- Border: `--border-color-strong`
- Focus: `--focus-ring-color`
- Padding: `--spacing-md` to `--spacing-lg`

**CSS Pattern:**

```css
.form-field {
  display: grid;
  gap: var(--spacing-md);
}

.form-field label {
  display: block;
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-bold);
  margin: 0;
}

.form-field input,
.form-field textarea,
.form-field select {
  width: 100%;
  padding: var(--spacing-md) var(--spacing-lg);
  border: var(--border-width-thin) solid var(--color-neutral-500);
  border-radius: var(--radius-lg);
  background: var(--color-neutral-850);
  color: var(--color-text-primary);
  font-family: var(--font-family-base);
  font-size: var(--font-size-base);
  transition: var(--transition-normal);
}

.form-field input::placeholder,
.form-field textarea::placeholder {
  color: var(--color-text-muted);
}

.form-field input:focus,
.form-field textarea:focus,
.form-field select:focus {
  border-color: var(--color-primary-light);
  box-shadow: 0 0 0 3px rgba(95, 212, 232, 0.15);
  outline: none;
}

.form-field input:disabled,
.form-field textarea:disabled,
.form-field select:disabled {
  background-color: var(--color-neutral-700);
  opacity: 0.6;
  cursor: not-allowed;
}

.form-help {
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
  margin: 0;
  line-height: var(--line-height-snug);
}

.form-error {
  color: var(--color-error-text);
  font-size: var(--font-size-sm);
  margin: 0;
}
```

**React Example:**

```tsx
<div className="form-field">
  <label htmlFor="email">Email Address</label>
  <input
    id="email"
    type="email"
    placeholder="you@example.com"
    aria-describedby="email-help"
  />
  <p id="email-help" className="form-help">
    We'll never share your email.
  </p>
</div>
```

**Accessibility:**
- Use `htmlFor` on labels
- Use `aria-describedby` for help text
- Use `aria-invalid` for error states

---

### Form Grid (Multi-column Layout)

**Purpose:** Arrange multiple form fields in responsive grid.

**CSS Pattern:**

```css
.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--spacing-lg);
}

.form-field-wide {
  grid-column: 1 / -1;
}

@media (max-width: 640px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}
```

**React Example:**

```tsx
<div className="form-grid">
  <div className="form-field">
    <label>First Name</label>
    <input type="text" />
  </div>
  <div className="form-field">
    <label>Last Name</label>
    <input type="text" />
  </div>
  <div className="form-field form-field-wide">
    <label>Address</label>
    <input type="text" />
  </div>
</div>
```

---

### Form Section with Card

**Purpose:** Grouped form fields with visual separation.

**CSS Pattern:**

```css
.form-section {
  background: var(--color-neutral-800);
  border: var(--border-width-thin) solid var(--border-color-default);
  border-radius: var(--radius-2xl);
  padding: var(--spacing-2xl);
}

.form-section h3 {
  margin: 0 0 var(--spacing-lg);
  color: var(--color-text-primary);
  font-size: var(--font-size-lg);
}

.form-section + .form-section {
  margin-top: var(--spacing-2xl);
}
```

---

## Status & Badge Components

### Status Badge

**Purpose:** Show status of a scan, finding, or other entity.

**Tokens Used:**
- Colors vary by status
- Uses `currentColor` for flexibility
- Border: 1px solid
- Radius: `--radius-full`

**CSS Pattern:**

```css
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-md);
  border: var(--border-width-thin) solid currentColor;
  border-radius: var(--radius-full);
  padding: var(--spacing-xs) var(--spacing-md);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-extrabold);
  white-space: nowrap;
  text-transform: capitalize;
}

.status-badge::before {
  content: "";
  width: 0.45rem;
  height: 0.45rem;
  border-radius: 50%;
  background: currentColor;
  flex-shrink: 0;
}

/* Status variants */
.status-pending { color: var(--color-status-pending); }
.status-running { color: var(--color-status-running); }
.status-complete { color: var(--color-status-complete); }
.status-warning { color: var(--color-status-warning); }
.status-error { color: var(--color-status-error); }
```

**React Example:**

```tsx
<span className="status-badge status-complete">
  Completed
</span>
```

**Usage Guidelines:**
- ✅ Use to indicate state/status
- ✅ Color + icon indicates meaning
- ❌ Don't use color alone—always include text

---

### Tag/Chip Badge

**Purpose:** Categorize or label content. Can be interactive.

**CSS Pattern:**

```css
.badge {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  background: rgba(95, 212, 232, 0.12);
  border: var(--border-width-thin) solid rgba(95, 212, 232, 0.3);
  color: var(--color-primary-light);
  padding: var(--spacing-xs) var(--spacing-md);
  border-radius: var(--radius-full);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-extrabold);
}

.badge:hover {
  background: rgba(95, 212, 232, 0.2);
  border-color: rgba(95, 212, 232, 0.5);
}

.badge-removable {
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.badge-remove {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  padding: 0;
  margin-left: var(--spacing-xs);
  font-size: 1em;
}
```

**React Example:**

```tsx
<span className="badge">
  Account Verified
</span>
```

---

### Alert/Message Badge

**Purpose:** Show warnings, errors, or info messages prominently.

**CSS Pattern:**

```css
.alert {
  display: flex;
  gap: var(--spacing-lg);
  padding: var(--spacing-lg) var(--spacing-2xl);
  border-radius: var(--radius-lg);
  border: var(--border-width-thin) solid;
  font-size: var(--font-size-base);
  line-height: var(--line-height-relaxed);
}

.alert-error {
  background: var(--color-error-bg);
  border-color: var(--color-error-border);
  color: var(--color-error-text);
}

.alert-success {
  background: var(--color-success-bg);
  border-color: var(--color-success-border);
  color: var(--color-success-text);
}

.alert-warning {
  background: var(--color-warning-bg);
  border-color: var(--color-warning-border);
  color: var(--color-warning-text);
}

.alert-info {
  background: var(--color-info-bg);
  border-color: var(--color-info-border);
  color: var(--color-info-text);
}

.alert-icon {
  flex-shrink: 0;
  font-size: var(--font-size-lg);
}

.alert-content h4 {
  margin: 0 0 var(--spacing-sm);
  font-size: var(--font-size-lg);
}

.alert-content p {
  margin: 0;
}
```

**React Example:**

```tsx
<div className="alert alert-error" role="alert">
  <div className="alert-icon">⚠️</div>
  <div className="alert-content">
    <h4>Processing Failed</h4>
    <p>Unable to process document. Please try again.</p>
  </div>
</div>
```

---

## Navigation Components

### Tabs

**Purpose:** Switch between related content sections.

**CSS Pattern:**

```css
.tab-nav {
  display: flex;
  gap: var(--spacing-md);
  flex-wrap: wrap;
  border-bottom: var(--border-width-thin) solid var(--border-color-default);
  padding-bottom: var(--spacing-md);
}

.tab-button {
  background: transparent;
  border: none;
  color: var(--color-text-tertiary);
  padding: var(--spacing-md) var(--spacing-2xl);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-bold);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: var(--transition-normal);
  position: relative;
}

.tab-button:hover {
  color: var(--color-text-primary);
  background: rgba(95, 212, 232, 0.08);
}

.tab-button.active {
  color: var(--color-primary-light);
  background: rgba(95, 212, 232, 0.12);
  border: var(--border-width-thin) solid rgba(95, 212, 232, 0.3);
}

.tab-button:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring-color);
  outline-offset: var(--focus-ring-offset);
}

.tab-panel {
  margin-top: var(--spacing-lg);
}

.tab-panel[hidden] {
  display: none;
}
```

**React Example:**

```tsx
<div className="tab-nav" role="tablist">
  <button
    className="tab-button active"
    role="tab"
    aria-selected="true"
  >
    Pending Review
  </button>
  <button
    className="tab-button"
    role="tab"
    aria-selected="false"
  >
    Confirmed
  </button>
</div>
```

**Keyboard Navigation:**
- Arrow Left/Right to switch tabs
- Home/End to jump to first/last tab

---

## Message Components

### Info Box / Callout

**Purpose:** Highlight important information or tips.

**CSS Pattern:**

```css
.info-box {
  padding: var(--spacing-lg) var(--spacing-2xl);
  border-left: 3px solid var(--color-primary-light);
  background: rgba(95, 212, 232, 0.06);
  border-radius: 0 var(--radius-lg) var(--radius-lg) 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  line-height: var(--line-height-relaxed);
}

.info-box strong {
  color: var(--color-text-primary);
}

.info-box p {
  margin: 0;
}

.info-box p + p {
  margin-top: var(--spacing-md);
}
```

**React Example:**

```tsx
<div className="info-box">
  <strong>Privacy Notice:</strong> Your data is encrypted and never shared with third parties.
</div>
```

---

## Layout Components

### Container / Max-Width Wrapper

**Purpose:** Constrain content to readable width on large screens.

**CSS Pattern:**

```css
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 var(--spacing-lg);
}

@media (max-width: 640px) {
  .container {
    padding: 0 var(--spacing-md);
  }
}
```

---

### Section / Page Panel

**Purpose:** Main content container with visual separation.

**CSS Pattern:**

```css
.page-panel {
  background: linear-gradient(
    135deg,
    rgba(21, 50, 75, 0.85),
    rgba(34, 31, 83, 0.72)
  );
  border: var(--border-width-thin) solid var(--border-color-lighter);
  border-radius: var(--radius-3xl);
  padding: clamp(var(--spacing-2xl), 4vw, var(--spacing-4xl));
}

.page-panel h1 {
  margin: var(--spacing-md) 0 var(--spacing-lg);
  font-size: clamp(var(--font-size-3xl), 4vw, var(--font-size-5xl));
  font-weight: var(--font-weight-black);
}

.page-panel > p {
  color: var(--color-text-secondary);
  line-height: var(--line-height-loose);
  max-width: 720px;
}
```

---

### Responsive Grid

**Purpose:** Flexible grid layout for dashboards and listings.

**CSS Pattern:**

```css
.grid {
  display: grid;
  gap: var(--spacing-lg);
}

.grid-2 {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.grid-3 {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

@media (max-width: 1024px) {
  .grid-3 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 640px) {
  .grid-2,
  .grid-3 { grid-template-columns: 1fr; }
}
```

**React Example:**

```tsx
<div className="grid grid-3">
  <div className="metric-card">...</div>
  <div className="metric-card">...</div>
  <div className="metric-card">...</div>
</div>
```

---

## Creating New Components

### Component Development Checklist

Before building a new component, ask:

1. **Purpose:** What problem does this solve?
2. **Variations:** What states does it have (default, hover, active, disabled, error)?
3. **Tokens:** Which design tokens should it use?
4. **Accessibility:** Does it work with screen readers and keyboard?
5. **Responsive:** Does it work on mobile and desktop?

### Template for New Components

```css
/* MyComponent */

.my-component {
  /* Layout */
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);

  /* Spacing */
  padding: var(--spacing-lg);
  margin: 0;

  /* Styling */
  background: var(--color-neutral-800);
  border: var(--border-width-thin) solid var(--border-color-default);
  border-radius: var(--radius-lg);

  /* Typography */
  font-family: var(--font-family-base);
  font-size: var(--font-size-base);
  color: var(--color-text-primary);

  /* Animation */
  transition: var(--transition-normal);
}

/* States */
.my-component:hover {
  border-color: var(--color-primary-light);
}

.my-component:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring-color);
  outline-offset: var(--focus-ring-offset);
}

.my-component:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Variants */
.my-component.variant-primary {
  background: var(--color-primary-light);
  color: #000;
}

/* Responsive */
@media (max-width: 640px) {
  .my-component {
    flex-direction: row;
  }
}
```

---

## Component Checklist

Use this checklist when building or reviewing components:

- [ ] **Tokens Used**: All colors, spacing, typography use CSS variables
- [ ] **Accessibility**:
  - [ ] Keyboard navigation works (Tab, Enter, Escape, Arrows)
  - [ ] Focus indicators visible
  - [ ] ARIA labels/roles present (if needed)
  - [ ] Color contrast verified (min 4.5:1, preferably 7:1)
  - [ ] Works with screen readers
- [ ] **Responsive**:
  - [ ] Mobile view tested (< 640px)
  - [ ] Tablet view tested (640px - 1024px)
  - [ ] Desktop view tested (> 1024px)
  - [ ] Touch targets minimum 44px
- [ ] **States**:
  - [ ] Default state
  - [ ] Hover state
  - [ ] Focus state
  - [ ] Active state
  - [ ] Disabled state
  - [ ] Error state (if applicable)
  - [ ] Loading state (if applicable)
- [ ] **Performance**:
  - [ ] No unnecessary repaints
  - [ ] Animations use transform/opacity
  - [ ] Lazy loading if needed
- [ ] **Documentation**:
  - [ ] Component purpose documented
  - [ ] Usage example provided
  - [ ] Props/variants listed
  - [ ] Accessibility notes included

---

## Common Patterns

### Disabled State
```css
.component:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  pointer-events: none;
}
```

### Loading State
```css
.component.loading {
  opacity: 0.6;
}

.component.loading::after {
  content: "";
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
```

### Empty State
```css
.empty-state {
  text-align: center;
  padding: var(--spacing-4xl);
  color: var(--color-text-tertiary);
}

.empty-state-icon {
  font-size: var(--font-size-5xl);
  margin-bottom: var(--spacing-lg);
  opacity: 0.5;
}
```

---

## Resources

- [Web Accessibility Guidelines](https://www.w3.org/WAI/fundamentals/)
- [Design Tokens Spec](https://designtokens.org/)
- [MDN Component Examples](https://developer.mozilla.org/en-US/docs/Web/Components)
- [A11y Project Checklist](https://www.a11yproject.com/checklist/)

---

## Version History

- **v1.0** (2026-08-16): Initial component pattern library with buttons, cards, forms, badges, and layout components
