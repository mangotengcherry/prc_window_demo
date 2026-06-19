<script setup>
// 레이아웃 + 상태 보유(부모). [Sidebar] + [조건요약/상태] + [조합별 ComboRow] + [Table]
import { ref, reactive, computed, onMounted } from 'vue'
import Sidebar from './components/Sidebar.vue'
import ComboRow from './components/ComboRow.vue'
import DataTable from './components/DataTable.vue'
import { fetchColumns, fetchXFeatureOptions, fetchBinned, fetchTimeseries, fetchTable } from './api/client.js'
import { cpk } from './stats.js'

const columns = ref(null)
const xFeatureOptions = ref([])

const binned = ref(null)
const timeseries = ref(null)
const tableRows = ref([])
const specByCombo = reactive({})

const status = ref('initial') // initial | loading | loaded | empty | error
const errorMsg = ref('')
const lastCond = ref(null)
const lastQueryAt = ref('')

const comboKey = (xf, yt, cfv) => `${xf}__${yt}__${cfv || ''}`

onMounted(async () => {
  try {
    columns.value = await fetchColumns()
  } catch (e) {
    status.value = 'error'
    errorMsg.value = e.message || '컬럼 로드 실패'
  }
})

async function onXoptsChange(p) {
  try {
    const res = await fetchXFeatureOptions(p.fabStep, { matching: p.matching, metroGrade: p.metroGrade, metroCategory: p.metroCategory })
    xFeatureOptions.value = res.features || []
  } catch (e) {
    xFeatureOptions.value = [] // graceful: 옵션 없으면 빈 목록
  }
}

async function onDraw(cond) {
  if (status.value === 'loading') return // 중복요청 방지
  status.value = 'loading'
  errorMsg.value = ''
  try {
    const [b, t, tbl] = await Promise.all([fetchBinned(cond), fetchTimeseries(cond), fetchTable(cond)])
    binned.value = b
    timeseries.value = t
    tableRows.value = tbl.rows
    b.combos.forEach((c) => {
      const k = comboKey(c.x_feature, c.y_target, c.category_feature_value)
      if (!specByCombo[k]) specByCombo[k] = { lower: null, upper: null }
    })
    lastCond.value = cond
    lastQueryAt.value = new Date().toLocaleTimeString()
    status.value = b.combos.length ? 'loaded' : 'empty'
  } catch (e) {
    status.value = 'error' // 마지막 성공 데이터는 유지
    errorMsg.value = e.message || '데이터 요청 실패'
  }
}

const dcSpec = (xf) => columns.value?.dc_spec?.[xf] || {}

// 조합(feature×target) → table 통계 매칭 (μ·σ_overall·σ_within·DC spec)
const statsByCombo = computed(() => {
  const m = {}
  tableRows.value.forEach((r) => { m[`${r.x_feature}__${r.y_target}`] = r })
  return m
})

const rows = computed(() => {
  if (!binned.value || !timeseries.value) return []
  const minN = columns.value?.min_n ?? 10
  return binned.value.combos.map((c) => {
    const tgt = timeseries.value.targets.find((s) => s.name === c.y_target)
    const ftr = timeseries.value.features.find((s) => s.name === c.x_feature)
    const maxN = c.bins.length ? Math.max(...c.bins.map((b) => b.wafer_count)) : 0
    return {
      key: comboKey(c.x_feature, c.y_target, c.category_feature_value),
      combo: c,
      target: tgt || null,
      feature: ftr || null,
      dcSpec: dcSpec(c.x_feature),
      stats: statsByCombo.value[`${c.x_feature}__${c.y_target}`] || null,
      thin: c.bins.length > 0 && maxN < minN,
    }
  })
})

// KPI 밴드 — Cpk(단기 σ)를 DC spec / user spec 기준으로 산출
const kpis = computed(() => {
  const rs = tableRows.value
  if (!rs.length) return null
  const minN = columns.value?.min_n ?? 10
  let wDc = null, wU = null, thinN = 0
  rs.forEach((r) => {
    const u = specFor(r.x_feature, r.y_target)
    const cDc = cpk(r.x_value, r.x_std_within, r.dc_lower, r.dc_upper)
    if (cDc != null) wDc = wDc == null ? cDc : Math.min(wDc, cDc)
    const cU = cpk(r.x_value, r.x_std_within, u.lower, u.upper)
    if (cU != null) wU = wU == null ? cU : Math.min(wU, cU)
    if (r.n != null && r.n < minN) thinN++
  })
  return { combos: rs.length, obs: timeseries.value?.n_total ?? null, worstCpkDc: wDc, worstCpkUser: wU, thinN }
})
function cpkClass(v) { return v == null ? '' : (v < 1 ? 'bad' : (v < 1.33 ? 'warn' : 'good')) }

const condSummary = computed(() => {
  const c = lastCond.value
  if (!c) return ''
  return `${c.line_id} · ${c.product} · ${c.category}/${c.eds_step} · ${c.fab_step} · ${c.date_range.start_date}~${c.date_range.end_date}`
})

function specFor(xf, yt) { return specByCombo[comboKey(xf, yt)] || {} }
</script>

<template>
  <div class="layout">
    <Sidebar :columns="columns" :x-feature-options="xFeatureOptions" :loading="status === 'loading'"
             @xopts-change="onXoptsChange" @draw="onDraw" />

    <main class="main">
      <header class="topbar">
        <div>
          <h1>분석 대시보드</h1>
          <p class="sub">{{ condSummary || 'feature × target 조합별 process window' }}</p>
        </div>
        <div class="meta">
          <span class="badge" :class="status">{{ status }}</span>
          <span v-if="lastQueryAt" class="qt">조회 {{ lastQueryAt }}</span>
        </div>
      </header>

      <p v-if="status === 'error'" class="banner err">⚠ {{ errorMsg }}</p>
      <p v-else-if="status === 'loading'" class="banner">불러오는 중…</p>
      <p v-else-if="status === 'empty'" class="banner">조건에 해당하는 데이터가 없습니다. (기간/관측 여부를 확인하세요)</p>
      <p v-else-if="status === 'initial'" class="banner">왼쪽에서 분석 조건을 선택하고 "차트 작성"을 누르세요.</p>

      <section v-if="kpis" class="kpis">
        <div class="kpi" title="현재 표시된 (feature × target) 조합 수">
          <span class="kv">{{ kpis.combos }}</span><span class="kl">조합 ⓘ</span></div>
        <div class="kpi" title="선택 기간 내 wafer 행 수 (관측 + 미관측). 기준: fab_track_out_time">
          <span class="kv">{{ kpis.obs ?? '-' }}</span><span class="kl">표본 수(기간) ⓘ</span></div>
        <div class="kpi" :title="'모든 조합의 Cpk(DC spec 기준) 중 최솟값. user 입력 없이 항상 산출.\nCpk = min(DSU−μ, μ−DSL) / (3σ_단기)\nσ_단기 = 이동범위 MR/1.128\n< 1.00 위험(빨강) · < 1.33 주의(노랑)'">
          <span class="kv" :class="cpkClass(kpis.worstCpkDc)">{{ kpis.worstCpkDc == null ? '-' : kpis.worstCpkDc.toFixed(2) }}</span><span class="kl">최저 Cpk(DC) ⓘ</span></div>
        <div class="kpi" :title="'user spec을 입력한 조합들의 Cpk 중 최솟값.\nCpk = min(USU−μ, μ−USL) / (3σ_단기)\nuser spec 미입력이면 \'-\''">
          <span class="kv" :class="cpkClass(kpis.worstCpkUser)">{{ kpis.worstCpkUser == null ? '-' : kpis.worstCpkUser.toFixed(2) }}</span><span class="kl">최저 Cpk(user) ⓘ</span></div>
        <div class="kpi" :title="'신뢰도 낮은 조합 수.\n조합의 최대 bin 표본수 < min_n(=' + (columns?.min_n ?? 10) + ') 이면 thin\n표본 부족으로 평균이 불안정'">
          <span class="kv" :class="{ warnum: kpis.thinN }">{{ kpis.thinN }}</span><span class="kl">thin 조합 ⓘ</span></div>
      </section>

      <section class="rows">
        <ComboRow v-for="r in rows" :key="r.key" :combo="r.combo"
                  :target="r.target" :feature="r.feature" :stats="r.stats"
                  :spec="specByCombo[r.key]" :dc-spec="r.dcSpec" :thin="r.thin"
                  :min-n="columns?.min_n ?? 10" :sampled="timeseries?.sampled" />
      </section>

      <section v-if="tableRows.length" class="table-area">
        <h3 class="pane-title">요약 테이블</h3>
        <DataTable :rows="tableRows" :spec-for="specFor" />
      </section>
    </main>
  </div>
</template>

<style scoped>
.layout { display: flex; height: 100vh; }
.main { flex: 1; display: flex; flex-direction: column; overflow-y: auto; }
.topbar { display: flex; align-items: flex-start; justify-content: space-between; padding: 24px 32px 8px; }
.topbar h1 { font-size: 24px; font-weight: 600; margin: 0; letter-spacing: -0.02em; }
.sub { margin: 3px 0 0; font-size: 13px; color: var(--text-2); }
.meta { display: flex; align-items: center; gap: 10px; }
.qt { font-size: 12px; color: var(--text-2); }
.badge { font-size: 11px; font-weight: 600; padding: 4px 11px; border-radius: 999px; text-transform: uppercase; letter-spacing: .03em; background: #e5e7eb; color: #374151; }
.badge.loaded { background: #dcfce7; color: #166534; }
.badge.loading { background: #dbeafe; color: #1e40af; }
.badge.error { background: #fee2e2; color: #991b1b; }
.badge.empty { background: #fef9c3; color: #854d0e; }
.banner { margin: 6px 32px; font-size: 14px; color: var(--text-2); }
.banner.err { color: #d70015; }
.kpis { display: flex; gap: 12px; padding: 8px 32px 2px; flex-wrap: wrap; }
.kpi { background: var(--surface); border: 1px solid var(--border); border-radius: 14px; box-shadow: var(--shadow-sm); padding: 10px 18px; min-width: 96px; display: flex; flex-direction: column; gap: 2px; }
.kv { font-size: 20px; font-weight: 700; letter-spacing: -0.02em; }
.kv.good { color: #166534; } .kv.warn { color: #854d0e; } .kv.bad { color: #991b1b; } .kv.warnum { color: #854d0e; }
.kl { font-size: 11px; color: var(--text-2); text-transform: uppercase; letter-spacing: .03em; }
.rows { display: flex; flex-direction: column; gap: 16px; padding: 12px 32px; }
.table-area { padding: 6px 32px 36px; display: flex; flex-direction: column; gap: 10px; }
.pane-title { margin: 0; font-size: 13px; font-weight: 600; color: var(--text-2); text-transform: uppercase; letter-spacing: .04em; }
</style>
