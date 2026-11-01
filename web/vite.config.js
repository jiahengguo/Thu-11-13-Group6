import { defineConfig } from 'vite';
import { fileURLToPath } from 'node:url';

export default defineConfig({
  // Runtime configuration stays on the Python server, never in the frontend bundle.
  envDir: false,
  define: { 'process.env.NODE_ENV': JSON.stringify('production') },
  build: {
    outDir: fileURLToPath(new URL('../src/tripmate/portal/static', import.meta.url)),
    emptyOutDir: false,
    target: 'es2020',
    minify: true,
    lib: {
      entry: fileURLToPath(new URL('./src/queue-entry.jsx', import.meta.url)),
      name: 'TripMateQueue',
      formats: ['iife'],
      fileName: () => 'portal-queue.js',
    },
  },
});
