import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
    plugins: [react()],
    server: {
        port: 4000,
        proxy: {
            '/api': 'http://ai-studio-server:8020'
        }
    },
    build: {
        outDir: 'dist',
        sourcemap: true
    }
})
