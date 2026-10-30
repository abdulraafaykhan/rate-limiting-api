import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Keep browser requests same-origin; credentials never live in Vite env files.
const target = process.env.API_PROXY_TARGET || "http://127.0.0.1:8001";
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": target,
      "/health": target,
      "/docs": target,
      "/openapi.json": target,
    },
  },
  preview: {
    proxy: {
      "/api": target,
      "/health": target,
      "/docs": target,
      "/openapi.json": target,
    },
  },
});
