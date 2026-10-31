import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('.', import.meta.url));

export default defineConfig({
  plugins: [react()],
  base: '/login-app/',
  build: {
    outDir: '../ui-console/public/login-app',
    emptyOutDir: true,
    rollupOptions: {
      input: [resolve(root, 'index.html'), resolve(root, 'index-no-gate.html')],
    },
  },
  server: { port: 3001 },
});
