import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  content: ["./pages/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./app/**/*.{ts,tsx}", "./src/**/*.{ts,tsx}"],
  prefix: "",
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
      },
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
          hover: "hsl(var(--card-hover))",
        },
        column: {
          bg: "hsl(var(--column-bg))",
        },
        sidebar: {
          DEFAULT: "hsl(var(--sidebar-background))",
          foreground: "hsl(var(--sidebar-foreground))",
          primary: "hsl(var(--sidebar-primary))",
          "primary-foreground": "hsl(var(--sidebar-primary-foreground))",
          accent: "hsl(var(--sidebar-accent))",
          "accent-foreground": "hsl(var(--sidebar-accent-foreground))",
          border: "hsl(var(--sidebar-border))",
          ring: "hsl(var(--sidebar-ring))",
        },
      },
      transitionProperty: {
        smooth: "var(--transition-smooth)",
      },
      transitionTimingFunction: {
        "butter": "cubic-bezier(0.4, 0, 0.2, 1)",
        "feng-shui": "cubic-bezier(0.16, 1, 0.3, 1)",
      },
      letterSpacing: {
        tight: '-0.011em',
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      keyframes: {
        "accordion-down": {
          from: {
            height: "0",
          },
          to: {
            height: "var(--radix-accordion-content-height)",
          },
        },
        "accordion-up": {
          from: {
            height: "var(--radix-accordion-content-height)",
          },
          to: {
            height: "0",
          },
        },
        "view-morph-in": {
          from: {
            opacity: "0",
            transform: "scale(0.98)",
          },
          to: {
            opacity: "1",
            transform: "scale(1)",
          },
        },
        "view-morph-out": {
          from: {
            opacity: "1",
            transform: "scale(1)",
          },
          to: {
            opacity: "0",
            transform: "scale(0.98)",
          },
        },
        "view-expand": {
          from: {
            width: "var(--from-width)",
            maxWidth: "var(--from-max-width)",
          },
          to: {
            width: "var(--to-width)",
            maxWidth: "var(--to-max-width)",
          },
        },
        "view-contract": {
          from: {
            width: "var(--from-width)",
            maxWidth: "var(--from-max-width)",
          },
          to: {
            width: "var(--to-width)",
            maxWidth: "var(--to-max-width)",
          },
        },
        "task-slide-in": {
          "0%": {
            opacity: "0",
            transform: "translateY(-12px) scale(0.96)",
          },
          "100%": {
            opacity: "1",
            transform: "translateY(0) scale(1)",
          },
        },
        "task-pulse": {
          "0%, 100%": {
            opacity: "1",
          },
          "50%": {
            opacity: "0.85",
          },
        },
        "task-shift-down": {
          "0%": {
            transform: "translateY(0)",
          },
          "30%": {
            transform: "translateY(12px)",
          },
          "100%": {
            transform: "translateY(0)",
          },
        },
        "column-pulse": {
          "0%": {
            transform: "scale(1)",
            opacity: "1",
          },
          "50%": {
            transform: "scale(1.005)",
            opacity: "0.95",
          },
          "100%": {
            transform: "scale(1)",
            opacity: "1",
          },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "view-morph-in": "view-morph-in 0.4s cubic-bezier(0.16, 1, 0.3, 1)",
        "view-morph-out": "view-morph-out 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
        "view-expand": "view-expand 0.4s cubic-bezier(0.4, 0, 0.2, 1)",
        "view-contract": "view-contract 0.4s cubic-bezier(0.4, 0, 0.2, 1)",
        "task-slide-in": "task-slide-in 0.5s cubic-bezier(0.16, 1, 0.3, 1)",
        "task-pulse": "task-pulse 1.5s ease-in-out",
        "task-shift-down": "task-shift-down 0.5s cubic-bezier(0.16, 1, 0.3, 1)",
        "column-pulse": "column-pulse 1.2s ease-in-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate"), require("@tailwindcss/typography")],
} satisfies Config;
