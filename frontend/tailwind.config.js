/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: { 950: '#090D11', 900: '#0E1419', 850: '#121A21', 800: '#18222B', 700: '#243040', 600: '#334357' },
        fog: { 100: '#E9EDF1', 300: '#B4BEC9', 500: '#8794A3', 600: '#7F8C99' },
        accent: 'rgb(var(--accent) / <alpha-value>)',
        up: '#5FD39A', down: '#F0646E', warn: '#F0B35A', model: '#9FB4FF',
      },
      fontFamily: {
        sans: ['"Instrument Sans Variable"', 'system-ui', 'sans-serif'],
        num: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      keyframes: { pulseDot: { '0%,100%': { opacity: '1' }, '50%': { opacity: '.35' } } },
      animation: { pulseDot: 'pulseDot 1.6s ease-in-out infinite' },
    },
  },
  plugins: [],
}
