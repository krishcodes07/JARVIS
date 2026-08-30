/** @type {import('tailwindcss').Config} */

/**
 * Every colour resolves through a CSS custom property set by
 * `src/theme/applyTheme.ts`, so `bg-surface-1` / `text-accent` follow the
 * active theme without any per-theme class variants.
 */
const token = (name) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        void: token('bg-void'),
        surface: {
          1: token('bg-surface-1'),
          2: token('bg-surface-2'),
          3: token('bg-surface-3'),
          DEFAULT: token('bg-surface-1'),
        },
        subtle: token('border-subtle'),
        strong: token('border-strong'),
        accent: {
          DEFAULT: token('accent'),
          soft: token('accent-soft'),
          glow: token('accent-glow'),
        },
        content: {
          DEFAULT: token('text-primary'),
          secondary: token('text-secondary'),
          muted: token('text-muted'),
        },
        success: token('success'),
        warning: token('warning'),
        danger: token('danger'),
        info: token('info'),
      },
      borderColor: {
        DEFAULT: 'rgb(var(--border-subtle) / 0.10)',
      },
      /*
       * Tailwind's stock opacity scale jumps 5 → 10 → 20, which is far too coarse
       * for the hairline borders and tinted surfaces this design system leans on.
       * Values not listed here silently produce no CSS at all, so anything used
       * as a `/NN` modifier must be registered.
       */
      opacity: {
        2: '0.02',
        3: '0.03',
        4: '0.04',
        6: '0.06',
        7: '0.07',
        8: '0.08',
        12: '0.12',
        14: '0.14',
        15: '0.15',
        18: '0.18',
        22: '0.22',
        25: '0.25',
        28: '0.28',
        32: '0.32',
        35: '0.35',
        45: '0.45',
        55: '0.55',
        65: '0.65',
        85: '0.85',
      },
      fontFamily: {
        sans: ['"Poppins"', '"Plus Jakarta Sans"', 'system-ui', '-apple-system', 'sans-serif'],
        display: ['"Poppins"', '"Plus Jakarta Sans"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      fontWeight: {
        450: '450',
      },
      boxShadow: {
        'accent-sm': '0 0 0 1px rgb(var(--accent) / 0.25), 0 2px 8px -2px rgb(var(--accent) / 0.35)',
        'accent-md': '0 0 24px -4px rgb(var(--accent) / 0.45)',
        'accent-lg': '0 0 60px -10px rgb(var(--accent) / 0.55)',
        panel: '0 24px 64px -16px rgb(0 0 0 / 0.7)',
      },
      keyframes: {
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        'slide-up': {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-down': {
          from: { opacity: '0', transform: 'translateY(-8px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        'scale-in': {
          from: { opacity: '0', transform: 'scale(0.96)' },
          to: { opacity: '1', transform: 'scale(1)' },
        },
        'pulse-glow': {
          '0%, 100%': { opacity: '0.45' },
          '50%': { opacity: '1' },
        },
        shimmer: {
          '100%': { transform: 'translateX(100%)' },
        },
        'caret-blink': {
          '0%, 45%': { opacity: '1' },
          '50%, 95%': { opacity: '0.15' },
        },
      },
      animation: {
        'fade-in': 'fade-in 180ms ease-out both',
        'slide-up': 'slide-up 220ms cubic-bezier(0.22, 1, 0.36, 1) both',
        'slide-down': 'slide-down 220ms cubic-bezier(0.22, 1, 0.36, 1) both',
        'scale-in': 'scale-in 180ms cubic-bezier(0.22, 1, 0.36, 1) both',
        'pulse-glow': 'pulse-glow 2.4s ease-in-out infinite',
        shimmer: 'shimmer 1.6s infinite',
        'caret-blink': 'caret-blink 1s steps(1) infinite',
      },
      transitionTimingFunction: {
        spring: 'cubic-bezier(0.22, 1, 0.36, 1)',
      },
    },
  },
  plugins: [],
}
