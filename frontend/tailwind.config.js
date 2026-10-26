/** @type {import('tailwindcss').Config} */

const palette = {
  bg: '#FFFAF3',
  surface: '#FFF2DB',
  soft: '#FFE5BF',
  accent: '#F62440',
  'accent-text': '#D81B36',
  ink: '#2A2420',
  muted: '#7A6F66',
  'border-strong': '#E8CFA6',
  ok: '#2F7D5B',
};

const inkScale = {
  50: palette.surface,
  100: palette.ink,
  200: palette.ink,
  300: palette.ink,
  400: palette.muted,
  500: palette.muted,
  600: palette.muted,
  700: palette['border-strong'],
  800: palette.soft,
  900: palette.surface,
  950: palette.bg,
};

const accentScale = {
  50: palette.soft,
  100: palette.soft,
  200: palette.soft,
  300: palette['accent-text'],
  400: palette['accent-text'],
  500: palette.accent,
  600: palette.accent,
  700: palette.accent,
  800: palette['accent-text'],
  900: palette.ink,
  950: palette.ink,
};

const okScale = {
  50: palette.surface,
  100: palette.soft,
  200: palette.soft,
  300: palette.ok,
  400: palette.ok,
  500: palette.ok,
  600: palette.ok,
  700: palette.ok,
  800: palette.ok,
  900: palette.ink,
  950: palette.ink,
};

const noneShadow = {
  sm: 'none',
  DEFAULT: 'none',
  md: 'none',
  lg: 'none',
  xl: 'none',
  '2xl': 'none',
  inner: 'none',
};

export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        ...palette,
        slate: inkScale,
        gray: inkScale,
        zinc: inkScale,
        neutral: inkScale,
        stone: inkScale,
        sentinel: accentScale,
        rose: accentScale,
        red: accentScale,
        pink: accentScale,
        cyan: accentScale,
        sky: accentScale,
        blue: accentScale,
        indigo: accentScale,
        violet: accentScale,
        purple: accentScale,
        fuchsia: accentScale,
        orange: accentScale,
        amber: {
          ...accentScale,
          50: palette.soft,
          200: palette.soft,
          300: palette.muted,
          400: palette.muted,
        },
        yellow: {
          ...accentScale,
          400: palette.muted,
        },
        emerald: okScale,
        green: okScale,
        teal: okScale,
        lime: okScale,
        black: palette.surface,
        aicte: {
          navy: palette.ink,
          saffron: palette.accent,
          gold: palette.soft,
          crimson: palette.accent,
          emerald: palette.ok,
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Consolas', 'monospace'],
      },
      maxWidth: {
        '7xl': '1200px',
      },
      borderRadius: {
        sm: '8px',
        DEFAULT: '8px',
        md: '8px',
        lg: '8px',
        xl: '8px',
        '2xl': '8px',
      },
      boxShadow: noneShadow,
      dropShadow: noneShadow,
    },
  },
  plugins: [],
}
