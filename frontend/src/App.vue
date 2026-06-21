<script setup>
// 레이아웃 + 상태 보유(부모). [Sidebar] + [조건요약/상태] + [조합별 ComboRow] + [Table]
import { ref, shallowRef, reactive, computed, watch, onMounted, defineAsyncComponent } from 'vue'
import Sidebar from './components/Sidebar.vue'
import ComboRow from './components/ComboRow.vue'
import DataTable from './components/DataTable.vue'
// 보조 분석 패널(차트 3개) — 결과가 있을 때만 필요 → 지연 로드로 초기 번들·파싱 분리
const InteractionPanel = defineAsyncComponent(() => import('./components/InteractionPanel.vue'))
import { fetchColumns, fetchXFeatureOptions, fetchBinned, fetchTimeseries, fetchTable, fetchDrivers, downloadRaw } from './api/client.js'
import { cpk, capabilityDiagnosis, cpkBand, DEFAULT_CAP_THRESHOLDS } from './stats.js'
import { SERIES } from './palette.js'
import { queryId, shareUrl, condFromUrl } from './share.js'

const columns = ref(null)
const xFeatureOptions = ref([])
const sidebarRef = ref(null)

// 서버 소유 대용량 페이로드 → shallowRef (내부를 깊은 reactive로 만들지 않아 변환·읽기 비용 절감)
const binned = shallowRef(null)
const timeseries = shallowRef(null)
const tableRows = shallowRef([])
const driversData = shallowRef([]) // 인사이트 2: target별 영향 요인 랭킹
const specByCombo = reactive({})

// 공정능력 진단 임계값 — 사용자 커스텀(localStorage 보존). 팀 표준에 맞게 조정.
const CAP_LS = 'capThresholds'
const capThresholds = reactive({ ...DEFAULT_CAP_THRESHOLDS })
try { Object.assign(capThresholds, JSON.parse(localStorage.getItem(CAP_LS) || '{}')) } catch { /* noop */ }
const showCapSettings = ref(false)
function saveCapThresholds() { try { localStorage.setItem(CAP_LS, JSON.stringify(capThresholds)) } catch { /* noop */ } }
function resetCapThresholds() { Object.assign(capThresholds, DEFAULT_CAP_THRESHOLDS); saveCapThresholds() }

// Cpk within σ 부분군(rational subgroup) — EQP/chamber/lot. Ppk는 항상 전체 σ.
const cpkSubgroup = ref(localStorage.getItem('cpkSubgroup') ?? 'EQP_CH')
const cpkSubgroupOptions = computed(() => {
  const cats = columns.value?.category_features || []
  const pref = ['EQP_CH', 'EQP', 'EQP_MODEL', 'PPID', 'ECO'].filter((k) => cats.includes(k))
  const rest = cats.filter((k) => !pref.includes(k))
  return ['', 'root_lot_id', ...pref, ...rest]  // ''=시간 I-MR
})
const cpkSubgroupLabel = (v) => (v ? (v === 'root_lot_id' ? 'root_lot' : v) : '시간 I-MR')
watch(cpkSubgroup, (v) => {
  try { localStorage.setItem('cpkSubgroup', v) } catch { /* noop */ }
  if (lastCond.value) refetchTable()
})
async function refetchTable() {
  try {
    const tbl = await fetchTable({ ...lastCond.value, cpk_subgroup: cpkSubgroup.value || null,
      selection: selection.value ? { time_range: selection.value } : null })
    tableRows.value = tbl.rows
  } catch (e) { errorMsg.value = e.message || '요약표 재집계 실패' }
}

const status = ref('initial') // initial | loading | loaded | empty | error
const errorMsg = ref('')
const lastCond = ref(null)
const lastQueryAt = ref('')
const showEstimate = ref(false) // 미관측 wafer 추정 y 표시(분리 모드 시계열)
const initialCond = ref(condFromUrl()) // 공유 URL(?q=)로 들어온 경우 복원
const copied = ref(false)
const selection = ref(null) // linked brushing: [startISO, endISO] | null
const reaggregating = ref(false) // brush 재집계 진행중(피드백용)

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
  selection.value = null // 새 분석은 brush 선택 초기화
  try {
    const [b, t, tbl, dr] = await Promise.all([fetchBinned(cond), fetchTimeseries(cond),
      fetchTable({ ...cond, cpk_subgroup: cpkSubgroup.value || null }), fetchDrivers(cond)])
    binned.value = b
    timeseries.value = t
    tableRows.value = tbl.rows
    driversData.value = dr.targets || []
    const mode = cond.category_feature?.chart_mode
    b.combos.forEach((c) => {
      // 겹쳐보기(multi_line)는 (x,y) 1행에 공유 spec, 분리(split)는 분할값별 spec
      const cfv = mode === 'multi_line' ? null : c.category_feature_value
      const k = comboKey(c.x_feature, c.y_target, cfv)
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
const targetGroupDefs = computed(() => lastCond.value?.y_target_groups || [])
// 교호작용 패널용 라벨(x_feature key → 표시명)
const interactionLabels = computed(() => {
  const m = {}
  ;(binned.value?.combos || []).forEach((c) => { m[c.x_feature] = c.x_feature_display_name })
  return m
})

// 조합(feature×target×분할값) → table 통계 매칭 (μ·σ_overall·σ_within·DC spec)
const statsByCombo = computed(() => {
  const m = {}
  tableRows.value.forEach((r) => { m[comboKey(r.x_feature, r.y_target, r.category_feature_value)] = r })
  return m
})

const sameCfv = (a, b) => (a ?? null) === (b ?? null)
const isThin = (c, minN) => { const mx = c.bins.length ? Math.max(...c.bins.map((b) => b.wafer_count)) : 0; return c.bins.length > 0 && mx < minN }
// 시계열 series를 (name|cfv) 키 맵으로 1회 인덱싱 → 조합별 O(1) 매칭(이전 O(combos×series) find)
const seriesIndex = computed(() => {
  const tm = {}, fm = {}
  const ts = timeseries.value
  if (ts) {
    ts.targets.forEach((s) => { tm[`${s.name}|${s.category_feature_value ?? ''}`] = s })
    ts.features.forEach((s) => { fm[`${s.name}|${s.category_feature_value ?? ''}`] = s })
  }
  return { tm, fm }
})
const tgtOf = (c, cfv) => seriesIndex.value.tm[`${c.y_target}|${cfv ?? ''}`] || null
const ftrOf = (c, cfv) => seriesIndex.value.fm[`${c.x_feature}|${cfv ?? ''}`] || null

const rows = computed(() => {
  if (!binned.value || !timeseries.value) return []
  const minN = columns.value?.min_n ?? 10
  const multi = lastCond.value?.category_feature?.chart_mode === 'multi_line'

  if (multi) {
    // (x_feature × y_target) 1행에 분할값들을 겹쳐 표시
    const groups = new Map()
    binned.value.combos.forEach((c) => {
      const gk = `${c.x_feature}__${c.y_target}`
      if (!groups.has(gk)) groups.set(gk, [])
      groups.get(gk).push(c)
    })
    return [...groups.values()].map((combos) => {
      const f = combos[0]
      const members = combos.map((c, i) => ({
        cfv: c.category_feature_value,
        combo: c,
        target: tgtOf(c, c.category_feature_value),
        feature: ftrOf(c, c.category_feature_value),
        stats: statsByCombo.value[comboKey(c.x_feature, c.y_target, c.category_feature_value)] || null,
        color: SERIES[i % SERIES.length],
      }))
      return {
        key: comboKey(f.x_feature, f.y_target, ''),  // 공유 spec
        multi: true,
        combo: { x_feature: f.x_feature, x_feature_display_name: f.x_feature_display_name, y_target: f.y_target, category_feature_name: f.category_feature_name },
        members,
        dcSpec: dcSpec(f.x_feature),
        thin: combos.some((c) => isThin(c, minN)),
      }
    })
  }

  const ests = timeseries.value.estimates || []
  return binned.value.combos.map((c) => {
    const cfv = c.category_feature_value
    return {
      key: comboKey(c.x_feature, c.y_target, cfv),
      multi: false,
      combo: c,
      target: tgtOf(c, cfv),
      feature: ftrOf(c, cfv),
      estimate: ests.find((e) => e.x_feature === c.x_feature && e.y_target === c.y_target && sameCfv(e.category_feature_value, cfv)) || null,
      dcSpec: dcSpec(c.x_feature),
      stats: statsByCombo.value[comboKey(c.x_feature, c.y_target, cfv)] || null,
      thin: isThin(c, minN),
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
    const u = specFor(r.x_feature, r.y_target, r.category_feature_value)
    const cDc = cpk(r.x_value, r.x_std_within, r.dc_lower, r.dc_upper)
    if (cDc != null) wDc = wDc == null ? cDc : Math.min(wDc, cDc)
    const cU = cpk(r.x_value, r.x_std_within, u.lower, u.upper)
    if (cU != null) wU = wU == null ? cU : Math.min(wU, cU)
    if (r.n != null && r.n < minN) thinN++
  })
  return { combos: rs.length, obs: timeseries.value?.n_total ?? null, worstCpkDc: wDc, worstCpkUser: wU, thinN }
})
function cpkClass(v) { return cpkBand(v, capThresholds) }

// 인사이트 5: 조건(분할값) 비교 랭킹 — (feature×target)별로 분할값을 target 평균순 정렬 + Cpk
const conditionCompare = computed(() => {
  const g = {}
  tableRows.value.forEach((r) => {
    if (r.category_feature_value == null) return  // 분할 없으면 비교 대상 아님
    const k = r.x_feature + '__' + r.y_target
    if (!g[k]) g[k] = { key: k, feature: r.x_feature_display_name || r.x_feature, target: r.y_target, items: [] }
    g[k].items.push({ cfv: r.category_feature_value, mean: r.mean, cpkc: cpk(r.x_value, r.x_std_within, r.dc_lower, r.dc_upper), n: r.n })
  })
  return Object.values(g)
    .map((x) => ({ ...x, items: x.items.filter((i) => i.mean != null).sort((a, b) => b.mean - a.mean) }))
    .filter((x) => x.items.length > 1)
})

// 인사이트 3: 공정능력 진단 — feature별 Cpk·Ppk + 진단(능력×안정성×중심). Cpk(DC)는 feature 단위.
const capability = computed(() => {
  const m = {}
  tableRows.value.forEach((r) => {
    if (r.x_value == null || r.dc_lower == null || r.dc_upper == null) return
    if (!m[r.x_feature] || (r.n || 0) > (m[r.x_feature].n || 0)) {
      m[r.x_feature] = { feature: r.x_feature, name: r.x_feature_display_name || r.x_feature, row: r, n: r.n }
    }
  })
  const minN = columns.value?.min_n ?? 10
  return Object.values(m).map((e) => {
    const r = e.row
    const dx = capabilityDiagnosis(r.x_value, r.x_std_within, r.x_std, r.dc_lower, r.dc_upper, capThresholds)
    const cpkDc = dx ? dx.cpk : cpk(r.x_value, r.x_std_within, r.dc_lower, r.dc_upper)
    return { feature: e.feature, name: e.name, n: e.n, dx, cpkDc, thin: (e.n ?? 0) < minN,
             meanDrift: tsDriftByFeature.value[e.feature] || null }
  }).filter((e) => e.cpkDc != null).sort((a, b) => a.cpkDc - b.cpkDc)
})
// 시계열 평균 drift(μ 이동) — feature명으로 매핑. 공정능력의 산포 drift(σ)와 교차 표시.
const tsDriftByFeature = computed(() => {
  const m = {}
  ;(timeseries.value?.features || []).forEach((f) => { if (f.drift?.flagged && !m[f.name]) m[f.name] = f.drift })
  return m
})

// 인사이트 1: lag 기반 관리이탈 사전 예측 — 미확보 wafer 추정이 target 관리한계를 벗어날 예측 수 + 추정 평균 이동(σ)
const forecast = computed(() => {
  const ests = (timeseries.value?.estimates || []).filter((e) => e.forecast)
  if (!ests.length) return null
  let oos = 0, n = 0, maxShift = 0, best = null
  ests.forEach((e) => {
    oos += e.forecast.oos; n += e.forecast.n
    if (Math.abs(e.forecast.shift) > Math.abs(maxShift)) maxShift = e.forecast.shift
    if (!best || (e.fit_summary?.r2 ?? 0) > (best.fit_summary?.r2 ?? 0)) best = e
  })
  return { oos, n, maxShift, r2: best?.fit_summary?.r2 ?? null,
           lowConf: !!best?.forecast?.low_conf, extrap: best?.forecast?.extrap ?? 0 }
})
// 관리이탈 예보 KPI 툴팁 — 신뢰 가드(저R²·외삽) 사유 포함
const forecastTitle = computed(() => {
  const f = forecast.value
  if (!f) return ''
  let t = `lag 기반 사전예측: 미확보 wafer를 y~x 회귀로 추정 → target 관리한계(±3σ) 초과 예측 수.\n미확보 batch 추정 평균이 관측 평균 대비 ${f.maxShift >= 0 ? '+' : ''}${f.maxShift}σ 이동(잠복 drift).\n신뢰도: 추정 R²=${f.r2 == null ? '-' : f.r2.toFixed(2)} · 외삽 ${Math.round((f.extrap || 0) * 100)}%(추정 X가 관측 범위 밖)`
  if (f.lowConf) t += `\n⚠ 신뢰 낮음 → "참고용"으로 강등(R²<0.2 또는 외삽 다수). 단정 경보 아님.`
  return t
})

const condSummary = computed(() => {
  const c = lastCond.value
  if (!c) return ''
  return `${c.line_id} · ${c.product} · ${c.category}/${c.eds_step} · ${c.fab_step} · ${c.date_range.start_date}~${c.date_range.end_date}`
})

// 겹쳐보기(multi_line)는 (x,y) 공유 spec → cfv 무시. 분리(split)는 분할값별 spec.
const isMultiMode = computed(() => lastCond.value?.category_feature?.chart_mode === 'multi_line')
function specFor(xf, yt, cfv) {
  return specByCombo[comboKey(xf, yt, isMultiMode.value ? null : cfv)] || {}
}

// provenance(출처·기간·표본·쿼리ID) + 공유 링크
const provenance = computed(() => {
  const c = lastCond.value
  if (!c) return null
  const tb = timeseries.value?.time_basis
  return {
    source: `demo · ${c.line_id}/${c.product} · ${c.category}/${c.eds_step} · ${c.fab_step}`,
    fabRange: `${c.date_range.start_date} ~ ${c.date_range.end_date}`,
    edsRange: c.target_date_range ? `${c.target_date_range.start_date} ~ ${c.target_date_range.end_date}` : '-',
    n: timeseries.value?.n_total ?? '-',
    qid: queryId(c),
    lagDays: tb?.expected_target_lag_days ?? null,
  }
})
// linked brushing — 시계열 brush 구간으로 window·table 재집계 (시계열은 전체 유지)
async function onBrush(range) {
  selection.value = range
  await reaggregate()
}
let reaggSeq = 0
async function reaggregate() {
  if (!lastCond.value) return
  const seq = ++reaggSeq
  reaggregating.value = true
  try {
    const cond = { ...lastCond.value, cpk_subgroup: cpkSubgroup.value || null,
      selection: selection.value ? { time_range: selection.value } : null }
    const [b, tbl] = await Promise.all([fetchBinned(cond), fetchTable(cond)])
    if (seq !== reaggSeq) return // 더 최신 brush 요청이 있으면 폐기(stale 방지)
    binned.value = b
    tableRows.value = tbl.rows
  } catch (e) {
    if (seq === reaggSeq) errorMsg.value = e.message || '재집계 실패'
  } finally {
    if (seq === reaggSeq) reaggregating.value = false
  }
}
function clearSelection() { selection.value = null; reaggregate() }
const selLabel = computed(() => selection.value ? `${selection.value[0].slice(0, 10)} ~ ${selection.value[1].slice(0, 10)}` : '')

async function copyShare() {
  if (!lastCond.value) return
  try {
    await navigator.clipboard.writeText(shareUrl(lastCond.value))
    copied.value = true
    setTimeout(() => { copied.value = false }, 1500)
  } catch { /* clipboard 미지원/거부 시 무시 */ }
}

// 현재 분석 조건의 wafer 원시데이터 CSV 다운로드 (brush 선택 구간 반영)
const downloading = ref(false)
async function downloadCsv() {
  if (!lastCond.value || downloading.value) return
  downloading.value = true
  try {
    const cond = { ...lastCond.value, selection: selection.value ? { time_range: selection.value } : null }
    await downloadRaw(cond)
  } catch (e) {
    errorMsg.value = e.message || 'CSV 다운로드 실패'
  } finally {
    downloading.value = false
  }
}
</script>

<template>
  <div class="layout">
    <Sidebar ref="sidebarRef" :columns="columns" :x-feature-options="xFeatureOptions" :loading="status === 'loading'"
             :initial="initialCond" @xopts-change="onXoptsChange" @draw="onDraw" />

    <main class="main">
      <header class="topbar">
        <div>
          <h1>분석 대시보드</h1>
          <p class="sub">{{ condSummary || 'feature × target 조합별 process window' }}</p>
        </div>
        <div class="meta">
          <label class="esttog" :class="{ on: showEstimate }" title="미관측 wafer의 추정 y를 시계열에 표시 (y~x 회귀, 관측값과 다른 표식). 분리 모드 적용">
            <input type="checkbox" v-model="showEstimate" /> 추정 y
          </label>
          <span v-if="showEstimate && isMultiMode" class="estnote" title="겹쳐보기(multi-line) 모드에서는 추정 y를 표시하지 않습니다. 분리 모드에서 확인하세요.">↳ 분리 모드에서 표시</span>
          <button v-if="lastCond" class="sharebtn" :title="'현재 분석 조건을 URL로 복사 (같은 링크로 재현)'" @click="copyShare">{{ copied ? '복사됨 ✓' : '🔗 공유' }}</button>
          <button v-if="lastCond" class="sharebtn" :disabled="downloading" :title="'현재 조건의 wafer 원시데이터(raw)를 CSV로 다운로드. 식별자(root_lot_id·wafer_id)·선택 feature/target 포함'" @click="downloadCsv">{{ downloading ? '생성 중…' : '⬇ CSV' }}</button>
          <span class="badge" :class="status">{{ status }}</span>
          <span v-if="lastQueryAt" class="qt">조회 {{ lastQueryAt }}</span>
        </div>
      </header>

      <div v-if="provenance" class="prov">
        <span><b>출처</b> {{ provenance.source }}</span>
        <span><b>분석기간 · fab</b> {{ provenance.fabRange }}</span>
        <span><b>y확보 · eds</b> {{ provenance.edsRange }}</span>
        <span><b>표본</b> {{ provenance.n }}</span>
        <span><b>쿼리</b> {{ provenance.qid }}</span>
      </div>

      <p v-if="status === 'error'" class="banner err">⚠ {{ errorMsg }}</p>
      <p v-else-if="status === 'loading'" class="banner">불러오는 중…</p>
      <p v-else-if="status === 'empty'" class="banner">조건에 해당하는 데이터가 없습니다. (기간/관측 여부를 확인하세요)</p>
      <div v-else-if="status === 'initial'" class="hero">
        <h2>FAB feature × EDS target 공정 윈도우 분석</h2>
        <p>조합별 <b>Window</b>(y vs x)·<b>시계열</b>·<b>Cpk/Ppk</b>, <b>교호작용</b>(scatter·heatmap), <b>추정 y</b>, 기간 <b>brush 재집계</b>를 한 화면에서.</p>
        <ol>
          <li><b>조건·기간</b> 확인 — 기본값이 채워져 있습니다</li>
          <li><b>Y target · X feature</b> 선택 (합산 그룹 · 값별 분할 옵션)</li>
          <li><b>차트 작성</b> → 각 행에서 <b>user spec</b>(lower/upper) 입력하면 Cpk 비교</li>
        </ol>
        <button class="hero-btn" @click="sidebarRef?.drawWithDefaults()">기본값으로 바로 작성 ▶</button>
        <p class="hero-sub">또는 왼쪽 패널에서 직접 조건을 고르세요.</p>
      </div>

      <div v-if="selection" class="selbar">
        <span>⏱ 기간 선택 <b>{{ selLabel }}</b> · <span v-if="reaggregating" class="reagg">재집계 중…</span><span v-else>window·요약표가 이 구간 wafer로 재집계됨 (시계열은 전체)</span></span>
        <button @click="clearSelection">전체 보기</button>
      </div>

      <section v-if="kpis" class="kpis">
        <div class="kpi" title="현재 표시된 (feature × target) 조합 수">
          <span class="kv">{{ kpis.combos }}</span><span class="kl">조합</span></div>
        <div class="kpi" title="선택 기간 내 wafer 행 수 (관측 + 미관측). 기준: fab_track_out_time">
          <span class="kv">{{ kpis.obs ?? '-' }}</span><span class="kl">표본 수(기간)</span></div>
        <div class="kpi" :class="'st-' + cpkClass(kpis.worstCpkDc)" :title="'모든 조합의 Cpk(DC spec 기준) 중 최솟값. user 입력 없이 항상 산출.\nCpk = min(DSU−μ, μ−DSL) / (3σ_단기)\nσ_단기 = 이동범위 MR/1.128\n< 1.00 위험(빨강) · < 1.33 주의(노랑)'">
          <span class="kv" :class="cpkClass(kpis.worstCpkDc)">{{ kpis.worstCpkDc == null ? '-' : kpis.worstCpkDc.toFixed(2) }}</span><span class="kl">최저 Cpk(DC)</span></div>
        <div class="kpi" :class="'st-' + cpkClass(kpis.worstCpkUser)" :title="'user spec을 입력한 조합들의 Cpk 중 최솟값.\nCpk = min(USU−μ, μ−USL) / (3σ_단기)\nuser spec 미입력이면 \'-\''">
          <span class="kv" :class="cpkClass(kpis.worstCpkUser)">{{ kpis.worstCpkUser == null ? '-' : kpis.worstCpkUser.toFixed(2) }}</span><span class="kl">최저 Cpk(user)</span></div>
        <div class="kpi" :title="'표본 부족 조합 수.\n조합의 최대 bin 표본수 < min_n(=' + (columns?.min_n ?? 10) + ')\n표본이 적어 평균이 불안정한 조합'">
          <span class="kv" :class="{ warnum: kpis.thinN }">{{ kpis.thinN }}</span><span class="kl">표본 부족 조합</span></div>
        <div v-if="forecast" class="kpi" :class="forecast.lowConf ? '' : (forecast.oos > 0 ? 'st-bad' : (Math.abs(forecast.maxShift) >= 1 ? 'st-warn' : ''))"
          :title="forecastTitle">
          <span class="kv" :class="forecast.lowConf ? 'muted' : (forecast.oos > 0 ? 'bad' : (Math.abs(forecast.maxShift) >= 1 ? 'warn' : ''))">{{ forecast.oos }}<small class="shift" v-if="Math.abs(forecast.maxShift) >= 0.5">{{ forecast.maxShift >= 0 ? '+' : '' }}{{ forecast.maxShift }}σ</small></span><span class="kl">관리이탈 예상{{ forecast.lowConf ? '(참고용)' : '' }} ⓘ</span></div>
      </section>

      <section v-if="status === 'loaded' && driversData.length" class="drivers-area">
        <h3 class="pane-title">영향 요인 (driver) 랭킹 <small>선택 target에 영향이 큰 feature 순 (|corr|, 관측 wafer)</small></h3>
        <div class="dgrid">
          <div v-for="t in driversData" :key="t.target" class="dcard">
            <div class="dtitle">{{ t.target }}</div>
            <div v-for="d in t.drivers.slice(0, 5)" :key="d.feature" class="drow" :title="d.display_name + ' · corr ' + d.corr + ' · n=' + d.n">
              <span class="dname">{{ d.display_name }}</span>
              <div class="dbar"><div class="dfill" :class="{ neg: d.corr < 0 }" :style="{ width: Math.max(2, d.abs * 100) + '%' }"></div></div>
              <span class="dval" :class="{ neg: d.corr < 0 }">{{ d.corr >= 0 ? '+' : '' }}{{ d.corr }}</span>
            </div>
            <p v-if="!t.drivers.length" class="dnone">표본 부족</p>
          </div>
        </div>
      </section>

      <section v-if="status === 'loaded' && capability.length" class="drivers-area">
        <h3 class="pane-title">공정능력 진단 (Cpk·Ppk)
          <small>DC spec · 약한 순. Cpk≫Ppk=산포 drift / 둘다 낮음=능력부족 / 둘다 높음=spec 여유 · <b>Cpk within={{ cpkSubgroupLabel(cpkSubgroup) }}</b> (마우스=조치)</small>
          <button class="capset-btn" :class="{ on: showCapSettings }" @click="showCapSettings = !showCapSettings" title="진단 임계값·부분군 설정">⚙ 진단 설정</button>
        </h3>
        <div v-if="showCapSettings" class="capset">
          <label class="capset-sg">Cpk 부분군
            <select v-model="cpkSubgroup">
              <option v-for="o in cpkSubgroupOptions" :key="o" :value="o">{{ cpkSubgroupLabel(o) }}</option>
            </select>
          </label>
          <span class="capset-div">|</span>
          <label>위험 &lt; <input type="number" step="0.01" min="0" v-model.number="capThresholds.incapable" @change="saveCapThresholds" /></label>
          <label>충분 ≥ <input type="number" step="0.01" min="0" v-model.number="capThresholds.capable" @change="saveCapThresholds" /></label>
          <label>과잉 ≥ <input type="number" step="0.01" min="0" v-model.number="capThresholds.over" @change="saveCapThresholds" /></label>
          <label>drift 비율 ≥ <input type="number" step="0.05" min="1" v-model.number="capThresholds.driftRatio" @change="saveCapThresholds" /></label>
          <button class="capset-reset" @click="resetCapThresholds">기본값</button>
          <span class="capset-hint">Cpk=군내(within) σ — 합리적 부분군(EQP/chamber/lot). Ppk=전체 σ. Cpk≫Ppk면 부분군 간(설비 등) 차이 큼.</span>
        </div>
        <div class="capgrid2">
          <div v-for="c in capability" :key="c.feature" class="caprow2" :title="c.dx ? c.dx.msg : (c.name + ' · n=' + c.n)">
            <span class="dname">{{ c.name }}</span>
            <span class="cpp">Cpk <b :class="cpkClass(c.dx ? c.dx.cpk : c.cpkDc)">{{ (c.dx ? c.dx.cpk : c.cpkDc).toFixed(2) }}</b></span>
            <span class="cpp">Ppk <b :class="cpkClass(c.dx ? c.dx.ppk : null)">{{ c.dx ? c.dx.ppk.toFixed(2) : '-' }}</b></span>
            <span class="dxtags">
              <span v-if="c.thin" class="dxtag dx-thin">표본 부족</span>
              <span v-else-if="c.dx" class="dxtag" :class="'dx-' + c.dx.state">{{ c.dx.label }}</span>
              <span v-if="c.meanDrift" class="dxtag dx-mean"
                :title="'시계열 평균이 최근 ' + (c.meanDrift.shift >= 0 ? '+' : '') + c.meanDrift.shift + 'σ 이동(평균/레벨 drift). 산포 drift와 별개 신호 — 함께 뜨면 추세+불안정.'">평균 drift {{ c.meanDrift.direction === 'up' ? '↑' : '↓' }}</span>
            </span>
          </div>
        </div>
      </section>

      <section v-if="status === 'loaded' && conditionCompare.length" class="drivers-area">
        <h3 class="pane-title">조건 비교 (랭킹) <small>분할값별 target 평균 순 — 어느 조건이 나은지 (Cpk 함께)</small></h3>
        <div class="dgrid">
          <div v-for="g in conditionCompare" :key="g.key" class="dcard">
            <div class="dtitle">{{ g.feature }} × {{ g.target }}</div>
            <table class="ctab">
              <tr v-for="(c, i) in g.items" :key="c.cfv" :class="{ best: i === 0 }">
                <td class="crank">{{ i + 1 }}</td>
                <td class="ccfv">{{ c.cfv }}</td>
                <td class="cnum">{{ c.mean == null ? '-' : c.mean.toFixed(1) }}</td>
                <td><span class="cpkv" :class="cpkClass(c.cpkc)">{{ c.cpkc == null ? '-' : c.cpkc.toFixed(2) }}</span></td>
                <td class="cn">n={{ c.n }}</td>
              </tr>
            </table>
          </div>
        </div>
      </section>

      <section class="rows">
        <ComboRow v-for="(r, i) in rows" :key="r.key" :combo="r.combo"
                  :target="r.target" :feature="r.feature" :stats="r.stats"
                  :multi="r.multi" :members="r.members"
                  :estimate="r.estimate" :show-estimate="showEstimate"
                  :spec="specByCombo[r.key]" :dc-spec="r.dcSpec" :thin="r.thin"
                  :min-n="columns?.min_n ?? 10" :sampled="timeseries?.sampled" :cap-thresholds="capThresholds"
                  :first="i === 0" :selection="selection" @brush="onBrush" />
      </section>

      <section v-if="tableRows.length" class="table-area">
        <h3 class="pane-title">요약 테이블</h3>
        <DataTable :rows="tableRows" :spec-for="specFor" :target-groups="targetGroupDefs" />
      </section>

      <section v-if="status === 'loaded' && lastCond" class="ix-area">
        <InteractionPanel :cond="lastCond" :labels="interactionLabels" :min-n="columns?.min_n ?? 10" />
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
.meta { display: flex; align-items: center; gap: 8px; }
.qt { font-size: 12px; color: var(--text-2); }
.esttog { display: flex; align-items: center; gap: 5px; font-size: 12px; font-weight: 600; color: var(--text-2); padding: 4px 10px; border: 1px solid var(--border); border-radius: 999px; background: #fff; cursor: pointer; }
.esttog.on { color: var(--accent); border-color: var(--accent); background: var(--accent-weak); }
.esttog input { width: 13px; height: 13px; accent-color: var(--accent); }
.estnote { font-size: 10px; font-weight: 600; color: #92400e; background: #fef3c7; padding: 2px 7px; border-radius: 999px; cursor: help; }
.sharebtn { font-size: 12px; font-weight: 600; color: var(--accent); background: #fff; border: 1px solid var(--accent); border-radius: 999px; padding: 4px 12px; cursor: pointer; }
.sharebtn:hover { background: var(--accent-weak); }
.sharebtn:disabled { opacity: .6; cursor: default; }
.badge { font-size: 11px; font-weight: 600; padding: 4px 11px; border-radius: 999px; text-transform: uppercase; letter-spacing: .03em; background: #e5e7eb; color: #374151; }
.badge.loaded { background: #dcfce7; color: #166534; }
.badge.loading { background: #dbeafe; color: #1e40af; }
.badge.error { background: #fee2e2; color: #991b1b; }
.badge.empty { background: #fef9c3; color: #854d0e; }
/* provenance: 필드 사이 구분선 + 라벨(크롬)/값(콘텐츠) 위계 분리 */
.prov { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 0; margin: 14px 32px 0; padding: 8px 14px; background: var(--surface-2); border: 1px solid var(--border); border-radius: 10px; font-size: 11.5px; color: var(--text); }
.prov > span { padding: 0 14px; border-left: 1px solid var(--border); line-height: 1.4; }
.prov > span:first-child { padding-left: 0; border-left: none; }
.prov b { font-weight: 600; color: var(--text-2); text-transform: uppercase; font-size: 10px; letter-spacing: .04em; margin-right: 5px; }
.prov .lag { color: #92400e; background: #fef3c7; padding: 1px 8px; border-radius: 999px; font-weight: 600; cursor: help; border-left: none; margin-left: 4px; }
.selbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin: 14px 32px 0; padding: 8px 14px; background: var(--accent-weak); border: 1px solid var(--accent); border-radius: 10px; font-size: 12.5px; color: var(--text); }
.selbar b { color: var(--accent); }
.selbar .reagg { color: var(--accent); font-weight: 600; }
.selbar button { padding: 5px 12px; font-size: 12px; font-weight: 600; color: #fff; background: var(--accent); border: none; border-radius: 8px; cursor: pointer; white-space: nowrap; }
.banner { margin: 10px 32px 0; font-size: 14px; color: var(--text-2); }
.banner.err { color: #d70015; }
.hero { margin: 24px 32px; max-width: 620px; background: var(--surface); border: 1px solid var(--border); border-radius: 16px; box-shadow: var(--shadow-sm); padding: 26px 28px; }
.hero h2 { margin: 0 0 8px; font-size: 19px; font-weight: 600; letter-spacing: -0.01em; }
.hero > p { margin: 0 0 14px; font-size: 13.5px; color: var(--text-2); line-height: 1.6; }
.hero b { color: var(--text); font-weight: 600; }
.hero ol { margin: 0 0 18px; padding-left: 20px; display: flex; flex-direction: column; gap: 6px; font-size: 13.5px; color: var(--text); }
.hero-btn { padding: 11px 20px; color: #fff; background: linear-gradient(135deg, var(--accent-2), var(--accent)); border: none; border-radius: 12px; font-size: 14px; font-weight: 600; cursor: pointer; box-shadow: 0 6px 16px rgba(79,70,229,.28); }
.hero-sub { margin: 12px 0 0; font-size: 12px; color: var(--text-2); }
.kpis { display: flex; gap: 12px; padding: 14px 32px 0; flex-wrap: wrap; }
.kpi { background: var(--surface); border: 1px solid var(--border); border-radius: 14px; box-shadow: var(--shadow-sm); padding: 10px 16px; min-width: 96px; display: flex; flex-direction: column; gap: 2px; cursor: help; }
/* 상태 레일은 Cpk 카드에만(값이 있을 때) — 정보 카드엔 표시 안 함 */
.kpi.st-good { border-left: 3px solid #16a34a; }
.kpi.st-warn { border-left: 3px solid #d97706; }
.kpi.st-bad { border-left: 3px solid #dc2626; }
.kv { font-size: 20px; font-weight: 700; letter-spacing: -0.02em; }
.kv.good { color: #166534; } .kv.warn { color: #854d0e; } .kv.bad { color: #991b1b; } .kv.warnum { color: #854d0e; } .kv.muted { color: #6b7280; }
.kv .shift { font-size: 11px; font-weight: 600; margin-left: 4px; opacity: .85; }
.kl { font-size: 11px; color: var(--text-2); text-transform: uppercase; letter-spacing: .03em; }
.drivers-area { padding: 14px 32px 0; display: flex; flex-direction: column; gap: 8px; }
.drivers-area .pane-title small { text-transform: none; letter-spacing: 0; font-weight: 500; color: var(--text-2); margin-left: 6px; }
.dgrid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }
.dcard { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; box-shadow: var(--shadow-sm); padding: 12px 14px; }
.dtitle { font-size: 13px; font-weight: 600; margin-bottom: 8px; }
.drow { display: grid; grid-template-columns: 110px 1fr 44px; align-items: center; gap: 8px; margin-bottom: 5px; cursor: help; }
.dname { font-size: 11px; color: var(--text-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.dbar { height: 9px; background: var(--surface-2); border-radius: 999px; overflow: hidden; }
.dfill { height: 100%; background: var(--accent); border-radius: 999px; }
.dfill.neg { background: #e8833a; }
.dval { font-size: 11px; font-weight: 700; color: var(--accent); text-align: right; }
.dval.neg { color: #b45309; }
.dnone { font-size: 11px; color: var(--text-2); margin: 4px 0 0; }
.capgrid2 { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 5px 18px; }
.caprow2 { display: grid; grid-template-columns: minmax(96px, 1.4fr) 62px 62px auto; align-items: center; gap: 8px; cursor: help; font-size: 12px; }
.cpp { color: var(--text-2); white-space: nowrap; }
.cpp b { font-weight: 700; color: var(--text); }
.cpp b.good { color: #166534; } .cpp b.warn { color: #854d0e; } .cpp b.bad { color: #991b1b; }
.dxtags { display: inline-flex; gap: 4px; flex-wrap: wrap; align-items: center; }
.capset-btn { float: right; font-size: 10px; font-weight: 600; color: var(--text-2); background: #fff; border: 1px solid var(--border); border-radius: 999px; padding: 1px 9px; cursor: pointer; text-transform: none; letter-spacing: 0; }
.capset-btn.on { color: var(--accent); border-color: var(--accent); background: var(--accent-weak); }
.capset { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 14px; padding: 8px 12px; margin: 2px 0 4px; background: var(--surface-2); border: 1px solid var(--border); border-radius: 10px; font-size: 11px; }
.capset label { display: inline-flex; align-items: center; gap: 4px; color: var(--text-2); font-weight: 600; }
.capset input { width: 52px; padding: 3px 6px; font-size: 11px; border: 1px solid var(--border); border-radius: 6px; background: #fff; outline: none; }
.capset input:focus { border-color: var(--accent); box-shadow: var(--ring); }
.capset select { padding: 3px 6px; font-size: 11px; border: 1px solid var(--border); border-radius: 6px; background: #fff; outline: none; font-weight: 600; color: var(--text); }
.capset select:focus { border-color: var(--accent); box-shadow: var(--ring); }
.capset-sg { color: var(--accent); }
.capset-div { color: var(--border); }
.capset-reset { font-size: 11px; font-weight: 600; color: var(--accent); background: #fff; border: 1px solid var(--accent); border-radius: 6px; padding: 3px 9px; cursor: pointer; }
.capset-hint { color: var(--text-2); font-weight: 500; }
.cpkv { font-size: 11px; font-weight: 700; text-align: right; }
.cpkv.good { color: #166534; } .cpkv.warn { color: #854d0e; } .cpkv.bad { color: #991b1b; }
.ctab { width: 100%; border-collapse: collapse; font-size: 12px; }
.ctab td { padding: 4px 6px; border-bottom: 1px solid var(--border); white-space: nowrap; }
.ctab tr:last-child td { border-bottom: none; }
.ctab tr.best td { background: var(--accent-weak); }
.ctab tr.best .ccfv { font-weight: 700; color: var(--accent); }
.crank { color: var(--text-2); width: 16px; }
.ccfv { width: 40%; overflow: hidden; text-overflow: ellipsis; }
.cnum { font-weight: 700; text-align: right; }
.cn { color: var(--text-2); font-size: 10px; text-align: right; }
.rows { display: flex; flex-direction: column; gap: 16px; padding: 16px 32px; }
.table-area { padding: 4px 32px 36px; display: flex; flex-direction: column; gap: 10px; }
.ix-area { padding: 0 32px 40px; }
.pane-title { margin: 0; font-size: 13px; font-weight: 600; color: var(--text-2); text-transform: uppercase; letter-spacing: .04em; }
</style>
