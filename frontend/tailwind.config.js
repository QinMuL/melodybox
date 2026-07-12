/** @type {import('tailwindcss').Config} */

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    container: {
      center: true,
    },
    extend: {
      colors: {
        // 主色：亮色用绿色（QQ 音乐），暗色用红色（网易云）
        // 通过 CSS 变量切换，支持透明度修饰符（如 primary/10）
        primary: {
          DEFAULT: "rgb(var(--color-primary) / <alpha-value>)",
          50: "rgb(var(--color-primary-50) / <alpha-value>)",
          100: "rgb(var(--color-primary-100) / <alpha-value>)",
          200: "rgb(var(--color-primary-200) / <alpha-value>)",
          300: "rgb(var(--color-primary-300) / <alpha-value>)",
          400: "rgb(var(--color-primary-400) / <alpha-value>)",
          500: "rgb(var(--color-primary-500) / <alpha-value>)",
          600: "rgb(var(--color-primary-600) / <alpha-value>)",
          700: "rgb(var(--color-primary-700) / <alpha-value>)",
          800: "rgb(var(--color-primary-800) / <alpha-value>)",
          900: "rgb(var(--color-primary-900) / <alpha-value>)",
        },
        // 浅色主题
        surface: {
          light: "#F5F5F7",
          card: "#FFFFFF",
          hover: "#F0F0F2",
          border: "#E5E5E7",
        },
        // 深色主题（仿网易云音乐：背景柔和深灰，避免纯黑刺眼）
        dark: {
          DEFAULT: "#1F1F1F",   // 主背景（网易云主色）
          card: "#2C2C2C",      // 卡片背景
          hover: "#333333",     // 悬停色
          border: "#383838",    // 边框
          light: "#383838",     // 浅一档（用于阴影边缘）
        },
        // 文字
        ink: {
          primary: "#333333",       // 浅色主文字
          secondary: "#666666",
          muted: "#999999",
          light: "#E5E5E5",         // 暗色主文字（避免纯白刺眼，仿网易云）
          lightSecondary: "#A0A0A0",
          lightMuted: "#707070",
        },
      },
      fontFamily: {
        sans: [
          "PingFang SC",
          "HarmonyOS Sans",
          "Microsoft YaHei",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif",
        ],
        mono: ["DIN Alternate", "SF Pro Display", "Roboto Mono", "monospace"],
      },
      borderRadius: {
        pill: "9999px",
      },
      boxShadow: {
        card: "0 2px 12px rgba(0, 0, 0, 0.06)",
        cardHover: "0 8px 24px rgba(0, 0, 0, 0.1)",
        primary: "0 4px 16px rgb(var(--color-primary) / 0.3)",
        glow: "0 0 20px rgb(var(--color-primary) / 0.4)",
      },
      backgroundImage: {
        // 主色渐变：通过 CSS 变量自动适配亮色绿/暗色红
        "primary-gradient": "linear-gradient(135deg, rgb(var(--color-primary-400)) 0%, rgb(var(--color-primary-600)) 100%)",
        "primary-gradient-hover":
          "linear-gradient(135deg, rgb(var(--color-primary-500)) 0%, rgb(var(--color-primary-700)) 100%)",
      },
      animation: {
        "fade-in": "fadeIn 0.3s ease-out",
        "slide-up": "slideUp 0.4s ease-out",
        "shimmer": "shimmer 2s linear infinite",
        "ripple": "ripple 0.6s ease-out",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        ripple: {
          "0%": { transform: "scale(0)", opacity: "0.6" },
          "100%": { transform: "scale(4)", opacity: "0" },
        },
      },
    },
  },
  plugins: [],
};
