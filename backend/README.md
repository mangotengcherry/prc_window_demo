# EDS BIN Process Window Workbench Backend

FastAPI prototype backend for a semiconductor YE process-window workbench. It uses synthetic in-memory wafer data only; no internal database, account, or secure source is accessed.

## Run

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://localhost:8000/docs` for the API contract.

## Main Endpoints

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

## Mock Data

The generator creates roughly 220 lots, several thousand wafers, and 600 EDS BIN columns. It encodes high-side Hole-to-Hole risk, low-side Ch.Hole Not Open risk, chamber tail behavior, ECO/PPID shifts, part-modification improvement, wafer-zone sensitivity, outlier wafers, and EDS pending wafers.

## Extension Point

Replace `app/services/mock_data_service.py` and keep service inputs stable to connect real FAB, FDC, EDS, and rule sources later. Add authentication and persistence around the route layer without moving calculation logic out of services.
