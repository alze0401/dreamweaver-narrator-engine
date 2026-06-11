/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // 织梦绮谭 - 精致二次元暗色主题
        primary: {
          DEFAULT: '#a882ff',    // 梦幻紫
          light: '#c4b5fd',
          dark: '#7c3aed',
        },
        accent: {
          DEFAULT: '#f472b6',    // 樱花粉
          light: '#f9a8d4',
          dark: '#ec4899',
        },
        surface: {
          DEFAULT: '#1a1625',    // 主背景 (深紫黑)
          light: '#252036',      // 浅背景
          dark: '#0c0a15',       // 最深背景
          card: '#1e1a2e',       // 卡片背景
        },
        text: {
          DEFAULT: '#ddd8f0',    // 主文本
          dim: '#7e7a96',        // 次要文本
          bright: '#ffffff',     // 高亮文本
          accent: '#c4b5fd',     // 紫色强调文本
        },
      },
      fontFamily: {
        sans: ['"Noto Sans SC"', '"Noto Sans JP"', 'system-ui', 'sans-serif'],
        serif: ['"Noto Serif SC"', '"Noto Serif JP"', 'Georgia', 'serif'],
        display: ['"Noto Serif SC"', '"Noto Sans SC"', 'serif'],
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-out',
        'fade-in-scale': 'fadeInScale 0.5s ease-out',
        'slide-up': 'slideUp 0.5s cubic-bezier(0.16, 1, 0.3, 1)',
        'float': 'float 6s ease-in-out infinite',
        'glow-pulse': 'glowPulse 6s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        fadeInScale: {
          '0%': { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(24px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-12px)' },
        },
        glowPulse: {
          '0%, 100%': { opacity: '0.4' },
          '50%': { opacity: '0.7' },
        },
      },
    },
  },
  plugins: [],
}
