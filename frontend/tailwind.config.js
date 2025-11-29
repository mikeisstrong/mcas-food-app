export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        'confidence-low': '#fca5a5',
        'confidence-medium': '#86efac',
        'confidence-high': '#22c55e',
      }
    },
  },
  plugins: [],
}
