# EDS BIN Process Window Workbench

Vue 3 + FastAPI prototype for a semiconductor YE data-analysis workbench. The app helps process and yield engineers review whether a FAB process management SPEC is appropriate by walking through analysis-set definition, EDS BIN Group construction, condition-rule splits, window review, outlier exclusion, pending EDS prediction, and export/report handoff.

This prototype uses synthetic/mock data only. It does not connect to internal databases, authentication systems, or secure company sources.

## File Structure

```text
backend/
  app/
    main.py
    api/                  FastAPI route modules
    core/config.py
    models/schemas.py     Pydantic request contracts
    services/             mock data, analysis, prediction, export logic
    data/mock_store.py    in-memory prototype store
  tests/
  requirements.txt
  README.md

frontend/
  src/
    main.ts
    App.vue
    router/
    stores/               Pinia stores
    api/                  typed API client
    views/                six workbench screens
    components/           common panels, Plotly charts, window/prediction widgets
  package.json
```

Legacy demo files from the earlier dashboard remain in the repo, but the current app entrypoint is `frontend/src/main.ts` and the current backend entrypoint is `backend/app/main.py`.

## Run

Backend:

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` to `http://localhost:8000` by default. If another service already uses port 8000, run the backend on another port and start Vite with:

```bash
BACKEND_URL=http://127.0.0.1:8001 npm run dev
```

## Mock Data

The backend generates roughly 220 lots, 2,000+ wafers, and 600 EDS BIN columns. The synthetic physics encode:

- high-side `metro_ch_hole_cd` increasing Hole-to-Hole BIN Group risk
- low-side `metro_ch_hole_cd` increasing Ch.Hole Not Open risk
- a safe window where both trade-off groups are lower
- chamber high-side tail behavior
- PPID/ECO average shifts
- Tool/Chamber part-modification improvement after a manual date
- edge/center wafer-zone sensitivity
- outlier wafers from other-process noise
- pending EDS wafers with FAB/FDC data available first

## Screens

- Analysis Set: population filters, exclusion toggles, lot/wafer/coverage summary
- BIN Group: single or summed EDS BIN Failure Mode definitions, including zone groups
- Condition Rule: ECO/PPID/Tool/Chamber/Recipe/PM-age splits and manual modification rules
- Window Review: summary, raw scatter, binned response, trade-off, time trend, condition split, zone view, interaction heatmap, and exclusion versions
- Pending Prediction: explainable regression, prediction interval, confidence, pending risk table, and backtest metrics
- Export / Report: CSV/JSON downloads and review-candidate summary text

## API

- `GET /api/health`
- `POST /api/mock-data/reset`
- `GET /api/metadata`
- `POST /api/analysis-sets`
- `GET /api/analysis-sets`
- `GET /api/analysis-sets/{analysis_set_id}`
- `POST /api/bin-groups`
- `GET /api/bin-groups`
- `POST /api/condition-rules`
- `GET /api/condition-rules`
- `POST /api/window-review`
- `POST /api/exclusion-rules`
- `GET /api/exclusion-rules`
- `POST /api/pending-prediction`
- `GET /api/export/analysis-set/{analysis_set_id}`
- `GET /api/export/report/{analysis_run_id}`

## Verification

```bash
python3 -m pytest backend/tests/test_workbench_app.py -q
cd frontend && npm test && npm run build
```

## Future Extension

The route layer is intentionally thin. To connect real systems later, replace the mock generator/store with database-backed repositories while keeping the service inputs stable. Add authentication, persisted Analysis Run versions, and governed export destinations around the route layer rather than inside chart or prediction logic.
