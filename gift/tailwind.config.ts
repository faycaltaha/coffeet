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
        brand: {
          50:  "#FEFCF8",
          100: "#FCF7EE",
          200: "#F8ECE0",
          300: "#F0D4BB",
          400: "#E4B08A",
          500: "#C88B5C",
          600: "#A06840",
          700: "#7A4D28",
          800: "#553416",
          900: "#2D1A06",
        },
      },
    },
  },
  plugins: [],
};

export default config;
