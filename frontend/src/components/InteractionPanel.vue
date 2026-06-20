<script setup>
// 교호작용 분석: 차트 작성에 쓰인 X features/Y target 중 2개를 x/y축으로,
// value_field를 집계해 scatter + heatmap + rank로 분석.
// scatter 점만 서버에서 받고, binning/집계/제외(outlier)는 프론트에서 즉시 계산(서버 재요청 없이 인터랙션).
import { ref, shallowRef, computed, watch } from 'vue'
import InteractionScatter from './InteractionScatter.vue'
import InteractionHeatmap from './InteractionHeatmap.vue'
import { fetchInteraction } from '../api/client.js'

const props = defineProps({
  cond: { type: Object, default: null },
  labels: { type: Object, default: () => ({}) },
  minN: { type: Number, default: 10 },
})

function labelOf(k) { return k === '__count__' ? 'wafer 수' : (props.labels[k] || k) }
const featOptions = computed(() => {
  const c = props.cond; if (!c) return []
  return [
    ...(c.x_features || []).map((k) => ({ key: k, label: labelOf(k), grp: 'X feature' })),
    ...(c.y_targets || []).map((k) => ({ key: k, label: k, grp: 'Y target' })),
  ]
})
const valueOptions = computed(() => [...featOptions.value, { key: '__count__', label: 'wafer 수', grp: '기타' }])

const xFeat = ref('')
const yFeat = ref('')
const valueField = ref('')
const aggregation = ref('average')
const xBins = ref(10)
const yBins = ref(10)
const excluded = ref(new Set())  // 제외된 점 index

const result = shallowRef(null)  // 서버 점 배열 → 깊은 reactive 불필요
const loading = ref(false)
const error = ref('')
let lastSig = ''

async function run() {
  const c = props.cond
  if (!c || !xFeat.value || !yFeat.value || !valueField.value) return
  const sig = [c.line_id, c.product, c.category, c.eds_step, c.fab_step,
    c.date_range?.start_date, c.date_range?.end_date, c.target_date_range?.start_date, c.target_date_range?.end_date,
    xFeat.value, yFeat.value, valueField.value].join('|')
  if (sig === lastSig) return  // 중복요청 방지(cond·축 동시 변경 등)
  lastSig = sig
  loading.value = true; error.value = ''
  try {
    result.value = await fetchInteraction({
      line_id: c.line_id, product: c.product, category: c.category, eds_step: c.eds_step,
      fab_step: c.fab_step, date_range: c.date_range, target_date_range: c.target_date_range,
      x_feature: xFeat.value, y_feature: yFeat.value, value_field: valueField.value,
      y_target_groups: c.y_target_groups || [],
    })
    excluded.value = new Set()  // 새 데이터 → 제외 초기화
  } catch (e) {
    error.value = e.message || '교호작용 분석 실패'
  } finally {
    loading.value = false
  }
}

watch(() => props.cond, (c) => {
  if (!c) { result.value = null; return }
  xFeat.value = c.x_features?.[0] || c.y_targets?.[0] || ''
  yFeat.value = c.x_features?.[1] || c.y_targets?.[0] || c.x_features?.[0] || ''
  valueField.value = c.y_targets?.[0] || '__count__'
  run()
}, { immediate: true })
watch([xFeat, yFeat, valueField], run)

// ---- 점 + 제외 ----
const points = computed(() => (result.value?.scatter_points || []).map((p, i) => ({ ...p, i })))
const activePoints = computed(() => points.value.filter((p) => !excluded.value.has(p.i)))
const excludedCount = computed(() => excluded.value.size)
function onToggleExclude(i) {
  const s = new Set(excluded.value)
  s.has(i) ? s.delete(i) : s.add(i)
  excluded.value = s
}
function onExcludeRegion(idxs) {
  const s = new Set(excluded.value)
  idxs.forEach((i) => s.add(i))
  excluded.value = s
}
function clearExcluded() { excluded.value = new Set() }

// ---- heatmap + rank (프론트 계산, 제외 반영) ----
function median(a) { const s = [...a].sort((x, y) => x - y); const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2 }
function edges(lo, hi, n) { if (hi <= lo) hi = lo + 1e-9; const out = []; for (let i = 0; i <= n; i++) out.push(lo + (hi - lo) * i / n); return out }
function binOf(v, lo, hi, n) { if (v < lo || v > hi) return -1; return Math.max(0, Math.min(n - 1, Math.floor((v - lo) / ((hi - lo) || 1e-9) * n))) }
const fmt = (v) => Number(v.toPrecision(4))

const heat = computed(() => {
  const pts = activePoints.value
  if (!pts.length) return { cells: [], rank: [] }
  // 단일 패스 min/max (대량 점에서 Math.min(...arr) 스프레드 스택 위험 회피)
  let xlo = Infinity, xhi = -Infinity, ylo = Infinity, yhi = -Infinity
  for (const p of pts) {
    if (p.x < xlo) xlo = p.x; if (p.x > xhi) xhi = p.x
    if (p.y < ylo) ylo = p.y; if (p.y > yhi) yhi = p.y
  }
  const xE = edges(xlo, xhi, xBins.value), yE = edges(ylo, yhi, yBins.value)
  const isCount = pts[0].value == null
  const buckets = new Map()
  for (const p of pts) {
    const xi = binOf(p.x, xlo, xhi, xBins.value), yi = binOf(p.y, ylo, yhi, yBins.value)
    if (xi < 0 || yi < 0) continue
    const k = xi + ',' + yi
    if (!buckets.has(k)) buckets.set(k, [])
    buckets.get(k).push(isCount ? 1 : p.value)
  }
  const cells = []
  for (const [k, vs] of buckets) {
    const [xi, yi] = k.split(',').map(Number)
    const v = isCount ? vs.length : (aggregation.value === 'median' ? median(vs) : vs.reduce((a, b) => a + b, 0) / vs.length)
    cells.push({ x_bin: xi, y_bin: yi, x_bin_label: `${fmt(xE[xi])} – ${fmt(xE[xi + 1])}`,
      y_bin_label: `${fmt(yE[yi])} – ${fmt(yE[yi + 1])}`, value: Math.round(v * 1e4) / 1e4, count: vs.length })
  }
  const rank = [...cells].sort((a, b) => b.value - a.value).slice(0, 50)
    .map((c, i) => ({ rank: i + 1, x_bin_label: c.x_bin_label, y_bin_label: c.y_bin_label, aggregation: c.value, count: c.count }))
  return { cells, rank }
})
</script>

<template>
  <section class="ix">
    <div class="head">
      <h3 class="pane-title">교호작용 분석</h3>
      <span v-if="result" class="ntot">n = {{ activePoints.length }}<span v-if="result.sampled"> · 다운샘플</span></span>
    </div>

    <div class="controls">
      <label class="f">X축<select v-model="xFeat"><option v-for="o in featOptions" :key="'x' + o.key" :value="o.key">{{ o.label }} · {{ o.grp }}</option></select></label>
      <label class="f">Y축<select v-model="yFeat"><option v-for="o in featOptions" :key="'y' + o.key" :value="o.key">{{ o.label }} · {{ o.grp }}</option></select></label>
      <label class="f">Value<select v-model="valueField"><option v-for="o in valueOptions" :key="'v' + o.key" :value="o.key">{{ o.label }}</option></select></label>
      <div class="f">집계
        <div class="seg">
          <button :class="{ on: aggregation === 'average' }" @click="aggregation = 'average'">평균</button>
          <button :class="{ on: aggregation === 'median' }" @click="aggregation = 'median'">중앙값</button>
        </div>
      </div>
      <label class="f sm">X bins<input type="number" min="2" max="40" v-model.number="xBins" /></label>
      <label class="f sm">Y bins<input type="number" min="2" max="40" v-model.number="yBins" /></label>
      <div v-if="excludedCount" class="excl">제외 {{ excludedCount }}개<button @click="clearExcluded">초기화</button></div>
      <span v-else-if="points.length" class="exclhint" title="scatter에서 점을 클릭하거나 영역을 드래그(우상단 brush)하면 outlier를 제외하고 heatmap·순위가 다시 계산됩니다">💡 점 클릭·영역 드래그 = outlier 제외</span>
    </div>

    <p v-if="error" class="banner err">⚠ {{ error }}</p>
    <p v-else-if="loading" class="banner">분석 중…</p>
    <p v-else-if="result && !points.length" class="banner">선택한 조합에 데이터가 없습니다.</p>

    <div v-if="points.length" class="charts">
      <div class="cell">
        <div class="cap">Scatter <small>{{ labelOf(yFeat) }} vs {{ labelOf(xFeat) }} · 점 클릭/영역 brush로 outlier 제외</small></div>
        <InteractionScatter :points="points" :excluded="excluded" :x-label="labelOf(xFeat)" :y-label="labelOf(yFeat)"
          :value-label="labelOf(valueField)" :sampled="result.sampled"
          @toggle-exclude="onToggleExclude" @exclude-region="onExcludeRegion" />
      </div>
      <div class="cell">
        <div class="cap">Heatmap <small>{{ labelOf(valueField) }} ({{ aggregation === 'median' ? '중앙값' : '평균' }}){{ excludedCount ? ' · 제외 반영' : '' }}</small></div>
        <InteractionHeatmap :cells="heat.cells" :x-bins="xBins" :y-bins="yBins"
          :x-label="labelOf(xFeat)" :y-label="labelOf(yFeat)" :value-label="labelOf(valueField)" :min-count="minN" />
      </div>
    </div>

    <div v-if="heat.rank.length" class="rank">
      <div class="cap">순위 ({{ labelOf(valueField) }} {{ aggregation === 'median' ? '중앙값' : '평균' }} 내림차순)</div>
      <div class="rank-wrap">
        <table>
          <thead><tr><th>#</th><th>{{ labelOf(xFeat) }}</th><th>{{ labelOf(yFeat) }}</th><th>집계값</th><th>n</th></tr></thead>
          <tbody>
            <tr v-for="r in heat.rank" :key="r.rank" :class="{ thin: r.count < minN }" :title="r.count < minN ? `표본 ${r.count} < ${minN} — 신뢰도 낮음(thin)` : ''">
              <td>{{ r.rank }}</td><td>{{ r.x_bin_label }}</td><td>{{ r.y_bin_label }}</td>
              <td class="num">{{ r.aggregation }}</td><td>{{ r.count }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>

<style scoped>
.ix { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 18px 20px; box-shadow: var(--shadow-sm); display: flex; flex-direction: column; gap: 12px; }
.head { display: flex; align-items: baseline; justify-content: space-between; }
.pane-title { margin: 0; font-size: 13px; font-weight: 600; color: var(--text-2); text-transform: uppercase; letter-spacing: .04em; }
.ntot { font-size: 12px; color: var(--text-2); }
.controls { display: flex; flex-wrap: wrap; gap: 10px 14px; align-items: flex-end; padding: 4px 0; }
.f { display: flex; flex-direction: column; gap: 4px; font-size: 11px; color: var(--text-2); font-weight: 600; }
.f select, .f input { padding: 6px 8px; font-size: 12px; border-radius: 8px; border: 1px solid var(--border); background: #fff; color: var(--text); outline: none; }
.f select:focus, .f input:focus { border-color: var(--accent); box-shadow: var(--ring); }
.f.sm input { width: 58px; }
.seg { display: flex; border: 1px solid var(--border); border-radius: 8px; overflow: hidden; background: #fff; }
.seg button { padding: 6px 12px; font-size: 12px; font-weight: 600; border: none; background: #fff; color: var(--text-2); cursor: pointer; }
.seg button + button { border-left: 1px solid var(--border); }
.seg button.on { background: var(--accent-weak); color: var(--accent); }
.excl { display: flex; align-items: center; gap: 8px; font-size: 12px; font-weight: 600; color: #9a3412; background: #ffedd5; border: 1px solid #fdba74; border-radius: 8px; padding: 5px 10px; }
.excl button { font-size: 11px; font-weight: 600; color: #fff; background: #ea580c; border: none; border-radius: 6px; padding: 3px 9px; cursor: pointer; }
.exclhint { align-self: center; font-size: 11px; font-weight: 600; color: var(--accent); background: var(--accent-weak); border-radius: 8px; padding: 5px 10px; cursor: help; }
.charts { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
.cell { min-width: 0; }
.cap { font-size: 11px; color: var(--text-2); margin-bottom: 4px; text-transform: uppercase; letter-spacing: .04em; font-weight: 600; }
.cap small { text-transform: none; letter-spacing: 0; color: var(--text); font-weight: 500; margin-left: 4px; }
.rank-wrap { max-height: 240px; overflow: auto; border: 1px solid var(--border); border-radius: 10px; }
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th, td { padding: 7px 12px; text-align: left; border-bottom: 1px solid var(--border); white-space: nowrap; }
th { background: var(--surface-2); color: var(--text-2); font-weight: 600; position: sticky; top: 0; font-size: 11px; }
td.num { font-weight: 700; }
tbody tr:hover { background: #f5f5f7; }
tr.thin { color: var(--text-2); }
tr.thin td:first-child { box-shadow: inset 3px 0 0 #fbbf24; }
.banner { margin: 4px 0; font-size: 13px; color: var(--text-2); }
.banner.err { color: #d70015; }
@media (max-width: 1100px) { .charts { grid-template-columns: 1fr; } }
</style>
