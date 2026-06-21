# Process Window 분석 대시보드 (Vue3 + FastAPI)

웹 개발 입문자를 위한 학습용 프로젝트. 먼저 **`process_window_dashboard_guide.ipynb`** 를 읽으며 개념을 익히고, 아래 코드를 실행해 보세요.

> Python은 **3.10+** 기준입니다.

## 구조
```
backend/   FastAPI(파이썬) — binning/시계열 계산 API
frontend/  Vue3 + Vite + ECharts — 화면과 차트
```

## 실행 (터미널 2개)

**① 백엔드**
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# API 테스트: http://localhost:8000/docs
```

**② 프론트엔드**
```bash
cd frontend
npm install
npm run dev
# 접속: http://localhost:5173
```

## 팀원에게 공유 (같은 LAN/내부망)

`vite.config.js` 의 `server.host: true` 로 dev 서버가 `0.0.0.0` 에 바인딩되어, 같은 네트워크의 팀원이 접속할 수 있습니다. **IP는 코드 어디에도 고정하지 않습니다** — 실행하는 PC의 현재 IP를 Vite가 자동 감지해 출력하므로, 어느 PC에서 띄우든 그대로 동작합니다. 백엔드는 Vite 프록시를 통해 호스트 내부에서만 호출되어 그대로 두면 됩니다(직접 노출 불필요).

**방법 A — IP로 공유 (간단)**
```bash
npm run dev    # 실행하면 터미널에 "Network: http://<자동감지-IP>:5173/" 가 출력됨
# 그 Network 주소를 팀원에게 전달. (수동 확인은 macOS: ipconfig getifaddr en0  / 유선은 en1)
```
LAN IP는 DHCP로 **바뀔 수 있으니** 외워서 고정하지 말고, 띄울 때마다 출력되는 `Network:` 줄로 그때그때 확인하세요.

**방법 B — 호스트네임으로 공유 (IP가 바뀌어도 고정, 권장)**
```bash
scutil --get LocalHostName     # macOS 컴퓨터 이름 확인 → 주소는 http://<그이름>.local:5173
```
`*.local`(mDNS) 이름은 IP가 바뀌어도 그대로라 더 안정적입니다. (`vite.config.js` 의 `allowedHosts: ['.local']` 로 허용해 둠)

> 주의
> - **같은 네트워크(사내 LAN/Wi-Fi)** 에 있어야 접속됩니다. 외부 인터넷에서는 안 됩니다(VPN/사내망 필요).
> - 첫 접속 시 macOS **방화벽** 이 차단하면 허용해 주세요: 시스템 설정 → 네트워크 → 방화벽.
> - 내 PC가 켜져 있고 dev 서버가 떠 있어야 접속됩니다. 상시·고정 주소가 필요하면 별도 서버 배포 또는 IT에 고정 IP(DHCP 예약) 요청을 권장합니다.

## 사용
1. X feature / Y target 선택 → **차트 그리기**
2. spec lower / upper 입력 → binned 차트에 빨간 수직선 표시
3. 시계열 차트를 드래그/스크롤하면 위·아래가 시간축으로 함께 움직임

자세한 설명은 노트북 9장(파일 아키텍처)과 10장(실행 방법)을 참고하세요.
