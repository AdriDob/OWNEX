/**
 * OWNEX Design System — Tailwind v4 Config
 * Single source of truth for design tokens
 * Maps to frontend/src/design/tokens.css
 */

import type { Config } from 'tailwindcss'

export default {
  content: [
    './src/**/*.{vue,js,ts,jsx,tsx}',
    './frontend/**/*.{vue,js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      // Colors are defined in CSS @theme (tokens.css) - Tailwind v4 reads them automatically
      // This config just adds semantic aliases and utilities

      fontFamily: {
        display: ['var(--font-display)', 'system-ui', 'sans-serif'],
        body: ['var(--font-body)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-mono)', 'monospace'],
      },

      spacing: {
        '1': 'var(--spacing-1)',
        '2': 'var(--spacing-2)',
        '3': 'var(--spacing-3)',
        '4': 'var(--spacing-4)',
        '5': 'var(--spacing-5)',
        '6': 'var(--spacing-6)',
        '8': 'var(--spacing-8)',
        '10': 'var(--spacing-10)',
      },

      borderRadius: {
        'sm': 'var(--radius-sm)',
        'md': 'var(--radius-md)',
        'lg': 'var(--radius-lg)',
        'xl': 'var(--radius-xl)',
        'full': 'var(--radius-full)',
      },

      transitionDuration: {
        'fast': 'var(--transition-fast)',
        'base': 'var(--transition-base)',
        'slow': 'var(--transition-slow)',
      },

      boxShadow: {
        'sm': 'var(--shadow-sm)',
        'md': 'var(--shadow-md)',
        'lg': 'var(--shadow-lg)',
        'glow': 'var(--shadow-glow)',
        'glow-gold': 'var(--shadow-glow-gold)',
      },

      backdropBlur: {
        'glass': '20px',
        'glass-strong': '24px',
        'glass-light': '8px',
      },

      zIndex: {
        'status-bar': 'var(--z-status-bar)',
        'sidebar': 'var(--z-sidebar)',
        'overlay': 'var(--z-overlay)',
        'modal': 'var(--z-modal)',
        'toast': 'var(--z-toast)',
        'tooltip': 'var(--z-tooltip)',
        'splash': 'var(--z-splash)',
        'command-palette': 'var(--z-command-palette)',
      },
    },
  },
  plugins: [],
} satisfies Config