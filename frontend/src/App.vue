<script setup>
// 레이아웃: [좌측 Sidebar] + [조합별 ComboRow 목록] + [하단 Table]
// 조합(feature × target)마다 spec 헤더 + (Window | 매칭 시계열) 한 행.
import { ref, reactive, computed, onMounted } from 'vue'
import Sidebar from './components/Sidebar.vue'
import ComboRow from './components/ComboRow.vue'
import DataTable from './components/DataTable.vue'
import { fetchColumns, fetchBinned, fetchTimeseries, fetchTable } from './api/client.js'

const columns = reactive({ features: [], targets: [], fabSteps: [] })
const dcSpec = reactive({}) // { feature: { lower, upper } }

const binned = ref(null)       // { fab_step, combos:[{x_feature,y_target,bins}] }
const timeseries = ref(null)   // { targets:[{name,points}], features:[{name,points}] }
const tableRows = ref([])
const specByCombo = reactive({}) // { "feat__tgt": { lower, upper } }

const loading = ref(false)
const error = ref('')

const comboKey = (xf, yt) => `${xf}__${yt}`

onMounted(async () => {
  try {
    const cols = await fetchColumns()
    columns.features = cols.features
    columns.targets = cols.targets
    columns.fabSteps = cols.fab_steps
    Object.assign(dcSpec, cols.dc_spec || {})
  } catch (e) {
    error.value = '백엔드 연결 실패 — uvicorn이 8000 포트에서 실행 중인지 확인하세요.'
  }
})

async function onDraw({ fabStep, xFeatures, yTargets }) {
  loading.value = true
  error.value = ''
  try {
    const [b, t, tbl] = await Promise.all([
      fetchBinned(fabStep, xFeatures, yTargets),
      fetchTimeseries(fabStep, xFeatures, yTargets),
      fetchTable(fabStep, xFeatures, yTargets),
    ])
    binned.value = b
    timeseries.value = t
    tableRows.value = tbl.rows
    // 조합마다 spec 입력 상태 보장 (기존 값 유지)
    b.combos.forEach((c) => {
      const k = comboKey(c.x_feature, c.y_target)
      if (!specByCombo[k]) specByCombo[k] = { lower: null, upper: null }
    })
  } catch (e) {
    error.value = '데이터 요청 실패: ' + (e.message || e)
  } finally {
    loading.value = false
  }
}

// 조합별로 매칭되는 시계열 series(points)를 찾아 묶어준다.
const rows = computed(() => {
  if (!binned.value || !timeseries.value) return []
  return binned.value.combos.map((c) => {
    const tgt = timeseries.value.targets.find((s) => s.name === c.y_target)
    const ftr = timeseries.value.features.find((s) => s.name === c.x_feature)
    return {
      key: comboKey(c.x_feature, c.y_target),
      combo: c,
      targetPoints: tgt ? tgt.points : [],
      featurePoints: ftr ? ftr.points : [],
    }
  })
})

// 테이블의 spec 컬럼: 해당 (feature×target) 조합의 spec
function specFor(xf, yt) { return specByCombo[comboKey(xf, yt)] || {} }
</script>

<template>
  <div class="layout">
    <Sidebar
      :features="columns.features" :targets="columns.targets" :fab-steps="columns.fabSteps"
      @draw="onDraw"
    />

    <main class="main">
      <div class="topbar">
        <div>
          <h1>분석 대시보드</h1>
          <p class="sub">feature × target 조합별 process window</p>
        </div>
        <span v-if="binned" class="step-badge">{{ binned.fab_step }}</span>
      </div>

      <p v-if="loading" class="status">불러오는 중…</p>
      <p v-if="error" class="status error">{{ error }}</p>

      <section class="rows">
        <ComboRow
          v-for="r in rows" :key="r.key"
          :combo="r.combo" :target-points="r.targetPoints" :feature-points="r.featurePoints"
          :spec="specByCombo[r.key]" :dc-spec="dcSpec[r.combo.x_feature] || {}"
        />
        <p v-if="!rows.length && !loading" class="empty">왼쪽에서 선택 후 "차트 작성"을 누르세요.</p>
      </section>

      <section class="table-area">
        <h3 class="pane-title">요약 테이블</h3>
        <DataTable :rows="tableRows" :spec-for="specFor" />
      </section>
    </main>
  </div>
</template>

<style scoped>
.layout { display: flex; height: 100vh; }
.main { flex: 1; display: flex; flex-direction: column; overflow-y: auto; }
.topbar { display: flex; align-items: flex-start; justify-content: space-between; padding: 28px 32px 10px; }
.topbar h1 { font-size: 26px; font-weight: 600; margin: 0; letter-spacing: -0.02em; }
.sub { margin: 3px 0 0; font-size: 14px; color: var(--text-2); }
.step-badge {
  background: var(--text); color: #fff; font-size: 12px; font-weight: 500;
  padding: 6px 14px; border-radius: 999px; letter-spacing: 0.02em;
}
.status { margin: 6px 32px; font-size: 14px; color: var(--text-2); }
.error { color: #d70015; }
.rows { display: flex; flex-direction: column; gap: 18px; padding: 14px 32px; }
.empty { color: #aaa; padding: 60px; text-align: center; font-size: 15px; }
.table-area { padding: 6px 32px 36px; display: flex; flex-direction: column; gap: 10px; }
.pane-title { margin: 0; font-size: 13px; font-weight: 600; color: var(--text-2); text-transform: uppercase; letter-spacing: 0.04em; }
</style>
