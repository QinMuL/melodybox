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
        // QQ 音乐主色调
        primary: {
          DEFAULT: "#31C27C",
          50: "#E8FAF0",
          100: "#D1F4E1",
          200: "#A3E9C4",
          300: "#75DDA6",
          400: "#47D288",
          500: "#31C27C",
          600: "#27A864",
          700: "#1FD1A1",
          800: "#1BA880",
          900: "#168566",
        },
        // 浅色主题
        surface: {
          light: "#F5F5F7",
          card: "#FFFFFF",
          hover: "#F0F0F2",
          border: "#E5E5E7",
        },
        // 深色主题
        dark: {
          DEFAULT: "#1A1A1A",
          card: "#2A2A2A",
          hover: "#333333",
          border: "#3A3A3A",
        },
        // 文字
        ink: {
          primary: "#333333",
          secondary: "#666666",
          muted: "#999999",
          light: "#FFFFFF",
          lightSecondary: "#CCCCCC",
          lightMuted: "#888888",
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
        primary: "0 4px 16px rgba(49, 194, 124, 0.3)",
        glow: "0 0 20px rgba(49, 194, 124, 0.4)",
      },
      backgroundImage: {
        "primary-gradient": "linear-gradient(135deg, #31C27C 0%, #1FD1A1 100%)",
        "primary-gradient-hover":
          "linear-gradient(135deg, #27A864 0%, #1BA880 100%)",
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
