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
        agent: {
          900: '#000000',
          800: '#111111',
          700: '#222222',
          600: '#333333',
          accent: '#3b82f6',
          warning: '#f59e0b',
          alert: '#ef4444',
        }
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      animation: {
        'spin-slow': 'spin 8s linear infinite',
        'pulse-glow': 'pulseGlow 3s ease-in-out infinite',
      },
      keyframes: {
        pulseGlow: {
          '0%, 100%': { opacity: 0.5, transform: 'scale(1)' },
          '50%': { opacity: 1, transform: 'scale(1.05)', filter: 'drop-shadow(0 0 20px rgba(59,130,246,0.5))' },
        }
      }
    },
  },
  plugins: [],
}
