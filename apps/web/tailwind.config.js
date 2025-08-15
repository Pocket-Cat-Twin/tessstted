/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#fef9f6',
          100: '#fef2ed',
          200: '#fcd9cc',
          300: '#f9b5a0',
          400: '#f48b73',
          500: '#efb0b6',
          600: '#e6928f',
          700: '#d97370',
          800: '#c85d5f',
          900: '#b44b4d',
          950: '#a03d3f'
        },
        secondary: {
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
          950: '#020617'
        },
        kawaii: {
          pink: '#ffd6e8',
          lavender: '#e6d9f5',
          peach: '#ffd6cc',
          cream: '#fef9f6',
          mint: '#d4f5e8',
          sky: '#e0f2fe'
        },
        coffee: {
          50: '#FAF7F4',
          100: '#F5E6D3',
          200: '#E8D5C4',
          300: '#C4A59A',
          400: '#A67C6A',
          500: '#8B4A42',
          600: '#6B3A33',
          700: '#4A2B25',
          800: '#3C251E',
          900: '#2D1C16',
          950: '#1E130E'
        }
      },
      fontFamily: {
        'sans': ['Bona Nova', 'serif'],
        'kawaii': ['Bona Nova', 'serif'],
        'body': ['Bona Nova', 'serif'],
        'serif': ['Bona Nova', 'serif'],
        'mono': ['JetBrains Mono', 'monospace']
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-up': 'slideUp 0.5s ease-out',
        'slide-down': 'slideDown 0.5s ease-out',
        'bounce-gentle': 'bounceGentle 2s infinite',
        'pulse-soft': 'pulseSoft 2s infinite'
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' }
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' }
        },
        slideDown: {
          '0%': { opacity: '0', transform: 'translateY(-20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' }
        },
        bounceGentle: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-5px)' }
        },
        pulseSoft: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' }
        }
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem'
      },
      screens: {
        'xs': '475px'
      }
    }
  },
  plugins: [
    require('@tailwindcss/typography')
  ]
};