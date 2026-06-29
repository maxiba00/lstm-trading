/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0f1117",
        surface: "#1a1d27",
        border: "#2a2d3a",
        accent: "#6366f1",
        "accent-light": "#818cf8",
        long: "#22c55e",
        short: "#ef4444",
        hold: "#64748b",
      },
    },
  },
  plugins: [],
};
