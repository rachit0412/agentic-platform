import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react()],
  base: '/login-app/',
  build: {
    outDir: '../ui-console/public/login-app',
    emptyOutDir: true,
  },
  server: { port: 3001 },
});
