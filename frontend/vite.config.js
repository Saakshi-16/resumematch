import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// During development React runs on port 5173 and Django on port 8000.
// The "proxy" below sends every /api request from React to Django,
// so the two talk to each other without any extra setup.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
});
