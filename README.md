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

## 사용
1. X feature / Y target 선택 → **차트 그리기**
2. spec lower / upper 입력 → binned 차트에 빨간 수직선 표시
3. 시계열 차트를 드래그/스크롤하면 위·아래가 시간축으로 함께 움직임

자세한 설명은 노트북 9장(파일 아키텍처)과 10장(실행 방법)을 참고하세요.
