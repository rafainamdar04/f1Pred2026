/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'f1-bg': '#080808',
        'f1-card': '#111111',
        'f1-border': 'rgba(255,255,255,0.07)',
        'f1-red': '#E10600',
        'f1-text': '#FFFFFF',
        'f1-muted': '#777777',
        'f1-cyan': '#27F4D2',
      },
      borderRadius: {
        'f1': '4px',
      },
      fontFamily: {
        barlow: ['Barlow Condensed', 'sans-serif'],
        dm: ['DM Sans', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
