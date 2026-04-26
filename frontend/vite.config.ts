import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/media': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    chunkSizeWarningLimit: 1000,
    cssCodeSplit: true,
    rolldownOptions: {
      output: {
        codeSplitting: {
          groups: [
            {
              name: 'react-vendor',
              test: /node_modules[\\\/](?:react|react-dom|react-router-dom)[\\\/]/,
              priority: 20,
            },
            {
              name: 'antd-vendor',
              test: /node_modules[\\\/](?:antd|@ant-design)[\\\/]/,
              priority: 15,
            },
            {
              name: 'monaco-vendor',
              test: /node_modules[\\\/](?:monaco-editor|@monaco-editor)[\\\/]/,
              priority: 15,
            },
            {
              name: 'echarts-vendor',
              test: /node_modules[\\\/](?:echarts|echarts-for-react)[\\\/]/,
              priority: 15,
            },
          ],
        },
      },
    },
  },
})
