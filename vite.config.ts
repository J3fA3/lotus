import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";

// Configuration constants
const SERVER_PORT = 8080;
const API_PROXY_TARGET = "http://localhost:8000";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  server: {
    host: "::",
    port: SERVER_PORT,
    proxy: {
      "/api": {
        target: API_PROXY_TARGET,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path,
      },
    },
    fs: {
      // Exclude backend directory from Vite's file system access
      deny: ['**/backend/**'],
    },
  },
  optimizeDeps: {
    // Exclude backend directory from dependency optimization
    exclude: ['backend'],
    entries: ['src/**/*.tsx', 'src/**/*.ts', 'index.html'],
  },
  plugins: [
    react(),
    mode === "development" && componentTagger(),
  ].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    sourcemap: mode === "development",
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ["react", "react-dom", "react-router-dom"],
          ui: ["@radix-ui/react-dialog", "@radix-ui/react-select"],
        },
      },
    },
  },
}));
