import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// A static single-page site. No backend, no analytics, no third-party scripts:
// a project whose entire argument is "we do not overclaim" should not ship a
// tracking pixel it has to explain.
export default defineConfig({
  plugins: [react()],
  base: './',
  build: {
    outDir: 'dist',
    sourcemap: true,
    target: 'es2022',
    assetsInlineLimit: 0,
  },
  server: {
    port: 4173,
  },
});
