import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    // true = 0.0.0.0 바인딩 → 같은 LAN/내부망의 팀원이 http://<내IP>:5173 으로 접속 가능.
    // (미설정 시 localhost 전용이라 외부 접속 불가) 실행 시 Vite가 Network URL을 자동 출력한다.
    // IP는 어디에도 하드코딩하지 않는다 — 실행 머신의 현재 IP를 자동 감지한다.
    host: true,
    // mDNS 호스트네임(예: my-mac.local) 접속 허용 → IP가 DHCP로 바뀌어도 이름은 고정.
    // (IP·localhost 접속은 기본 허용이라 .local만 추가) 보안: .local은 같은 망에서만 해석됨.
    allowedHosts: ['.local'],
    port: 5173,
    proxy: {
      // /api 로 시작하는 요청을 백엔드(8000)로 전달 → 브라우저 CORS 회피.
      // 프록시는 호스트 머신에서 실행되므로 백엔드는 localhost(8000)에 그대로 두면 됨(직접 노출 불필요).
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
