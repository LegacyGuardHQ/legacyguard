import type { Config } from 'tailwindcss';

export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // Neutral palette
        neutral: {
          50: '#e8eef8',
          100: '#c1d0e1',
          200: '#aec0d7',
          300: '#91b8dc',
          400: '#536577',
          500: '#324965',
          600: '#1a2d42',
          700: '#0f1e2e',
          800: '#0b1a2c',
          850: '#0a1728',
          900: '#07111f',
          950: '#03070d',
        },
        // Primary - Cyan
        primary: {
          dark: '#1b4a5b',
          base: '#3fb4ca',
          light: '#72d9ea',
          lighter: '#8de3ef',
        },
        // Secondary - Purple
        secondary: {
          dark: '#2b1f52',
          base: '#5748b3',
          light: '#7568db',
        },
        // Status colors
        status: {
          pending: '#f3cf72',
          running: '#72d9ea',
          complete: '#8de3bf',
          warning: '#f5b97f',
          error: '#ff9b9b',
        },
        // Semantic
        error: {
          text: '#ffc7c7',
          border: 'rgba(255, 109, 109, 0.45)',
          bg: 'rgba(108, 27, 36, 0.35)',
        },
        success: {
          text: '#a9ebd0',
          border: 'rgba(54, 211, 153, 0.4)',
          bg: 'rgba(32, 91, 70, 0.3)',
        },
      },
      fontFamily: {
        base: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Consolas', 'monospace'],
      },
      fontSize: {
        xs: ['0.75rem', { lineHeight: '1.5' }],
        sm: ['0.82rem', { lineHeight: '1.5' }],
        base: ['0.95rem', { lineHeight: '1.5' }],
        lg: ['1.05rem', { lineHeight: '1.5' }],
        xl: ['1.25rem', { lineHeight: '1.3' }],
        '2xl': ['1.75rem', { lineHeight: '1.3' }],
        '3xl': ['2rem', { lineHeight: '1.3' }],
        '4xl': ['2.5rem', { lineHeight: '1.02' }],
        '5xl': ['3.5rem', { lineHeight: '1.02' }],
      },
      spacing: {
        xs: '0.25rem',
        sm: '0.5rem',
        md: '0.75rem',
        lg: '1rem',
        xl: '1.25rem',
        '2xl': '1.5rem',
        '3xl': '2rem',
        '4xl': '2.5rem',
        '5xl': '3rem',
        '6xl': '4rem',
      },
      borderRadius: {
        sm: '6px',
        md: '8px',
        lg: '12px',
        xl: '14px',
        '2xl': '18px',
        '3xl': '24px',
        full: '999px',
      },
      boxShadow: {
        sm: '0 1px 2px rgba(0, 0, 0, 0.05)',
        md: '0 4px 6px rgba(0, 0, 0, 0.1)',
        lg: '0 10px 15px rgba(0, 0, 0, 0.1)',
        xl: '0 20px 25px rgba(0, 0, 0, 0.1)',
        '2xl': '0 24px 70px rgba(0, 0, 0, 0.34)',
      },
      transitionDuration: {
        fast: '150ms',
        normal: '200ms',
        slow: '300ms',
      },
      backgroundImage: {
        'gradient-accent': 'linear-gradient(135deg, #3fb4ca, #7568db)',
      },
      backdropBlur: {
        sm: 'blur(8px)',
        md: 'blur(14px)',
        lg: 'blur(16px)',
      },
    },
  },
  plugins: [
    function ({ addComponents, theme }: any) {
      addComponents({
        // Button components
        '.btn-primary': {
          '@apply px-lg py-md bg-gradient-accent text-white font-extrabold rounded-lg cursor-pointer transition-normal min-h-[44px] inline-flex items-center justify-center hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-light disabled:opacity-50 disabled:cursor-not-allowed': {},
        },
        '.btn-secondary': {
          '@apply px-lg py-md bg-neutral-800 text-neutral-50 border border-neutral-600 font-bold rounded-lg cursor-pointer transition-normal min-h-[44px] inline-flex items-center justify-center hover:bg-neutral-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-light disabled:opacity-50 disabled:cursor-not-allowed': {},
        },
        '.btn-link': {
          '@apply px-lg py-md text-primary-light font-extrabold cursor-pointer transition-normal min-h-[44px] inline-flex items-center justify-center hover:text-primary-lighter hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-light disabled:opacity-50 disabled:cursor-not-allowed': {},
        },

        // Card components
        '.card': {
          '@apply bg-neutral-800 border border-neutral-500 rounded-2xl p-lg transition-normal hover:border-primary-light hover:bg-neutral-850 hover:shadow-lg': {},
        },
        '.card-header': {
          '@apply mb-lg': {},
        },
        '.card-title': {
          '@apply text-xl font-bold m-0': {},
        },
        '.card-body': {
          '@apply text-neutral-200': {},
        },

        // Badge components
        '.badge': {
          '@apply inline-flex items-center gap-sm px-md py-xs bg-primary-base bg-opacity-10 border border-primary-base border-opacity-30 text-primary-light rounded-full text-xs font-extrabold': {},
        },
        '.badge-success': {
          '@apply bg-status-complete bg-opacity-15 border-status-complete border-opacity-40 text-status-complete': {},
        },
        '.badge-error': {
          '@apply bg-status-error bg-opacity-15 border-status-error border-opacity-40 text-status-error': {},
        },
        '.badge-warning': {
          '@apply bg-status-warning bg-opacity-15 border-status-warning border-opacity-40 text-status-warning': {},
        },

        // Form components
        '.form-field': {
          '@apply flex flex-col gap-md': {},
        },
        '.form-label': {
          '@apply block text-neutral-50 font-bold text-base': {},
        },
        '.form-input': {
          '@apply w-full px-lg py-md border border-neutral-500 rounded-lg bg-neutral-850 text-neutral-50 font-base transition-normal focus:border-primary-light focus:outline-none focus:ring-2 focus:ring-primary-light focus:ring-opacity-15 disabled:bg-neutral-700 disabled:opacity-60 disabled:cursor-not-allowed': {},
        },
        '.form-help': {
          '@apply text-neutral-400 text-sm': {},
        },

        // Alert components
        '.alert': {
          '@apply flex gap-lg p-lg rounded-lg border': {},
        },
        '.alert-error': {
          '@apply bg-error-bg border-error-border text-error-text': {},
        },
        '.alert-success': {
          '@apply bg-success-bg border-success-border text-success-text': {},
        },
      });
    },
  ],
} satisfies Config;
