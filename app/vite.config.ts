import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'
import { servePrivateData } from './vite.privateData.ts'

const dataDir = path.resolve(import.meta.dirname, '../data')

export default defineConfig({
  plugins: [vue(), tailwindcss(), servePrivateData(dataDir)],
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname, './src'),
    },
  },
  server: {
    proxy: {
      '/api': {
        // En Docker : API_TARGET=http://api:8001 (hostname interne)
        // En local  : http://localhost:8001
        target: process.env.API_TARGET ?? 'http://localhost:8001',
        changeOrigin: true,
      },
    },
  },
})
