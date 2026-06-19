<script setup>
// 교호작용 분석 패널: 차트 작성에 쓰인 X features/Y target 중 2개를 x/y축으로,
// value_field를 집계(average/median)해 scatter + heatmap + rank table로 분석.
import { ref, computed, watch } from 'vue'
import InteractionScatter from './InteractionScatter.vue'
import InteractionHeatmap from './InteractionHeatmap.vue'
import { fetchInteraction } from '../api/client.js'

const props = defineProps({
  cond: { type: Object, default: null },         // 마지막 차트 작성 조건(lastCond)
  labels: { type: Object, default: () => ({}) }, // x_feature key → 표시명
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
const xRange = ref(['', ''])
const yRange = ref(['', ''])

const result = ref(null)
const loading = ref(false)
const error = ref('')

function validRange(r) {
  const a = parseFloat(r[0]), b = parseFloat(r[1])
  return (isFinite(a) && isFinite(b) && b > a) ? [a, b] : null
}

async function run() {
  const c = props.cond
  if (!c || !xFeat.value || !yFeat.value || !valueField.value) return
  loading.value = true; error.value = ''
  try {
    result.value = await fetchInteraction({
      line_id: c.line_id, product: c.product, category: c.category, eds_step: c.eds_step,
      fab_step: c.fab_step, date_range: c.date_range, target_date_range: c.target_date_range,
      x_feature: xFeat.value, y_feature: yFeat.value, value_field: valueField.value,
      aggregation: aggregation.value, x_bins: xBins.value, y_bins: yBins.value,
      x_range: validRange(xRange.value), y_range: validRange(yRange.value),
      y_target_groups: c.y_target_groups || [],
    })
  } catch (e) {
    error.value = e.message || '교호작용 분석 실패'
  } finally {
    loading.value = false
  }
}

// 새 차트 작성(cond 변경) → 기본 축/값 재설정 후 1회 실행
watch(() => props.cond, (c) => {
  if (!c) { result.value = null; return }
  xFeat.value = c.x_features?.[0] || c.y_targets?.[0] || ''
  yFeat.value = c.x_features?.[1] || c.y_targets?.[0] || c.x_features?.[0] || ''
  valueField.value = c.y_targets?.[0] || '__count__'
  xRange.value = ['', '']; yRange.value = ['', '']
  run()
}, { immediate: true })

// 컨트롤 변경 → 즉시 반영
watch([xFeat, yFeat, valueField, aggregation, xBins, yBins], run)
</script>

<template>
  <section class="ix">
    <div class="head">
      <h3 class="pane-title">교호작용 분석</h3>
      <span v-if="result" class="ntot">n = {{ result.n_total }}<span v-if="result.sampled"> · scatter 다운샘플</span></span>
    </div>

    <div class="controls">
      <label class="f">X축
        <select v-model="xFeat"><option v-for="o in featOptions" :key="'x' + o.key" :value="o.key">{{ o.label }} · {{ o.grp }}</option></select>
      </label>
      <label class="f">Y축
        <select v-model="yFeat"><option v-for="o in featOptions" :key="'y' + o.key" :value="o.key">{{ o.label }} · {{ o.grp }}</option></select>
      </label>
      <label class="f">Value
        <select v-model="valueField"><option v-for="o in valueOptions" :key="'v' + o.key" :value="o.key">{{ o.label }}</option></select>
      </label>
      <div class="f">집계
        <div class="seg">
          <button :class="{ on: aggregation === 'average' }" @click="aggregation = 'average'">평균</button>
          <button :class="{ on: aggregation === 'median' }" @click="aggregation = 'median'">중앙값</button>
        </div>
      </div>
      <label class="f sm">X bins<input type="number" min="2" max="40" v-model.number="xBins" /></label>
      <label class="f sm">Y bins<input type="number" min="2" max="40" v-model.number="yBins" /></label>
      <div class="f rng">X range
        <span><input type="number" v-model="xRange[0]" placeholder="min" @change="run" /><input type="number" v-model="xRange[1]" placeholder="max" @change="run" /></span>
      </div>
      <div class="f rng">Y range
        <span><input type="number" v-model="yRange[0]" placeholder="min" @change="run" /><input type="number" v-model="yRange[1]" placeholder="max" @change="run" /></span>
      </div>
    </div>

    <p v-if="error" class="banner err">⚠ {{ error }}</p>
    <p v-else-if="loading" class="banner">분석 중…</p>
    <p v-else-if="result && !result.n_total" class="banner">선택한 조합에 데이터가 없습니다.</p>

    <div v-if="result && result.n_total" class="charts">
      <div class="cell">
        <div class="cap">Scatter <small>{{ labelOf(yFeat) }} vs {{ labelOf(xFeat) }}</small></div>
        <InteractionScatter :points="result.scatter_points" :x-label="labelOf(xFeat)" :y-label="labelOf(yFeat)"
          :value-label="labelOf(valueField)" :sampled="result.sampled" />
      </div>
      <div class="cell">
        <div class="cap">Heatmap <small>{{ labelOf(valueField) }} ({{ aggregation === 'median' ? '중앙값' : '평균' }})</small></div>
        <InteractionHeatmap :cells="result.heatmap_cells" :x-bins="xBins" :y-bins="yBins"
          :x-label="labelOf(xFeat)" :y-label="labelOf(yFeat)" :value-label="labelOf(valueField)" :min-count="minN" />
      </div>
    </div>

    <div v-if="result && result.rank_rows.length" class="rank">
      <div class="cap">순위 ({{ labelOf(valueField) }} {{ aggregation === 'median' ? '중앙값' : '평균' }} 내림차순)</div>
      <div class="rank-wrap">
        <table>
          <thead><tr><th>#</th><th>{{ labelOf(xFeat) }}</th><th>{{ labelOf(yFeat) }}</th><th>집계값</th><th>n</th></tr></thead>
          <tbody>
            <tr v-for="r in result.rank_rows" :key="r.rank" :class="{ thin: r.count < minN }">
              <td>{{ r.rank }}</td><td>{{ r.x_bin_label }}</td><td>{{ r.y_bin_label }}</td>
              <td class="num">{{ r.aggregation }}</td><td>{{ r.count }}<span v-if="r.count < minN" class="tn">thin</span></td>
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
.rng span { display: flex; gap: 4px; }
.rng input { width: 64px; }
.seg { display: flex; border: 1px solid var(--border); border-radius: 8px; overflow: hidden; background: #fff; }
.seg button { padding: 6px 12px; font-size: 12px; font-weight: 600; border: none; background: #fff; color: var(--text-2); cursor: pointer; }
.seg button + button { border-left: 1px solid var(--border); }
.seg button.on { background: var(--accent-weak); color: var(--accent); }
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
.tn { font-size: 9px; font-weight: 700; color: #92400e; background: #fde68a; padding: 0 5px; border-radius: 999px; margin-left: 6px; }
.banner { margin: 4px 0; font-size: 13px; color: var(--text-2); }
.banner.err { color: #d70015; }
@media (max-width: 1100px) { .charts { grid-template-columns: 1fr; } }
</style>
