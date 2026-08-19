import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Printoka brand — primary accent is the live site's signature red (#E52220).
        brand: {
          50: "#fef3f2",
          100: "#fde3e1",
          200: "#fbccc9",
          300: "#f7a8a3",
          400: "#f0766e",
          500: "#e52220", // Printoka red — CTAs, links, highlights
          600: "#cc1d1b",
          700: "#a91816",
          800: "#8a1614",
          900: "#731817",
          950: "#3e0908",
        },
        // The rainbow-logo palette (Brand Guideline) — used sparingly for accents / illustration.
        accent: {
          orange: "#ff5a00",
          gold: "#ffc400",
          teal: "#00c2bb",
          blue: "#2962ff",
        },
        surface: {
          DEFAULT: "#ffffff",
          muted: "#fafafa",
          subtle: "#f5f5f5",
        },
        ink: {
          DEFAULT: "#212121", // live site body text
          secondary: "#424242",
          muted: "#616161", // live site secondary text
          subtle: "#9e9e9e",
        },
        border: {
          DEFAULT: "#e0e0e0",
          strong: "#bdbdbd",
        },
      },
      fontFamily: {
        sans: ["Montserrat", "system-ui", "sans-serif"],
        display: ["Montserrat", "system-ui", "sans-serif"],
      },
      boxShadow: {
        "card": "0 1px 3px 0 rgb(0 0 0 / 0.05), 0 1px 2px -1px rgb(0 0 0 / 0.05)",
        "card-hover": "0 4px 12px 0 rgb(0 0 0 / 0.08), 0 2px 4px -2px rgb(0 0 0 / 0.06)",
        "panel": "0 0 0 1px rgb(0 0 0 / 0.05), 0 2px 8px 0 rgb(0 0 0 / 0.06)",
        "dialog": "0 20px 60px -10px rgb(0 0 0 / 0.15)",
        "price": "0 0 0 1px rgb(229 34 32 / 0.18), 0 4px 16px 0 rgb(229 34 32 / 0.08)",
      },
      borderRadius: {
        "4xl": "2rem",
      },
      animation: {
        "fade-in": "fade-in 0.3s ease-out",
        "slide-up": "slide-up 0.3s ease-out",
        "slide-down": "slide-down 0.3s ease-out",
        "scale-in": "scale-in 0.2s ease-out",
        "price-tick": "price-tick 0.4s ease-out",
        "shimmer": "shimmer 1.5s infinite",
        "spin-slow": "spin 3s linear infinite",
      },
      keyframes: {
        "fade-in": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        "slide-up": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "slide-down": {
          from: { opacity: "0", transform: "translateY(-8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "scale-in": {
          from: { opacity: "0", transform: "scale(0.96)" },
          to: { opacity: "1", transform: "scale(1)" },
        },
        "price-tick": {
          "0%": { transform: "translateY(-4px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
        "shimmer": {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
