/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'telus-purple': '#4B0082',
        'telus-green': '#66CC00',
        'telus-blue': '#0066CC',
        'telus-light-purple': '#8A2BE2',
        'telus-dark-purple': '#2E0054',
      }
    }
  },
  plugins: []
}
