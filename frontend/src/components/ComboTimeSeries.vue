<script setup>
// 시계열 (M1): 위=target, 아래=feature.
//  - 분리(단일): scatter + 이동평균 + 관리한계(±3σ) / feature spec.
//  - 겹쳐보기(groups): 분할값별 옅은 scatter + 굵은 이동평균을 색으로 겹쳐 비교(관리한계 생략, spec 공유).
import { computed } from 'vue'
import VChart from 'vue-echarts'
import '../echarts.js'
import { PALETTE as C } from '../palette.js'

const props = defineProps({
  target: { type: Object, default: null },   // 단일: { observed_points, control_limits, ... }
  feature: { type: Object, default: null },  // 단일: { points, control_limits, ... }
  estimate: { type: Object, default: null }, // 단일: { points:[[iso,val]], fit_summary }
  showEstimate: { type: Boolean, default: false },
  groups: { type: Array, default: null },    // [{ label, color, target, feature }] — 있으면 겹쳐보기
  selection: { type: Array, default: null }, // [startISO, endISO] linked-brushing 선택 구간(밴드로 표시)
  yTarget: { type: String, default: '' },
  xFeature: { type: String, default: '' },
  spec: { type: Object, default: () => ({ lower: null, upper: null }) },
  dcSpec: { type: Object, default: () => ({ lower: null, upper: null }) },
  sampled: { type: Boolean, default: false },
})
const emit = defineEmits(['brush'])

// 시계열 x축 기간 brush → 선택 구간(ISO) 또는 해제(null) 방출
function onBrushEnd(params) {
  const areas = params?.areas || []
  if (!areas.length) { emit('brush', null); return }
  const a = areas[0]
  const cr = a.coordRange || (a.coordRanges && a.coordRanges[0])
  if (!cr || cr.length !== 2) return
  emit('brush', [new Date(cr[0]).toISOString(), new Date(cr[1]).toISOString()])
}

// 중심 이동평균 — 슬라이딩 합으로 O(n) (이전 O(n·win))
function movingAverage(points) {
  const n = points.length
  if (!n) return []
  const half = Math.floor(Math.max(5, Math.round(n / 15)) / 2)
  const out = new Array(n)
  let sum = 0, lo = 0, hi = -1
  for (let i = 0; i < n; i++) {
    const want = Math.min(n - 1, i + half)
    while (hi < want) { hi++; sum += points[hi][1] }
    const newLo = Math.max(0, i - half)
    while (lo < newLo) { sum -= points[lo][1]; lo++ }
    out[i] = [points[i][0], +(sum / (hi - lo + 1)).toFixed(4)]
  }
  return out
}
const tPts = (t) => (t?.observed_points || []).map((p) => [p.time, p.value])
const fPts = (f) => f?.points || []
// 이동평균은 target/feature에만 의존 → 별도 computed로 캐시(spec 입력·추정 토글 시 재계산 방지)
const tMaSingle = computed(() => movingAverage(tPts(props.target)))
const fMaSingle = computed(() => movingAverage(fPts(props.feature)))
const groupMas = computed(() => (props.groups || []).map((g) => ({ t: movingAverage(tPts(g.target)), f: movingAverage(fPts(g.feature)) })))
// 선택 구간 밴드 (linked brushing의 시각적 앵커 — brush가 사라져도 남음)
const selBand = () => props.selection ? { silent: true, itemStyle: { color: 'rgba(79,70,229,0.07)' }, data: [[{ xAxis: props.selection[0] }, { xAxis: props.selection[1] }]] } : undefined

// feature spec(user/DC) 수평선 — 라벨 흰 배경 칩으로 축 눈금과 겹쳐도 가독
const hl = (v, color, label) => ({ yAxis: v, lineStyle: { color, type: 'dashed', width: 2 }, label: { formatter: label, fontSize: 9, color, position: 'start', backgroundColor: '#fff', padding: [1, 3], borderRadius: 2 } })
function featLines() {
  const out = []
  if (props.spec.lower != null) out.push(hl(props.spec.lower, C.specUser, 'USL'))
  if (props.spec.upper != null) out.push(hl(props.spec.upper, C.specUser, 'USU'))
  if (props.dcSpec.lower != null) out.push(hl(props.dcSpec.lower, C.specDc, 'DC-L'))
  if (props.dcSpec.upper != null) out.push(hl(props.dcSpec.upper, C.specDc, 'DC-U'))
  return out
}

const baseLayout = {
  axisPointer: { link: [{ xAxisIndex: 'all' }] },
  tooltip: { trigger: 'axis' },
  toolbox: { show: true, right: 6, top: -4, itemSize: 13,
    feature: { brush: { type: ['lineX', 'clear'], title: { lineX: '기간 선택', clear: '선택 해제' } } } },
  brush: { xAxisIndex: [0, 1], brushType: 'lineX', brushMode: 'single', removeOnClick: true,
    throttleType: 'debounce', throttleDelay: 350,
    brushStyle: { color: 'rgba(79,70,229,0.10)', borderColor: 'rgba(79,70,229,0.45)' } },
  grid: [{ left: 58, right: 38, top: 42, height: '30%' }, { left: 58, right: 38, top: '56%', height: '30%' }],
  dataZoom: [
    { type: 'inside', xAxisIndex: [0, 1] },
    { type: 'slider', yAxisIndex: 0, right: 6, top: 42, height: '30%', width: 22, brushSelect: false, handleSize: 24, moveHandleSize: 9, showDetail: false },
    { type: 'slider', yAxisIndex: 1, right: 6, top: '56%', height: '30%', width: 22, brushSelect: false, handleSize: 24, moveHandleSize: 9, showDetail: false },
    { type: 'inside', yAxisIndex: 0 }, { type: 'inside', yAxisIndex: 1 },
    { type: 'slider', xAxisIndex: [0, 1], left: 58, right: 38, bottom: 6, height: 16, brushSelect: false, handleSize: 24, moveHandleSize: 9, showDetail: false },
  ],
}
function axes() {
  return {
    xAxis: [{ type: 'time', gridIndex: 0, axisLabel: { show: false } }, { type: 'time', gridIndex: 1 }],
    yAxis: [
      { type: 'value', gridIndex: 0, name: props.yTarget, scale: true, nameTextStyle: { fontSize: 10 } },
      { type: 'value', gridIndex: 1, name: props.xFeature, scale: true, nameTextStyle: { fontSize: 10 } },
    ],
  }
}

const isMulti = computed(() => Array.isArray(props.groups) && props.groups.length > 0)
const hasData = computed(() => isMulti.value
  ? props.groups.some((g) => tPts(g.target).length || fPts(g.feature).length)
  : !!(props.target || props.feature))

const estInfo = computed(() => {
  if (!props.showEstimate || isMulti.value || !props.estimate?.fit_summary || !props.estimate.points?.length) return null
  const f = props.estimate.fit_summary
  return { r2: f.r2, n: f.n, count: props.estimate.points.length, weak: f.r2 != null && f.r2 < 0.2 }
})

function singleOption() {
  const tp = tPts(props.target)
  const fp = fPts(props.feature)
  const estPts = (props.showEstimate && props.estimate?.points?.length) ? props.estimate.points : []
  const tcl = props.target?.control_limits
  const clMark = (cl, color) => {
    if (!cl) return []
    const lbl = (t) => ({ formatter: t, fontSize: 9, color, position: 'start', backgroundColor: '#fff', padding: [1, 3], borderRadius: 2 })
    return [
      { yAxis: cl.ucl, lineStyle: { color, type: 'dashed', width: 1, opacity: 0.7 }, label: lbl('UCL') },
      { yAxis: cl.lcl, lineStyle: { color, type: 'dashed', width: 1, opacity: 0.7 }, label: lbl('LCL') },
    ]
  }
  return {
    ...baseLayout, ...axes(),
    legend: { top: 2, left: 'center', itemWidth: 14, itemHeight: 8, itemGap: 12, textStyle: { fontSize: 10 },
      data: ['target', 'target 추세', ...(estPts.length ? ['추정 y'] : []), 'feature', 'feature 추세'] },
    series: [
      { name: 'target', type: 'scatter', xAxisIndex: 0, yAxisIndex: 0, data: tp, symbolSize: 4,
        itemStyle: { color: C.tsTarget }, markLine: { symbol: 'none', data: clMark(tcl, C.faint) }, markArea: selBand() },
      { name: 'target 추세', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: tMaSingle.value,
        smooth: true, showSymbol: false, z: 5, lineStyle: { color: C.tsTargetMa, width: 3 }, itemStyle: { color: C.tsTargetMa } },
      { name: '추정 y', type: 'scatter', xAxisIndex: 0, yAxisIndex: 0, data: estPts, symbol: 'diamond', symbolSize: 7, z: 4,
        itemStyle: { color: 'transparent', borderColor: C.estimate, borderWidth: 1.5 } },
      { name: 'feature', type: 'scatter', xAxisIndex: 1, yAxisIndex: 1, data: fp, symbolSize: 4,
        itemStyle: { color: C.tsFeature }, markLine: { symbol: 'none', data: featLines() }, markArea: selBand() },
      { name: 'feature 추세', type: 'line', xAxisIndex: 1, yAxisIndex: 1, data: fMaSingle.value,
        smooth: true, showSymbol: false, z: 5, lineStyle: { color: C.tsFeatureMa, width: 3 }, itemStyle: { color: C.tsFeatureMa } },
    ],
  }
}

function multiOption() {
  const groups = props.groups
  const series = []
  groups.forEach((g, gi) => {
    const tp = tPts(g.target)
    const fp = fPts(g.feature)
    const ma = groupMas.value[gi] || { t: [], f: [] }  // 캐시된 이동평균(집계 무관 재계산 방지)
    // 같은 분할값의 4개 series는 동일 name → 범례에서 한 번에 토글. 선택 밴드는 첫 그룹에만
    series.push(
      { name: g.label, type: 'scatter', xAxisIndex: 0, yAxisIndex: 0, data: tp, symbolSize: 3, itemStyle: { color: g.color, opacity: 0.32 },
        ...(gi === 0 ? { markArea: selBand() } : {}) },
      { name: g.label, type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: ma.t, smooth: true, showSymbol: false, z: 5, lineStyle: { color: g.color, width: 2.5 } },
      { name: g.label, type: 'scatter', xAxisIndex: 1, yAxisIndex: 1, data: fp, symbolSize: 3, itemStyle: { color: g.color, opacity: 0.32 },
        ...(gi === 0 ? { markLine: { symbol: 'none', data: featLines() }, markArea: selBand() } : {}) },
      { name: g.label, type: 'line', xAxisIndex: 1, yAxisIndex: 1, data: ma.f, smooth: true, showSymbol: false, z: 5, lineStyle: { color: g.color, width: 2.5 } },
    )
  })
  return {
    ...baseLayout, ...axes(),
    legend: { top: 2, left: 'center', itemWidth: 14, itemHeight: 8, textStyle: { fontSize: 10 }, data: groups.map((g) => g.label) },
    series,
  }
}

const option = computed(() => (isMulti.value ? multiOption() : singleOption()))
</script>

<template>
  <div class="ts">
    <span v-if="sampled" class="ds">다운샘플 표시</span>
    <span v-if="estInfo" class="est" :class="{ weak: estInfo.weak }"
      :title="`추정 y~x 회귀 · R²=${estInfo.r2 ?? '-'} · 적합 n=${estInfo.n} · 추정 ${estInfo.count}점` + (estInfo.weak ? ' · 적합도 낮음(참고용)' : '')">
      추정 R² {{ estInfo.r2 == null ? '-' : estInfo.r2.toFixed(2) }}{{ estInfo.weak ? ' ⚠' : '' }}
    </span>
    <VChart v-if="hasData" class="chart" :option="option" autoresize @brushend="onBrushEnd" />
    <p v-else class="empty">시계열 데이터 없음</p>
  </div>
</template>

<style scoped>
.ts { position: relative; height: 100%; }
.ds { position: absolute; top: 2px; left: 56px; z-index: 2; font-size: 10px; font-weight: 600; color: #92400e; background: #fde68a; padding: 1px 7px; border-radius: 999px; }
.est { position: absolute; top: 2px; left: 56px; z-index: 2; font-size: 10px; font-weight: 600; color: #6b21a8; background: #f3e8ff; padding: 1px 7px; border-radius: 999px; }
.est.weak { color: #92400e; background: #fde68a; }
.chart { height: 400px; width: 100%; }
.empty { height: 400px; display: flex; align-items: center; justify-content: center; color: #aaa; font-size: 13px; }
</style>
