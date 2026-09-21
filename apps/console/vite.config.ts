import react from '@vitejs/plugin-react';
// `vitest/config` re-exports Vite's `defineConfig` with the `test` key typed, so
// the test configuration lives here rather than in a second config file.
import { defineConfig } from 'vitest/config';

// The dev server proxies /api to the Python service so the browser makes
// same-origin requests. That avoids needing CORS at all in development, and it
// means the console cannot accidentally ship with a hard-coded backend host.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: false,
    proxy: {
      '/api': {
        target: process.env.CS_API_PROXY ?? 'http://127.0.0.1:8080',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
        ws: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    target: 'es2022',
  },
  test: {
    globals: true,
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
});
