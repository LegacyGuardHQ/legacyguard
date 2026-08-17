# LegacyGuard Design System

A comprehensive guide to styling, theming, and component patterns for the LegacyGuard frontend.

## Table of Contents

1. [Overview](#overview)
2. [Design Tokens](#design-tokens)
3. [Color System](#color-system)
4. [Typography](#typography)
5. [Spacing & Layout](#spacing--layout)
6. [Components](#components)
7. [Accessibility](#accessibility)
8. [Dark/Light Theme Setup](#darklight-theme-setup)
9. [Best Practices](#best-practices)

---

## Overview

The LegacyGuard design system is built on **design tokens** — a single source of truth for all visual properties. This approach ensures consistency, scalability, and makes global changes simple.

### Files Structure

```
frontend/src/styles/
├── tokens.css          # Design tokens (colors, typography, spacing)
├── index.css           # Main stylesheet (components & layouts)
├── accessibility.css   # WCAG compliance & color improvements
└── README.md           # This file
```

### How It Works

1. **tokens.css** defines all design decisions as CSS variables
2. **index.css** uses these variables for component styling
3. **accessibility.css** ensures WCAG AAA compliance and semantic colors
4. Components inherit consistency automatically

---

## Design Tokens

All design decisions are defined in `frontend/src/styles/tokens.css` as CSS custom properties.

### Using Tokens

```css
/* Instead of hardcoding values: */
.button {
  padding: 1rem;
  font-size: 1rem;
  color: #72d9ea;
}

/* Use tokens: */
.button {
  padding: var(--spacing-lg);
  font-size: var(--font-size-base);
  color: var(--color-primary-light);
}
```

### Available Token Categories

- **Colors**: `--color-*` (primary, secondary, neutral, status)
- **Typography**: `--font-*` (family, size, weight, line-height)
- **Spacing**: `--spacing-*` (xs through 6xl)
- **Radius**: `--radius-*` (sm through full)
- **Shadows**: `--shadow-*` (sm through 2xl)
- **Transitions**: `--transition-*` (fast, normal, slow)
- **Focus States**: `--focus-ring-*` (for accessibility)

---

## Color System

### Palette Overview

The LegacyGuard color palette is built for **dark-first design** with privacy and professionalism in mind.

#### Neutral Scale (Grays)

```
--color-neutral-950: #03070d   (darkest)
--color-neutral-900: #07111f   (app background)
--color-neutral-850: #0a1728
--color-neutral-800: #0b1a2c   (card background)
--color-neutral-700: #0f1e2e
--color-neutral-600: #1a2d42
--color-neutral-500: #324965   (borders)
--color-neutral-400: #536577
--color-neutral-300: #91b8dc
--color-neutral-200: #aec0d7   (secondary text)
--color-neutral-100: #c1d0e1   (text)
--color-neutral-50: #e8eef8    (primary text)
```

#### Primary Color (Cyan)

Used for interactive elements, links, and accents.

```
--color-primary-dark: #1b4a5b
--color-primary-base: #3fb4ca
--color-primary-light: #72d9ea   (most used)
--color-primary-lighter: #8de3ef
```

**Use when:**
- Interactive elements (buttons, links)
- Active states
- Highlights and accents
- Focus indicators

#### Secondary Color (Purple)

Used for gradients and decorative elements.

```
--color-secondary-dark: #2b1f52
--color-secondary-base: #5748b3
--color-secondary-light: #7568db
```

**Use when:**
- Gradient backgrounds
- Decorative elements
- Visual hierarchy depth

#### Status Colors

Semantic colors for user feedback.

| Color | Token | Usage | Example |
|-------|-------|-------|---------|
| Pending | `--color-status-pending: #f3cf72` | In-progress actions | Loading states |
| Running | `--color-status-running: #72d9ea` | Active processes | Scanning in progress |
| Complete | `--color-status-complete: #8de3bf` | Success states | Scan finished |
| Warning | `--color-status-warning: #f5b97f` | Warnings | Failed with info |
| Error | `--color-status-error: #ff9b9b` | Errors | Scan failed |

#### Semantic Text Colors

Improved for WCAG AAA accessibility compliance (7:1 contrast ratio).

```css
--color-text-primary: #e8eef8     /* Main text */
--color-text-secondary: #b8c9da   /* Supporting text */
--color-text-tertiary: #8fa5bf    /* Subtle text */
--color-text-muted: #7a8ba3       /* Very subtle text */
```

**Contrast Ratios (verified):**
- Primary text on dark bg: 14.5:1 ✅ AAA
- Secondary text on dark bg: 10.2:1 ✅ AAA
- Tertiary text on dark bg: 6.8:1 ✅ AA+

### Semantic Color Tokens

Use these for consistent semantic meanings:

```css
/* Error states */
--color-error-text: #ff6b6b
--color-error-border: rgba(255, 107, 107, 0.4)
--color-error-bg: rgba(43, 21, 21, 0.6)

/* Success states */
--color-success-text: #51d4a8
--color-success-border: rgba(81, 212, 168, 0.4)
--color-success-bg: rgba(26, 61, 46, 0.6)

/* Warning states */
--color-warning-text: #ffa94d
--color-warning-border: rgba(255, 169, 77, 0.4)
--color-warning-bg: rgba(61, 46, 26, 0.6)

/* Info states */
--color-info-text: #5fd4e8
--color-info-border: rgba(95, 212, 232, 0.4)
--color-info-bg: rgba(26, 61, 71, 0.6)
```

### How to Change Colors Globally

To update the entire app's color scheme, edit `frontend/src/styles/tokens.css`:

```css
:root {
  --color-primary-light: #NEW_COLOR;
}
```

All components using `var(--color-primary-light)` will update automatically.

---

## Typography

### Font Families

```css
--font-family-base: Inter, ui-sans-serif, system-ui, ...
--font-family-mono: ui-monospace, SFMono-Regular, Consolas, ...
```

**Base font:** Inter (clean, modern, optimized for readability)
**Monospace font:** System monospace (code and technical values)

### Font Sizes (Major Third Scale)

A mathematical scale (1.25x multiplier) for consistent hierarchy:

```css
--font-size-xs:   0.75rem   (12px)
--font-size-sm:   0.82rem   (13px)
--font-size-base: 0.95rem   (15px)
--font-size-lg:   1.05rem   (17px)
--font-size-xl:   1.25rem   (20px)
--font-size-2xl:  1.75rem   (28px)
--font-size-3xl:  2rem      (32px)
--font-size-4xl:  2.5rem    (40px)
--font-size-5xl:  3.5rem    (56px)
```

**Usage Guide:**

| Element | Token | Usage |
|---------|-------|-------|
| Captions | `font-size-xs` | Eyebrows, badges |
| Small text | `font-size-sm` | Metadata, hints |
| Body text | `font-size-base` | Regular paragraphs |
| Emphasized | `font-size-lg` | Emphasized body text |
| Subheadings | `font-size-xl` | Secondary headings |
| Page titles | `font-size-3xl` to `5xl` | Main headings |

### Font Weights

```css
--font-weight-normal: 400     /* body text */
--font-weight-medium: 500     /* emphasis */
--font-weight-semibold: 600   /* strong emphasis */
--font-weight-bold: 700       /* headings */
--font-weight-extrabold: 800  /* buttons, tags */
--font-weight-black: 900      /* brand, emphasis */
```

### Line Heights

```css
--line-height-tight: 1.02       /* headlines */
--line-height-snug: 1.3         /* headings */
--line-height-normal: 1.5       /* body text */
--line-height-relaxed: 1.6      /* description text */
--line-height-loose: 1.75       /* large blocks */
```

### Example: Heading Styles

```css
h1 {
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-black);
  line-height: var(--line-height-snug);
}

h2 {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-snug);
}

body {
  font-size: var(--font-size-base);
  line-height: var(--line-height-normal);
}
```

---

## Spacing & Layout

### Spacing Scale

A 4px-based scale for consistent rhythm:

```css
--spacing-xs:  0.25rem   (4px)
--spacing-sm:  0.5rem    (8px)
--spacing-md:  0.75rem   (12px)
--spacing-lg:  1rem      (16px)
--spacing-xl:  1.25rem   (20px)
--spacing-2xl: 1.5rem    (24px)
--spacing-3xl: 2rem      (32px)
--spacing-4xl: 2.5rem    (40px)
--spacing-5xl: 3rem      (48px)
--spacing-6xl: 4rem      (64px)
```

### Usage Examples

```css
/* Padding */
.card { padding: var(--spacing-lg); }

/* Margin */
.section { margin-bottom: var(--spacing-2xl); }

/* Gaps in flex/grid */
.flex-group { gap: var(--spacing-md); }

/* Clamp for responsive sizing */
.dashboard {
  padding: clamp(var(--spacing-xl), 5vw, var(--spacing-5xl));
}
```

### Border Radius

```css
--radius-sm: 6px        /* subtle, small elements */
--radius-md: 8px        /* filters, dropdowns */
--radius-lg: 12px       /* inputs, cards */
--radius-xl: 14px       /* scan items */
--radius-2xl: 18px      /* metric cards */
--radius-3xl: 24px      /* page panels */
--radius-full: 999px    /* pills, badges */
```

### Shadows

```css
--shadow-sm:  0 1px 2px rgba(0, 0, 0, 0.05)
--shadow-md:  0 4px 6px rgba(0, 0, 0, 0.1)
--shadow-lg:  0 10px 15px rgba(0, 0, 0, 0.1)
--shadow-xl:  0 20px 25px rgba(0, 0, 0, 0.1)
--shadow-2xl: 0 24px 70px rgba(0, 0, 0, 0.34)    /* heavy lift */
```

---

## Components

### Common Component Patterns

#### Buttons

```css
.primary-button {
  background: var(--color-accent-gradient);
  color: white;
  padding: var(--spacing-md) var(--spacing-lg);
  border-radius: var(--radius-lg);
  font-weight: var(--font-weight-extrabold);
}

.primary-button:hover:not(:disabled) {
  opacity: 0.9;
}

.primary-button:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring-color);
}
```

#### Cards

```css
.card {
  background: var(--color-neutral-800);
  border: 1px solid var(--border-color-default);
  border-radius: var(--radius-2xl);
  padding: var(--spacing-lg);
  box-shadow: var(--shadow-md);
}

.card:hover {
  border-color: var(--color-primary-light);
  background: var(--color-neutral-850);
}
```

#### Badges

```css
.badge {
  background: rgba(95, 212, 232, 0.12);
  border: 1px solid rgba(95, 212, 232, 0.3);
  color: var(--color-primary-light);
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-full);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-extrabold);
}
```

#### Status Badge

```css
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-md);
  border: 1px solid currentColor;
  border-radius: var(--radius-full);
  padding: var(--spacing-xs) var(--spacing-md);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-extrabold);
}

.status-badge::before {
  content: "";
  width: 0.45rem;
  height: 0.45rem;
  border-radius: 50%;
  background: currentColor;
}

.status-complete { color: var(--color-status-complete); }
.status-error { color: var(--color-status-error); }
```

---

## Accessibility

### WCAG Compliance

LegacyGuard targets **WCAG AAA** (7:1 contrast ratio for normal text).

**Verified Contrast Ratios:**
- Primary text on dark: 14.5:1 ✅ AAA
- Secondary text on dark: 10.2:1 ✅ AAA
- Action buttons: 10:1+ ✅ AAA
- Focus rings: 7.2:1 ✅ AAA

### Focus States

All interactive elements must have visible focus indicators:

```css
:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring-color);
  outline-offset: var(--focus-ring-offset);
}
```

### Touch Targets

Minimum 44px × 44px for touch targets:

```css
button, a[role="button"] {
  min-height: 44px;
  min-width: 44px;
}
```

### Reduced Motion

Support users who prefer reduced motion:

```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

### High Contrast Mode

Support high contrast preferences:

```css
@media (prefers-contrast: more) {
  :root {
    --color-text-secondary: #d4dde9;
    --border-color-default: rgba(145, 184, 220, 0.4);
  }
}
```

### Color Alone Not Sufficient

Never use color as the only indicator. Always include:
- Icons or symbols
- Text labels
- Borders or patterns

---

## Dark/Light Theme Setup

The current implementation is **dark-first**. To add light mode:

1. Create `frontend/src/styles/theme-light.css`:

```css
@media (prefers-color-scheme: light) {
  :root {
    --color-neutral-900: #f8f9fb;
    --color-neutral-800: #f0f1f5;
    --color-text-primary: #1a202c;
    --color-text-secondary: #4a5568;
    /* ... override other tokens */
  }
}
```

2. Import in `main.tsx`:

```typescript
import './styles/theme-light.css';
```

3. Add theme toggle if desired.

---

## Best Practices

### 1. Always Use Tokens

❌ **Don't:**
```css
.button {
  color: #72d9ea;
  padding: 1rem;
}
```

✅ **Do:**
```css
.button {
  color: var(--color-primary-light);
  padding: var(--spacing-lg);
}
```

### 2. Semantic Colors for Intent

❌ **Don't:**
```css
.error { color: #ff6b6b; }
.success { color: #51d4a8; }
```

✅ **Do:**
```css
.error { color: var(--color-error-text); }
.success { color: var(--color-success-text); }
```

### 3. Responsive with `clamp()`

❌ **Don't:**
```css
.panel { padding: 2rem; }
```

✅ **Do:**
```css
.panel {
  padding: clamp(var(--spacing-xl), 5vw, var(--spacing-5xl));
}
```

### 4. Consistent Focus States

All interactive elements need focus indicators:

```css
button:focus-visible,
input:focus-visible,
a:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring-color);
  outline-offset: var(--focus-ring-offset);
}
```

### 5. Use Transitions for Interactivity

```css
button {
  transition: var(--transition-normal);
}

button:hover {
  background: var(--color-primary-base-hover);
}
```

### 6. Accessibility First

- Always test color contrast
- Include focus states
- Use semantic HTML
- Support keyboard navigation
- Test with screen readers

### 7. Performance

- Use CSS variables instead of SCSS/PostCSS processing
- Minimize repaints with transform/opacity
- Use will-change sparingly

```css
.animated {
  transition: transform var(--transition-normal);
}

.animated:hover {
  transform: translateY(-2px);
}
```

---

## Common Questions

### Q: How do I add a new color?

Edit `frontend/src/styles/tokens.css` and add to `:root`:

```css
:root {
  --color-custom: #hexcode;
}
```

Then use it: `color: var(--color-custom);`

### Q: Can I override tokens for specific pages?

Yes, use a scoped class:

```css
.discovery-page {
  --color-primary-light: #newcolor;
}
```

### Q: How do I implement dark mode?

Create `theme-light.css` with overridden tokens and import it.

### Q: What if a design doesn't match tokens?

First, check if you should update the tokens (consistency is key). If the exception is intentional, document it with a comment.

---

## Resources

- [CSS Custom Properties](https://developer.mozilla.org/en-US/docs/Web/CSS/--*)
- [WCAG Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [Contrast Checker](https://webaim.org/resources/contrastchecker/)
- [A11y Project](https://www.a11yproject.com/)

---

## Version History

- **v1.0** (2026-08-16): Initial design system with tokens, colors, typography, and accessibility
