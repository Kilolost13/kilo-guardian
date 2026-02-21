/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'zombie-green': '#39FF14',
        'terminal-green': '#2dd10d',
        'dark-bg': '#050505',
        'zombie-dark': '#050505',
        'dark-card': '#1a1a1a',
        'dark-border': '#2a2a2a',
        'neon-blue': '#00d9ff',
        'neon-purple': '#b842ff',
        'neon-pink': '#ff006e',
        'blood-red': '#ff0033',
      },
      fontFamily: {
        'mono': ['Share Tech Mono', 'Courier New', 'monospace'],
        'terminal': ['Share Tech Mono', 'monospace'],
        'header': ['Orbitron', 'sans-serif'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
        'scanline': 'scanline 10s linear infinite',
        'pulse-red': 'pulse 1s infinite',
      },
      keyframes: {
        glow: {
          '0%': { textShadow: '0 0 5px #39FF14, 0 0 10px #39FF14' },
          '100%': { textShadow: '0 0 10px #39FF14, 0 0 20px #39FF14, 0 0 30px #39FF14' },
        },
        scanline: {
          '0%': { bottom: '100%' },
          '100%': { bottom: '-100%' },
        },
      },
      backgroundImage: {
        'zombie-gradient': 'linear-gradient(135deg, #050505 0%, #1a1a1a 50%, #050505 100%)',
        'terminal-gradient': 'linear-gradient(to bottom, #050505, #1a1a1a)',
        'grid': 'linear-gradient(rgba(57, 255, 20, 0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(57, 255, 20, 0.08) 1px, transparent 1px)',
      },
      backgroundSize: {
        'grid': '20px 20px',
      },
    },
  },
  plugins: [],
}
