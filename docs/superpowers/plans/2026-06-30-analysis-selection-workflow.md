# Analysis Selection Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the separate setup menus with one `분석물량 선정` workflow that supports shared read-only conditions, personal editable copies, fixed/recent date modes, EDS-actual-only analysis, and a FAB -> EDS -> Legend step flow.

**Architecture:** Add a small backend in-memory condition library alongside the existing mock stores, then use it from a new consolidated Vue view. Keep Window Review contracts stable by continuing to create Analysis Set, BIN Group selection, and Condition Rule selection through the existing stores. Hide Pending prediction from navigation without deleting backend prediction code.

**Tech Stack:** FastAPI, Pydantic, in-memory mock store, Vue 3, Pinia, Element Plus, Node test runner, pytest.

---

### Task 1: Backend Condition Library

**Files:**
- Modify: `backend/app/data/mock_store.py`
- Modify: `backend/app/models/schemas.py`
- Modify: `backend/app/services/mock_data_service.py`
- Create: `backend/app/services/analysis_condition_service.py`
- Create: `backend/app/api/routes_analysis_conditions.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_workbench_app.py`

- [ ] **Step 1: Write failing backend test**

Add a test that resets mock data, lists `/api/analysis-conditions`, verifies shared Ch.Hole revision presets are read-only, copies one shared preset to personal scope, updates the personal copy with a recent-day FAB period, and confirms shared presets remain unchanged.

- [ ] **Step 2: Run backend test to verify RED**

Run: `python3 -m pytest backend/tests/test_workbench_app.py -q`

Expected: fails with missing `/api/analysis-conditions` route.

- [ ] **Step 3: Add schemas and store fields**

Add condition-template schemas for `shared` and `personal` scopes, fixed/recent date mode, FAB filters, EDS filters, legend config, and selected BIN Group IDs.

- [ ] **Step 4: Add service and routes**

Implement list, copy-to-personal, update-personal, and create-analysis-set-from-condition helpers. Shared templates must be read-only; personal templates can be changed.

- [ ] **Step 5: Run backend test to verify GREEN**

Run: `python3 -m pytest backend/tests/test_workbench_app.py -q`

Expected: all backend tests pass.

### Task 2: Frontend Model And Navigation

**Files:**
- Create: `frontend/src/analysisSelection.js`
- Create: `frontend/src/analysisSelection.test.js`
- Create: `frontend/src/navigation.js`
- Create: `frontend/src/navigation.test.js`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/api/analysisApi.ts`
- Modify: `frontend/src/stores/analysisSetStore.ts`

- [ ] **Step 1: Write failing frontend tests**

Add tests that confirm the visible nav contains `분석물량 선정`, `Window Review`, and `Export / Report`; excludes `Pending 예측`; and that condition library helpers label shared templates read-only and personal templates editable.

- [ ] **Step 2: Run frontend test to verify RED**

Run: `npm test`

Expected: fails because `analysisSelection.js` and `navigation.js` do not exist.

- [ ] **Step 3: Add helper modules and API methods**

Implement navigation metadata and analysis-selection view-model helpers. Add API methods for condition list, copy, update, and create-analysis-set-from-condition.

- [ ] **Step 4: Run frontend test to verify GREEN**

Run: `npm test`

Expected: all frontend tests pass.

### Task 3: Consolidated UI

**Files:**
- Create: `frontend/src/views/AnalysisSelectionView.vue`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/guideContent.js`
- Leave in place: `frontend/src/views/AnalysisSetView.vue`, `frontend/src/views/BinGroupView.vue`, `frontend/src/views/ConditionRuleView.vue`, `frontend/src/views/PendingPredictionView.vue`

- [ ] **Step 1: Build the consolidated view**

Create a left condition library with `공유 조건` and `개인 조건` tabs, a central three-step wizard (`FAB 기준`, `EDS 기준`, `Legend 설정`), and a sticky bottom action row with `Back`, `Next`, `개인 조건으로 저장`, and `Window Review로 이동`.

- [ ] **Step 2: Route and nav cleanup**

Route `/analysis-selection` to the new view, redirect `/analysis-set`, `/bin-group`, and `/condition-rule` to `/analysis-selection`, and remove `Pending 예측` from visible navigation.

- [ ] **Step 3: Preserve current selections**

When applying a condition, create or select an Analysis Set with `eds_status: actual_only`, select the condition's BIN Group IDs, and select the condition rule so Window Review uses the chosen setup.

- [ ] **Step 4: Run frontend test and build**

Run: `npm test`

Run: `npm run build`

Expected: tests and build pass.

### Task 4: Preview Verification

**Files:**
- No source edits.

- [ ] **Step 1: Start worktree frontend**

Run: `BACKEND_URL=http://127.0.0.1:8010 npm run dev -- --host 127.0.0.1 --port 5174`

- [ ] **Step 2: Browser smoke check**

Open `http://127.0.0.1:5174/analysis-selection`, verify the `분석물량 선정` page renders, the nav no longer shows `Pending 예측`, shared/personal condition tabs are visible, and no console errors appear.
