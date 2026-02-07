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
        // ============================================
        // SALESFORCE LIGHTNING DESIGN SYSTEM COLORS
        // ============================================

        // Primary Brand Colors (Salesforce Blue)
        'slds-brand': {
          DEFAULT: '#0176D3',
          light: '#1B96FF',
          dark: '#014486',
          darker: '#032D60',
        },

        // Semantic Colors
        'slds-success': {
          DEFAULT: '#2E844A',
          light: '#45C65A',
          dark: '#1E5631',
        },
        'slds-warning': {
          DEFAULT: '#DD7A01',
          light: '#FE9339',
          dark: '#A96404',
        },
        'slds-error': {
          DEFAULT: '#C23934',
          light: '#EA001E',
          dark: '#8E0000',
        },
        'slds-info': {
          DEFAULT: '#0176D3',
          light: '#1B96FF',
          dark: '#014486',
        },

        // Background Colors
        'slds-bg': {
          page: '#F3F3F3',
          card: '#FFFFFF',
          section: '#FAFAFA',
          inverse: '#16325C',
          highlight: '#F3F3F3',
          wash: '#E5E5E5',
        },

        // Text Colors
        'slds-text': {
          DEFAULT: '#181818',
          weak: '#706E6B',
          inverse: '#FFFFFF',
          link: '#0176D3',
          'link-hover': '#014486',
          placeholder: '#939393',
        },

        // Border Colors
        'slds-border': {
          DEFAULT: '#E5E5E5',
          strong: '#C9C9C9',
          separator: '#DDDBDA',
          focus: '#0176D3',
          error: '#C23934',
        },

        // ============================================
        // TRUELOG EXTENDED PALETTE (SLDS-compatible)
        // ============================================

        // Primary palette (aligned with SLDS brand)
        primary: {
          50: '#E5F2FC',
          100: '#C2E1F9',
          200: '#8DC8F4',
          300: '#57AFEE',
          400: '#1B96FF',
          500: '#0176D3',  // SLDS Brand Default
          600: '#0161B3',
          700: '#014486',
          800: '#032D60',
          900: '#021B3A',
          950: '#010F20',
        },

        // Secondary accent (purple - for special highlights)
        secondary: {
          50: '#F3E8FF',
          100: '#E9D5FF',
          200: '#D8B4FE',
          300: '#C084FC',
          400: '#A855F7',
          500: '#9333EA',
          600: '#7E22CE',
          700: '#6B21A8',
          800: '#581C87',
          900: '#3B0764',
          950: '#2E1065',
        },

        // Success (SLDS-aligned green)
        success: {
          50: '#EBF7EE',
          100: '#CFF0D6',
          200: '#A3E3B3',
          300: '#6DD28A',
          400: '#45C65A',
          500: '#2E844A',  // SLDS Success Default
          600: '#256B3B',
          700: '#1E5631',
          800: '#164123',
          900: '#0F2C17',
          950: '#081A0E',
        },

        // Warning (SLDS-aligned orange)
        warning: {
          50: '#FFF5E6',
          100: '#FFE8C2',
          200: '#FED18C',
          300: '#FEB856',
          400: '#FE9339',
          500: '#DD7A01',  // SLDS Warning Default
          600: '#B86401',
          700: '#A96404',
          800: '#6D4001',
          900: '#462800',
          950: '#2C1900',
        },

        // Danger/Error (SLDS-aligned red)
        danger: {
          50: '#FEF1F0',
          100: '#FEDCDA',
          200: '#FCBAB5',
          300: '#FA8F87',
          400: '#F76359',
          500: '#C23934',  // SLDS Error Default
          600: '#A32D28',
          700: '#8E0000',
          800: '#5C0000',
          900: '#3D0000',
          950: '#270000',
        },

        // Neutral grays (SLDS-aligned)
        gray: {
          50: '#FAFAFA',
          100: '#F3F3F3',
          200: '#E5E5E5',
          300: '#DDDBDA',
          400: '#C9C9C9',
          500: '#939393',
          600: '#706E6B',
          700: '#514F4D',
          800: '#3A3A3A',
          900: '#181818',
          950: '#0F0F0F',
        },

        // Object-specific colors (for icons/badges)
        'slds-asset': '#747474',
        'slds-case': '#F2CF5B',
        'slds-account': '#7F8DE1',
        'slds-contact': '#A094ED',
        'slds-opportunity': '#FCB95B',
        'slds-lead': '#F88962',
        'slds-task': '#4BC076',
        'slds-event': '#EB7092',

        // TrueLog Brand Colors
        truelog: {
          light: '#A5C5E9',
          DEFAULT: '#7BA7DE',
          dark: '#5089D3',
        },

        // Salesforce Blue (for branding consistency)
        'sf-blue': '#0176d3',
      },

      fontFamily: {
        sans: [
          'Salesforce Sans',
          'Inter',
          'system-ui',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'Roboto',
          'Helvetica Neue',
          'Arial',
          'sans-serif',
        ],
        mono: [
          'JetBrains Mono',
          'SF Mono',
          'Fira Code',
          'Consolas',
          'Monaco',
          'monospace',
        ],
      },

      fontSize: {
        // SLDS Type Scale
        'display': ['2rem', { lineHeight: '1.25', letterSpacing: '-0.02em', fontWeight: '700' }],
        'heading-1': ['1.5rem', { lineHeight: '1.25', letterSpacing: '-0.01em', fontWeight: '700' }],
        'heading-2': ['1.25rem', { lineHeight: '1.25', letterSpacing: '0', fontWeight: '700' }],
        'heading-3': ['1rem', { lineHeight: '1.5', letterSpacing: '0', fontWeight: '700' }],
        'body': ['0.875rem', { lineHeight: '1.5', letterSpacing: '0', fontWeight: '400' }],
        'body-small': ['0.75rem', { lineHeight: '1.5', letterSpacing: '0', fontWeight: '400' }],
        'caption': ['0.6875rem', { lineHeight: '1.5', letterSpacing: '0.02em', fontWeight: '400' }],
      },

      spacing: {
        // SLDS Spacing Scale (4px base unit)
        'slds-0': '0',
        'slds-1': '0.125rem',   // 2px
        'slds-2': '0.25rem',    // 4px
        'slds-3': '0.5rem',     // 8px
        'slds-4': '0.75rem',    // 12px
        'slds-5': '1rem',       // 16px
        'slds-6': '1.5rem',     // 24px
        'slds-7': '2rem',       // 32px
        'slds-8': '3rem',       // 48px
        'slds-9': '4rem',       // 64px
        'slds-10': '5rem',      // 80px
      },

      boxShadow: {
        // SLDS Shadows
        'slds-card': '0 2px 2px 0 rgba(0, 0, 0, 0.05)',
        'slds-card-hover': '0 4px 8px 0 rgba(0, 0, 0, 0.08)',
        'slds-dropdown': '0 2px 3px 0 rgba(0, 0, 0, 0.16)',
        'slds-modal': '0 2px 16px 0 rgba(0, 0, 0, 0.22)',
        'slds-popover': '0 2px 8px 0 rgba(0, 0, 0, 0.16)',
        'slds-focus': '0 0 3px #0176D3',
        // Legacy glass effects (for progressive enhancement)
        'glass': '0 25px 45px -12px rgba(0, 0, 0, 0.35), 0 10px 15px -3px rgba(0, 0, 0, 0.2)',
        'glass-hover': '0 32px 64px -12px rgba(0, 0, 0, 0.4), 0 15px 25px -5px rgba(0, 0, 0, 0.25)',
        // Primary button shadows
        'primary': '0 4px 8px rgba(1, 118, 211, 0.3)',
        'primary-hover': '0 8px 16px rgba(1, 118, 211, 0.4)',
      },

      borderRadius: {
        'slds': '0.25rem',       // 4px - SLDS default
        'slds-sm': '0.125rem',   // 2px
        'slds-md': '0.375rem',   // 6px
        'slds-lg': '0.5rem',     // 8px
        'slds-full': '9999px',   // Pills/badges
        // Legacy
        'glass': '24px',
        'button': '16px',
      },

      borderWidth: {
        'slds': '1px',
        'slds-thick': '2px',
      },

      maxWidth: {
        'slds-container': '1280px',
        'slds-narrow': '960px',
        'slds-wide': '1440px',
        'slds-modal-sm': '400px',
        'slds-modal-md': '640px',
        'slds-modal-lg': '960px',
      },

      minHeight: {
        'slds-input': '2rem',       // 32px
        'slds-input-sm': '1.5rem',  // 24px
        'slds-input-lg': '2.5rem',  // 40px
        'slds-button': '2rem',      // 32px
        'slds-button-sm': '1.5rem', // 24px
        'slds-button-lg': '2.5rem', // 40px
        'slds-touch': '2.75rem',    // 44px - touch target
      },

      backdropBlur: {
        'glass': '20px',
      },

      animation: {
        'fade-in': 'fadeIn 0.2s ease-out',
        'fade-out': 'fadeOut 0.2s ease-out',
        'slide-up': 'slideUp 0.2s ease-out',
        'slide-down': 'slideDown 0.2s ease-out',
        'slide-in-right': 'slideInRight 0.2s ease-out',
        'slide-in-left': 'slideInLeft 0.2s ease-out',
        'scale-in': 'scaleIn 0.2s ease-out',
        'spin-slow': 'spin 2s linear infinite',
      },

      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        fadeOut: {
          '0%': { opacity: '1' },
          '100%': { opacity: '0' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        slideDown: {
          '0%': { transform: 'translateY(-10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        slideInRight: {
          '0%': { transform: 'translateX(20px)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        slideInLeft: {
          '0%': { transform: 'translateX(-20px)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        scaleIn: {
          '0%': { transform: 'scale(0.95)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
      },

      transitionDuration: {
        'slds-fast': '100ms',
        'slds-normal': '200ms',
        'slds-slow': '400ms',
      },

      zIndex: {
        'slds-dropdown': '7000',
        'slds-modal': '9000',
        'slds-popover': '6000',
        'slds-spinner': '9050',
        'slds-toast': '10000',
      },
    },
  },
  plugins: [],
}
