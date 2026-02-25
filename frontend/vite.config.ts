import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiTarget = process.env.VITE_API_URL || "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  build: {
    assetsDir: "static",
    outDir: "dist",
  },
  server: {
    port: 5173,
    proxy: {
      "/api": apiTarget,
      "/v1": apiTarget,
      "/assets": apiTarget,
    },
  },
});
