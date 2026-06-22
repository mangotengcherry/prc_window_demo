# PRC Window Workbench Risk Briefing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the approved Workbench + Streamlined Controls UI direction: a compact query sidebar, a lag-aware risk briefing band, and a calmer first-screen analysis order.

**Architecture:** Add a small pure `riskBriefing` view-model utility with Node tests, then consume it from `App.vue` through a focused `RiskBriefingBand.vue` component. Keep existing chart and API contracts intact; update `Sidebar.vue` in place so existing query state and events keep working.

**Tech Stack:** Vue 3 Composition API, Vite, ECharts through existing components, Node built-in test runner for frontend utility tests, existing FastAPI response contracts.

---

## File Structure

- Create `frontend/src/riskBriefing.js`: pure derivation functions for top driver, suggested window, lag-aware risk, trust checks, and next check.
- Create `frontend/src/riskBriefing.test.js`: Node tests for the derivation rules.
- Modify `frontend/package.json`: add a `test` script using Node's built-in test runner.
- Create `frontend/src/components/RiskBriefingBand.vue`: presentation-only component for the top briefing cards.
- Modify `frontend/src/components/Sidebar.vue`: make the default sidebar a compact query summary with an expandable query editor.
- Modify `frontend/src/App.vue`: compute the briefing view model, render the new band, and reorder first-screen content.
- Modify `frontend/src/style.css` and scoped component styles only where needed for layout polish.

## Task 1: Add Tested Risk Briefing View Model

**Files:**
- Create: `frontend/src/riskBriefing.js`
- Create: `frontend/src/riskBriefing.test.js`
- Modify: `frontend/package.json`

- [ ] **Step 1: Add the frontend test script**

Modify `frontend/package.json` scripts to include `test`:

```json
{
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "test": "node --test src/*.test.js"
  }
}
```

- [ ] **Step 2: Write failing tests for briefing derivation**

Create `frontend/src/riskBriefing.test.js`:

```js
import test from 'node:test'
import assert from 'node:assert/strict'
import { buildRiskBriefing, deriveSuggestedWindow, daysBetween } from './riskBriefing.js'

const cond = {
  line_id: 'AAAA',
  product: 'AAEQ',
  category: 'BIN',
  eds_step: 'EDS_M',
  fab_step: 'EQ760200',
  date_range: { start_date: '2026-01-01', end_date: '2026-06-18' },
  target_date_range: { start_date: '2026-01-01', end_date: '2026-04-27' },
  x_features: ['numeric|EQ760200|MT123456|CD_MEAN|avg'],
  y_targets: ['BIN0131'],
}

const combo = {
  x_feature: 'numeric|EQ760200|MT123456|CD_MEAN|avg',
  x_feature_display_name: 'CD_MEAN / avg',
  y_target: 'BIN0131',
  bins: [
    { bin_left: 40, bin_right: 41, y_avg: 0.18, wafer_count: 22 },
    { bin_left: 42.1, bin_right: 43, y_avg: 0.08, wafer_count: 148 },
    { bin_left: 44, bin_right: 45, y_avg: 0.23, wafer_count: 31 },
  ],
}

test('daysBetween returns positive day gaps for date strings', () => {
  assert.equal(daysBetween('2026-04-27', '2026-06-18'), 52)
})

test('deriveSuggestedWindow picks the lowest target mean among sufficiently populated bins', () => {
  const result = deriveSuggestedWindow(combo, 10)
  assert.deepEqual(result, {
    label: '42.10-43.00',
    value: '0.080',
    n: 148,
    bin: combo.bins[1],
  })
})

test('buildRiskBriefing combines forecast, driver, window, and trust information', () => {
  const briefing = buildRiskBriefing({
    cond,
    columns: { min_n: 10 },
    binned: { combos: [combo] },
    timeseries: {
      n_total: 300,
      targets: [{ name: 'BIN0131', avg: 0.12, observed_points: [{ time: '2026-04-27T00:00:00' }] }],
      features: [{ name: combo.x_feature, drift: { flagged: true, direction: 'up', shift: 1.8 } }],
      estimates: [{
        x_feature: combo.x_feature,
        y_target: 'BIN0131',
        points: [['2026-06-01T00:00:00', 0.15], ['2026-06-18T00:00:00', 0.16]],
        fit_summary: { r2: 0.64, extrap: 0.08, n: 180, slope: 1, intercept: 0 },
        forecast: { n: 37, mean_pred: 0.162, shift: 1.8, r2: 0.64, extrap: 0.08, low_conf: false },
      }],
    },
    driversData: [{
      target: 'BIN0131',
      drivers: [{ feature: combo.x_feature, display_name: 'CD_MEAN / avg', corr: 0.61, abs: 0.61, n: 180, q_value: 0.03 }],
    }],
    tableRows: [
      { x_feature: combo.x_feature, y_target: 'BIN0131', category_feature_name: 'EQP_CH', category_feature_value: 'CH01', mean: 0.08, n: 92 },
      { x_feature: combo.x_feature, y_target: 'BIN0131', category_feature_name: 'EQP_CH', category_feature_value: 'CH02', mean: 0.19, n: 77 },
    ],
  })

  assert.equal(briefing.available, true)
  assert.equal(briefing.risk.value, '+0.042')
  assert.equal(briefing.risk.detail, '+1.8σ predicted recent gap')
  assert.equal(briefing.topDriver.name, 'CD_MEAN / avg')
  assert.equal(briefing.suggestedWindow.label, '42.10-43.00')
  assert.equal(briefing.nextCheck.label, 'Check EQP_CH split')
  assert.equal(briefing.nextCheck.detail, 'CH02 has highest target mean · n=77')
  assert.equal(briefing.trust[0].value, '148')
  assert.equal(briefing.trust[1].value, 'R² 0.64')
  assert.equal(briefing.trust[2].value, '8%')
  assert.equal(briefing.trust[3].value, '52d')
})
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
cd frontend
npm test
```

Expected: FAIL with a module resolution error for `./riskBriefing.js`.

- [ ] **Step 4: Implement the minimal briefing utility**

Create `frontend/src/riskBriefing.js`:

```js
import { fmtNum } from './stats.js'

export function daysBetween(start, end) {
  if (!start || !end) return null
  const a = new Date(start)
  const b = new Date(end)
  if (Number.isNaN(a.getTime()) || Number.isNaN(b.getTime())) return null
  return Math.max(0, Math.round((b - a) / 86400000))
}

function firstValue(arr) {
  return Array.isArray(arr) && arr.length ? arr[0] : null
}

function sameCfv(a, b) {
  return (a ?? null) === (b ?? null)
}

function signed(v) {
  if (v == null || Number.isNaN(v)) return '-'
  return `${v >= 0 ? '+' : ''}${fmtNum(v)}`
}

function pct(v) {
  if (v == null || Number.isNaN(v)) return '-'
  return `${Math.round(v * 100)}%`
}

function primaryTarget(cond) {
  return firstValue(cond?.y_targets) || ''
}

function primaryFeature(cond) {
  return firstValue(cond?.x_features) || ''
}

function comboMatches(combo, feature, target) {
  return combo?.x_feature === feature && combo?.y_target === target
}

function findCombo(binned, feature, target) {
  const combos = binned?.combos || []
  return combos.find((c) => comboMatches(c, feature, target)) ||
    combos.find((c) => c.y_target === target) ||
    combos[0] ||
    null
}

function findTargetSeries(timeseries, target, cfv = null) {
  return (timeseries?.targets || []).find((s) => s.name === target && sameCfv(s.category_feature_value, cfv)) ||
    (timeseries?.targets || []).find((s) => s.name === target) ||
    null
}

function findEstimate(timeseries, feature, target, cfv = null) {
  return (timeseries?.estimates || []).find((e) =>
    e.x_feature === feature && e.y_target === target && sameCfv(e.category_feature_value, cfv)
  ) || null
}

function findTopDriver(driversData, target) {
  const targetBlock = (driversData || []).find((t) => t.target === target) || firstValue(driversData)
  return firstValue(targetBlock?.drivers)
}

function observedLastDate(targetSeries, fallback) {
  const points = targetSeries?.observed_points || []
  const last = points.length ? points[points.length - 1]?.time : null
  return last || fallback || null
}

export function deriveSuggestedWindow(combo, minN = 10) {
  const bins = (combo?.bins || []).filter((b) => b.y_avg != null && (b.wafer_count ?? b.n_observed ?? 0) >= minN)
  if (!bins.length) return null
  const best = [...bins].sort((a, b) => a.y_avg - b.y_avg)[0]
  return {
    label: `${Number(best.bin_left).toFixed(2)}-${Number(best.bin_right).toFixed(2)}`,
    value: fmtNum(best.y_avg),
    n: best.wafer_count ?? best.n_observed ?? null,
    bin: best,
  }
}

function deriveNextCheck(tableRows, feature, target) {
  const rows = (tableRows || []).filter((r) =>
    r.x_feature === feature &&
    r.y_target === target &&
    r.category_feature_value != null &&
    r.mean != null
  )
  if (!rows.length) return {
    label: 'Review top driver window',
    detail: 'Use window chart and time series together',
    tone: 'neutral',
  }
  const worst = [...rows].sort((a, b) => b.mean - a.mean)[0]
  return {
    label: `Check ${worst.category_feature_name || 'split'} split`,
    detail: `${worst.category_feature_value} has highest target mean · n=${worst.n ?? '-'}`,
    tone: 'warn',
  }
}

export function buildRiskBriefing({ cond, columns, binned, timeseries, driversData, tableRows }) {
  if (!cond || !binned || !timeseries) return { available: false, reason: 'Run an analysis to see the risk briefing.' }

  const target = primaryTarget(cond)
  const topDriver = findTopDriver(driversData, target)
  const feature = topDriver?.feature || primaryFeature(cond)
  const combo = findCombo(binned, feature, target)
  const targetSeries = findTargetSeries(timeseries, target, combo?.category_feature_value)
  const estimate = findEstimate(timeseries, combo?.x_feature || feature, target, combo?.category_feature_value)
  const forecast = estimate?.forecast || null
  const fit = estimate?.fit_summary || forecast || null
  const observedAvg = targetSeries?.avg
  const predictedMean = forecast?.mean_pred
  const gap = predictedMean != null && observedAvg != null ? predictedMean - observedAvg : null
  const minN = columns?.min_n ?? 10
  const suggestedWindow = deriveSuggestedWindow(combo, minN)
  const lastObserved = observedLastDate(targetSeries, cond.target_date_range?.end_date)
  const gapDays = daysBetween(lastObserved, cond.date_range?.end_date)

  return {
    available: true,
    title: `${cond.fab_step} · ${target} process window`,
    subtitle: `${cond.line_id} / ${cond.product} · FAB ${cond.date_range?.start_date} to ${cond.date_range?.end_date} · EDS observed through ${lastObserved ? String(lastObserved).slice(0, 10) : '-'}`,
    risk: {
      label: 'Lag-aware risk',
      value: gap == null ? '-' : signed(gap),
      detail: forecast?.shift == null ? 'prediction confidence unavailable' : `${signed(forecast.shift)}σ predicted recent gap`,
      lowConfidence: !!forecast?.low_conf,
    },
    topDriver: {
      label: 'Top driver',
      name: topDriver?.display_name || combo?.x_feature_display_name || feature || '-',
      detail: topDriver ? `corr ${signed(topDriver.corr)} · n=${topDriver.n}` : 'driver ranking unavailable',
      significant: topDriver?.q_value == null ? null : topDriver.q_value < 0.1,
    },
    suggestedWindow: suggestedWindow || {
      label: '-',
      value: '-',
      n: null,
    },
    nextCheck: deriveNextCheck(tableRows, combo?.x_feature || feature, target),
    trust: [
      { label: 'Observed support', value: suggestedWindow?.n == null ? '-' : String(suggestedWindow.n) },
      { label: 'Model fit', value: fit?.r2 == null ? '-' : `R² ${fmtNum(fit.r2)}` },
      { label: 'Extrapolation', value: fit?.extrap == null ? '-' : pct(fit.extrap) },
      { label: 'Missing Y gap', value: gapDays == null ? '-' : `${gapDays}d` },
    ],
  }
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run:

```bash
cd frontend
npm test
```

Expected: PASS for all three tests.

- [ ] **Step 6: Commit**

```bash
git add frontend/package.json frontend/src/riskBriefing.js frontend/src/riskBriefing.test.js
git commit -m "feat: derive risk briefing view model"
```

## Task 2: Add Risk Briefing Presentation Component

**Files:**
- Create: `frontend/src/components/RiskBriefingBand.vue`

- [ ] **Step 1: Create a presentation-only component**

Create `frontend/src/components/RiskBriefingBand.vue`:

```vue
<script setup>
defineProps({
  briefing: { type: Object, default: null },
})
</script>

<template>
  <section class="risk-band" aria-label="Lag-aware risk briefing">
    <template v-if="briefing?.available">
      <div class="risk-main" :class="{ muted: briefing.risk.lowConfidence }">
        <span class="eyebrow">{{ briefing.risk.label }}</span>
        <strong>{{ briefing.risk.value }}</strong>
        <span>{{ briefing.risk.detail }}</span>
      </div>

      <div class="risk-card">
        <span class="eyebrow">{{ briefing.topDriver.label }}</span>
        <strong>{{ briefing.topDriver.name }}</strong>
        <span>{{ briefing.topDriver.detail }}</span>
      </div>

      <div class="risk-card">
        <span class="eyebrow">Suggested window</span>
        <strong>{{ briefing.suggestedWindow.label }}</strong>
        <span>target {{ briefing.suggestedWindow.value }} · n={{ briefing.suggestedWindow.n ?? '-' }}</span>
      </div>

      <div class="risk-card" :class="'tone-' + briefing.nextCheck.tone">
        <span class="eyebrow">Next check</span>
        <strong>{{ briefing.nextCheck.label }}</strong>
        <span>{{ briefing.nextCheck.detail }}</span>
      </div>

      <div class="trust-card">
        <span class="eyebrow">Trust check</span>
        <dl>
          <template v-for="t in briefing.trust" :key="t.label">
            <dt>{{ t.label }}</dt>
            <dd>{{ t.value }}</dd>
          </template>
        </dl>
      </div>
    </template>

    <p v-else class="risk-empty">{{ briefing?.reason || 'Run an analysis to see the risk briefing.' }}</p>
  </section>
</template>

<style scoped>
.risk-band {
  margin: 14px 32px 0;
  display: grid;
  grid-template-columns: minmax(180px, 1.1fr) repeat(3, minmax(150px, .85fr)) minmax(190px, .9fr);
  gap: 10px;
}
.risk-main,
.risk-card,
.trust-card,
.risk-empty {
  min-width: 0;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  box-shadow: var(--shadow-sm);
  padding: 12px 14px;
}
.risk-main {
  color: #fff;
  background: #111827;
  border-color: #111827;
}
.risk-main.muted {
  background: #374151;
  border-color: #374151;
}
.risk-card.tone-warn {
  background: #fff7ed;
  border-color: #fed7aa;
}
.eyebrow {
  display: block;
  margin-bottom: 5px;
  color: inherit;
  opacity: .72;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: .05em;
  text-transform: uppercase;
}
strong {
  display: block;
  overflow: hidden;
  color: inherit;
  font-size: 16px;
  font-weight: 800;
  line-height: 1.18;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.risk-main strong {
  font-size: 25px;
  letter-spacing: 0;
}
span:not(.eyebrow) {
  display: block;
  margin-top: 4px;
  color: inherit;
  opacity: .76;
  font-size: 11px;
  font-weight: 600;
  line-height: 1.35;
}
dl {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 5px 10px;
  margin: 0;
  font-size: 11px;
}
dt {
  color: var(--text-2);
  font-weight: 600;
}
dd {
  margin: 0;
  color: var(--text);
  font-weight: 800;
}
.risk-empty {
  grid-column: 1 / -1;
  margin: 0;
  color: var(--text-2);
  font-size: 13px;
}
@media (max-width: 1220px) {
  .risk-band {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 760px) {
  .risk-band {
    grid-template-columns: 1fr;
    margin: 12px 16px 0;
  }
}
</style>
```

- [ ] **Step 2: Run build to catch component syntax issues**

Run:

```bash
cd frontend
npm run build
```

Expected: PASS with Vite production build output.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/RiskBriefingBand.vue
git commit -m "feat: add risk briefing band component"
```

## Task 3: Render Briefing In App And Reorder First Screen

**Files:**
- Modify: `frontend/src/App.vue`

- [ ] **Step 1: Import the component and briefing utility**

In `frontend/src/App.vue`, add imports near existing component imports:

```js
import RiskBriefingBand from './components/RiskBriefingBand.vue'
import { buildRiskBriefing } from './riskBriefing.js'
```

- [ ] **Step 2: Add computed briefing view model**

Add this computed block after `condSummary`:

```js
const riskBriefing = computed(() => buildRiskBriefing({
  cond: lastCond.value,
  columns: columns.value,
  binned: binned.value,
  timeseries: timeseries.value,
  driversData: driversData.value,
  tableRows: tableRows.value,
}))
```

- [ ] **Step 3: Render the band below provenance**

In the template, add the band after the provenance block and before banners:

```vue
<RiskBriefingBand v-if="lastCond" :briefing="riskBriefing" />
```

- [ ] **Step 4: Move combo rows above secondary insight panels**

In `frontend/src/App.vue`, reorder the loaded-state sections so this order is used:

```vue
<section v-if="kpis" class="kpis">
  ...
</section>

<section class="rows">
  <ComboRow v-for="(r, i) in rows" ... />
</section>

<section v-if="status === 'loaded' && driversData.length" class="drivers-area">
  ...
</section>

<section v-if="status === 'loaded' && capability.length" class="drivers-area">
  ...
</section>

<section v-if="status === 'loaded' && conditionCompare.length" class="drivers-area">
  ...
</section>
```

Keep the existing `ComboRow` props unchanged. This gives the first screen the briefing plus workbench charts before lower-priority analysis panels.

- [ ] **Step 5: Run tests and build**

Run:

```bash
cd frontend
npm test
npm run build
```

Expected: tests PASS and build PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/App.vue
git commit -m "feat: show lag-aware risk briefing"
```

## Task 4: Streamline Sidebar Controls

**Files:**
- Modify: `frontend/src/components/Sidebar.vue`

- [ ] **Step 1: Add compact/edit mode state and summary helpers**

In `frontend/src/components/Sidebar.vue`, add these values after `chartMode`:

```js
const editMode = ref(false)
const compactReady = computed(() => valid.value && !editMode.value)

function showEditor() {
  editMode.value = true
}

function closeEditor() {
  if (valid.value) editMode.value = false
}

const dateSummary = computed(() => {
  if (!startDate.value || !endDate.value) return '-'
  return `${startDate.value} ~ ${endDate.value}`
})

const targetDateSummary = computed(() => {
  if (!yStartDate.value || !yEndDate.value) return '-'
  return `${yStartDate.value} ~ ${yEndDate.value}`
})

const selectedXOptions = computed(() => {
  const byName = new Map(props.xFeatureOptions.map((o) => [o.name, o]))
  return xFeatures.value.map((name) => byName.get(name) || { name, display_name: keyDisplay(name), score: null })
})

const selectedTargets = computed(() => yTargets.value.map((name) => {
  const group = targetGroups.value.find((g) => g.name === name)
  return group ? { name, kind: 'group', detail: group.sources.join(' + ') } : { name, kind: 'target', detail: category.value }
}))
```

- [ ] **Step 2: Collapse editor after successful draw**

Update `onDraw()` in `Sidebar.vue` so it collapses after emitting:

```js
function onDraw() {
  if (!valid.value) return
  emit('draw', {
    line_id: lineId.value, product: product.value, category: category.value, eds_step: edsStep.value,
    date_range: { start_date: startDate.value, end_date: endDate.value, time_column: 'fab_track_out_time' },
    target_date_range: { start_date: yStartDate.value, end_date: yEndDate.value, time_column: 'eds_tkout_time' },
    fab_step: fabStep.value,
    x_features: [...xFeatures.value], y_targets: [...yTargets.value], bins: 10,
    y_target_groups: targetGroups.value
      .filter((g) => yTargets.value.includes(g.name))
      .map((g) => ({ name: g.name, sources: [...g.sources], agg: g.agg })),
    category_feature: categoryFeature.value
      ? { name: categoryFeature.value, values: [...categoryValues.value], chart_mode: chartMode.value }
      : null,
  })
  editMode.value = false
}
```

- [ ] **Step 3: Replace the top-level template structure**

In the `<template>`, keep the existing field markup but wrap it in an editor container. The top of `<aside class="sidebar">` should become:

```vue
<aside class="sidebar" :class="{ compact: compactReady }">
  <div class="brand-row">
    <h1 class="brand"><span class="dot"></span>Process Window</h1>
    <span class="view-pill">Workbench</span>
  </div>

  <button class="edit-query" @click="showEditor">{{ compactReady ? 'Edit query' : 'Query controls' }}</button>

  <section class="query-summary">
    <h3>Current query</h3>
    <div class="chips">
      <span class="qchip">{{ lineId || '-' }}</span>
      <span class="qchip">{{ product || '-' }}</span>
      <span class="qchip">{{ fabStep || '-' }}</span>
      <span class="qchip">{{ category || '-' }}</span>
    </div>
    <p class="summary-line">FAB {{ dateSummary }}</p>
    <p class="summary-line">EDS {{ targetDateSummary }}</p>
  </section>

  <section class="query-summary">
    <h3>Targets <small>{{ yTargets.length }}</small></h3>
    <div class="selected-list">
      <div v-for="t in selectedTargets.slice(0, 4)" :key="t.name" class="selected-row">
        <span>{{ t.name }}</span>
        <b>{{ t.kind }}</b>
      </div>
      <p v-if="!selectedTargets.length" class="none-mini">No target selected</p>
    </div>
  </section>

  <section class="query-summary grow">
    <h3>Features <small>{{ xFeatures.length }}</small></h3>
    <input class="search" v-model="xSearch" placeholder="Search selected/ranked features" />
    <div class="selected-list">
      <div v-for="o in selectedXOptions.slice(0, 5)" :key="o.name" class="selected-row feature-row" :title="o.name">
        <span>{{ o.display_name }}</span>
        <b v-if="o.score != null">{{ o.score }}</b>
      </div>
      <p v-if="!selectedXOptions.length" class="none-mini">No feature selected</p>
    </div>
  </section>

  <section class="advanced-summary">
    <button type="button" @click="editMode = !editMode">
      <span>Advanced filters</span>
      <b>{{ editMode ? '−' : '+' }}</b>
    </button>
    <p>Matching, grade, split mode, reset actions</p>
  </section>

  <div v-if="editMode || !valid" class="query-editor">
    <!-- Move the existing Line/Product/FAB/Y/X/Split controls here without changing their v-models. -->
  </div>

  <button class="draw" :disabled="!valid || loading" @click="onDraw">
    {{ loading ? '불러오는 중…' : '차트 작성' }}
  </button>
  <button v-if="editMode && valid" type="button" class="close-editor" @click="closeEditor">요약만 보기</button>
  <p v-if="!valid" class="hint">Line·제품·Category·EDS·FAB·기간 + X/Y 1개 이상 선택</p>
</aside>
```

When implementing this step, move the existing controls from the current template into the marked `query-editor` block. Do not rename existing refs, computed values, or event handlers.

- [ ] **Step 4: Add compact sidebar styles**

Append to `Sidebar.vue` scoped styles:

```css
.brand-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.view-pill {
  flex: 0 0 auto;
  color: var(--text-2);
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 3px 7px;
  font-size: 10px;
  font-weight: 700;
}
.edit-query {
  width: 100%;
  padding: 10px 12px;
  color: #fff;
  background: var(--accent);
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}
.query-summary {
  gap: 7px;
  padding: 10px;
  background: rgba(255,255,255,.74);
  border: 1px solid var(--border);
  border-radius: 8px;
}
.query-summary.grow {
  min-height: 0;
  flex: 1;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}
.qchip {
  max-width: 100%;
  overflow: hidden;
  color: var(--text);
  background: var(--surface-2);
  border-radius: 999px;
  padding: 4px 7px;
  font-size: 10px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.summary-line {
  margin: 0;
  color: var(--text-2);
  font-size: 11px;
  line-height: 1.35;
}
.selected-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.selected-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  padding: 7px 8px;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 7px;
}
.selected-row span {
  min-width: 0;
  overflow: hidden;
  color: var(--text);
  font-size: 12px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.selected-row b {
  color: var(--accent);
  font-size: 9px;
  font-weight: 800;
  text-transform: uppercase;
}
.feature-row:first-child {
  background: #fff1f2;
  border-color: #fecaca;
}
.feature-row:first-child span {
  color: #991b1b;
}
.none-mini {
  margin: 0;
  color: var(--text-2);
  font-size: 11px;
}
.advanced-summary {
  padding: 9px 10px;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 8px;
}
.advanced-summary button {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0;
  color: var(--text);
  background: transparent;
  border: none;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
}
.advanced-summary p {
  margin: 4px 0 0;
  color: var(--text-2);
  font-size: 10px;
}
.query-editor {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding-top: 4px;
}
.close-editor {
  padding: 8px 10px;
  color: var(--accent);
  background: #fff;
  border: 1px solid var(--accent);
  border-radius: 8px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}
```

- [ ] **Step 5: Run build**

Run:

```bash
cd frontend
npm run build
```

Expected: PASS. If Vue reports adjacent template root or missing closing tags, fix the moved editor markup before continuing.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/Sidebar.vue
git commit -m "feat: streamline query sidebar"
```

## Task 5: Polish Layout Spacing And Responsive Behavior

**Files:**
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/style.css`
- Modify: `frontend/src/components/Sidebar.vue`

- [ ] **Step 1: Tighten first-screen spacing in App**

In `frontend/src/App.vue` scoped styles, adjust these existing rules:

```css
.topbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 20px 32px 6px;
}
.kpis {
  display: flex;
  gap: 10px;
  padding: 12px 32px 0;
  flex-wrap: wrap;
}
.rows {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 14px 32px;
}
.drivers-area {
  padding: 10px 32px 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
```

- [ ] **Step 2: Remove one-note visual noise from global background**

In `frontend/src/style.css`, simplify `body` background to reduce decorative competition:

```css
body {
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text",
    "Helvetica Neue", "Pretendard", system-ui, sans-serif;
  color: var(--text);
  background: var(--bg);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  letter-spacing: 0;
}
```

- [ ] **Step 3: Keep sidebar stable on narrower screens**

In `Sidebar.vue` scoped styles, update `.sidebar` width to:

```css
.sidebar {
  width: 288px;
  flex: 0 0 288px;
  background: var(--sidebar);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border-right: 1px solid var(--border);
  padding: 18px 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
}
```

- [ ] **Step 4: Run build**

Run:

```bash
cd frontend
npm run build
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.vue frontend/src/style.css frontend/src/components/Sidebar.vue
git commit -m "style: calm first-screen dashboard layout"
```

## Task 6: Browser Smoke Test And Fixes

**Files:**
- Modify only files touched by Tasks 1-5 if smoke testing exposes layout or runtime issues.

- [ ] **Step 1: Start backend**

Run:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Expected: backend starts and prints Uvicorn running on `http://127.0.0.1:8000`.

- [ ] **Step 2: Start frontend**

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

Expected: Vite prints a local URL, usually `http://localhost:5173/`.

- [ ] **Step 3: Smoke test default flow in browser**

Open the frontend URL and verify:

- Initial screen renders without console errors.
- Sidebar shows compact query summary sections.
- If no X/Y is selected, query editor is visible enough to select required values.
- Clicking "기본값으로 바로 작성" or selecting one X/Y and clicking "차트 작성" loads data.
- After data loads, sidebar collapses to summary.
- Risk briefing band appears above KPI/cards.
- Risk briefing cards do not show `undefined`, `NaN`, or blank labels.
- Window/time-series combo rows appear before secondary driver/capability panels.

- [ ] **Step 4: Check responsive layout**

Use browser viewport checks:

- Desktop around `1280 x 720`: no overlapping cards or clipped sidebar labels.
- Narrow around `900 x 720`: risk briefing wraps to two columns, sidebar remains usable.
- Mobile-width behavior can remain horizontally constrained because the current app is desktop analytical software, but text must not overlap.

- [ ] **Step 5: Run final verification**

Run:

```bash
cd frontend
npm test
npm run build
```

Expected: tests PASS and build PASS.

- [ ] **Step 6: Commit smoke-test fixes**

If fixes were needed:

```bash
git add frontend/src
git commit -m "fix: polish risk briefing workbench layout"
```

If no fixes were needed, skip this commit and record the verification output in the final response.

## Self-Review

Spec coverage:

- Streamlined sidebar query summary: Task 4.
- Lag-aware risk briefing: Tasks 1-3.
- Spotfire-like workbench familiarity: Tasks 3 and 5 preserve chart/workbench flow.
- Trust guardrails: Task 1 derives them and Task 2 renders them.
- Existing API preservation: Tasks use current `binned`, `timeseries`, `table`, and `drivers` responses.
- Verification: Task 6.

Plan checks:

- No backend model or API rewrite is required.
- Pure data derivation is tested before UI consumption.
- UI work is split into presentation, integration, sidebar, and polish tasks.
- Each task produces software that can build independently.
