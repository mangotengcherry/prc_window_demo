import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      // /api 로 시작하는 요청을 백엔드(8000)로 전달 → 브라우저 CORS 회피
      '/api': 'http://localhost:8000',
    },
  },
  build: {
    rollupOptions: {
      output: {
        // ECharts(최대 의존성)를 별도 청크로 → 앱 코드 변경 시 캐시 유지, 초기 파싱 부담 분리
        manualChunks: { echarts: ['echarts', 'vue-echarts'] },
      },
    },
  },
})
