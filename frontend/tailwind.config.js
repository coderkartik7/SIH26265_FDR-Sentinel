/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        sentinel: {
          50: '#f0f7ff',
          100: '#e0effe',
          200: '#bae0fd',
          300: '#7cc7fb',
          400: '#38a9f6',
          500: '#0e8ce8',
          600: '#026fc6',
          700: '#0358a0',
          800: '#074b83',
          900: '#0b3f6d',
          950: '#072849',
        },
        aicte: {
          navy: '#0b1d3a',
          saffron: '#ff7722',
          gold: '#f59e0b',
          crimson: '#dc2626',
          emerald: '#059669',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
