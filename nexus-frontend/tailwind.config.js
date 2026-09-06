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
        nexus: {
          yellow: {
            DEFAULT: '#FFB800',
            hover: '#E5A600',
            light: '#FDE68A',
            glow: 'rgba(255, 184, 0, 0.25)',
          },
          blue: {
            DEFAULT: '#2563EB',
            dark: '#1D4ED8',
            deep: '#1E40AF',
            navy: '#0F172A',
            darker: '#0B0F19',
          },
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        display: ['Montserrat', 'Inter', 'sans-serif'],
      },
      boxShadow: {
        'nexus-card': '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
        'nexus-glow': '0 0 25px rgba(255, 184, 0, 0.15)',
        'nexus-blue-glow': '0 0 25px rgba(37, 99, 235, 0.25)',
      },
    },
  },
  plugins: [],
}
