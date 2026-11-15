/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        linen: {
          canvas: '#fbf9f4',
          surface: '#ffffff',
          surfaceAlt: '#f5efe6',
          border: '#e8e1d5',
          borderSubtle: '#f0e9df',
          text: '#2b2622',
          muted: '#7c746d',
          codeBg: '#f0e7db',
          codeText: '#6b5344',
          accent: '#2b2622',
          accentHover: '#423b35',
          userBubble: '#f3ece2',
          link: '#1d4ed8'
        }
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'Inter', 'Helvetica', 'Arial', 'sans-serif']
      }
    },
  },
  plugins: [],
}
