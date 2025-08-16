import { sveltekit } from "@sveltejs/kit/vite";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [sveltekit()],
  server: {
    port: 5173,
    host: "0.0.0.0",
    strictPort: true,
    hmr: {
      port: 5173
    },
    cors: true,
    headers: {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization"
    }
  },
  preview: {
    port: 4173,
    host: "0.0.0.0",
    strictPort: true
  },
  build: {
    sourcemap: true,
    rollupOptions: {
      onwarn: (warning, warn) => {
        if (warning.code === 'UNRESOLVED_IMPORT') return;
        warn(warning);
      }
    }
  }
});
