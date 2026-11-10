import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Dentro de Docker el backend se resuelve por nombre de servicio
      "/api": process.env.VITE_API_PROXY ?? "http://backend:8000",
    },
  },
});
