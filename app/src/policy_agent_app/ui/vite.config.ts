import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Build the SPA into ``dist``; the FastAPI backend serves that directory at "/".
// During development, API calls are proxied to the local uvicorn process.
export default defineConfig({
  plugins: [react()],
  build: { outDir: "dist" },
  server: {
    proxy: {
      "/api": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
});
