<script setup>
// Window 차트 (M1).
//  - 분리(단일): bar=count, line=y avg. 표본 적은 bin은 흐리게.
//  - 겹쳐보기(groups): 분할값별 y avg 추세선만 겹쳐 표시(막대 생략, 비교 우선).
//  - user spec(점선 vermillion) / DC spec(점선 black) 수직선 + 라벨, 범례·tooltip.
import { computed } from 'vue'
import VChart from 'vue-echarts'
import '../echarts.js'
import { PALETTE as C } from '../palette.js'

const props = defineProps({
  bins: { type: Array, default: () => [] },
  groups: { type: Array, default: null },  // [{ label, color, bins }] — 있으면 겹쳐보기
  recommendedWindow: { type: Object, default: null },  // { lower, upper, score } 추천 공정창
  xFeature: { type: String, default: '' },
  yTarget: { type: String, default: '' },
  spec: { type: Object, default: () => ({ lower: null, upper: null }) },
  dcSpec: { type: Object, default: () => ({ lower: null, upper: null }) },
  minN: { type: Number, default: 10 },
})

const mk = (val, color, label) => ({ xAxis: val, lineStyle: { color, type: 'dashed', width: 2 }, label: { formatter: label, fontSize: 9, color } })
function specLines() {
  const out = []
  if (props.spec.lower != null) out.push(mk(props.spec.lower, C.specUser, 'USL'))
  if (props.spec.upper != null) out.push(mk(props.spec.upper, C.specUser, 'USU'))
  if (props.dcSpec.lower != null) out.push(mk(props.dcSpec.lower, C.specDc, 'DC-L'))
  if (props.dcSpec.upper != null) out.push(mk(props.dcSpec.upper, C.specDc, 'DC-U'))
  return out
}
const zoom = (rightW) => ([
  { type: 'slider', yAxisIndex: 0, right: 8, width: 22, brushSelect: false, handleSize: 24, moveHandleSize: 9, showDetail: false },
  { type: 'inside', yAxisIndex: 0 },
  { type: 'slider', xAxisIndex: 0, height: 18, bottom: 4, brushSelect: false, handleSize: 24, moveHandleSize: 9, showDetail: false },
  { type: 'inside', xAxisIndex: 0 },
])

const isMulti = computed(() => Array.isArray(props.groups) && props.groups.length > 0)
const hasData = computed(() => isMulti.value ? props.groups.some((g) => g.bins.length) : props.bins.length > 0)

function singleOption() {
  const bins = props.bins
  const countData = bins.map((b) => ({
    value: [b.bin_center, b.wafer_count],
    itemStyle: { color: C.count, opacity: b.wafer_count < props.minN ? 0.4 : 1 },
  }))
  const avgData = bins.map((b) => {
    const ci = b.y_sem != null ? +(1.96 * b.y_sem).toFixed(4) : null
    return { value: [b.bin_center, b.y_avg], n: b.wafer_count, ci, left: b.bin_left, right: b.bin_right }
  })
  return {
    legend: { data: ['wafer count', 'y avg'], top: 4, left: 'center', itemWidth: 14, itemHeight: 8, textStyle: { fontSize: 10 } },
    tooltip: {
      trigger: 'axis',
      formatter: (ps) => {
        const a = ps.find((p) => p.seriesName === 'y avg')
        if (!a) return ''
        const d = a.data
        const rng = `[${d.left}, ${d.right}]`
        const avg = d.value[1] == null ? '-' : d.value[1]
        const ci = d.ci == null ? '' : ` ± ${d.ci}`
        return `${props.xFeature} ${rng}<br/>n = ${d.n}<br/>y avg = ${avg}${ci}`
      },
    },
    grid: { left: 54, right: 70, top: 40, bottom: 54 },
    xAxis: { type: 'value', scale: true, name: props.xFeature, nameLocation: 'middle', nameGap: 20, nameTextStyle: { fontSize: 10 } },
    yAxis: [
      { type: 'value', name: 'count', nameTextStyle: { fontSize: 10 } },
      { type: 'value', name: `${props.yTarget}`, position: 'right', nameTextStyle: { fontSize: 10 } },
    ],
    dataZoom: [
      { type: 'slider', yAxisIndex: [0, 1], right: 8, width: 22, brushSelect: false, handleSize: 24, moveHandleSize: 9, showDetail: false },
      { type: 'inside', yAxisIndex: [0, 1] },
      { type: 'slider', xAxisIndex: 0, height: 18, bottom: 4, brushSelect: false, handleSize: 24, moveHandleSize: 9, showDetail: false },
      { type: 'inside', xAxisIndex: 0 },
    ],
    series: [
      { name: 'wafer count', type: 'bar', yAxisIndex: 0, data: countData },
      {
        name: 'y avg', type: 'line', yAxisIndex: 1, smooth: true, symbolSize: 6, z: 3,
        data: avgData, lineStyle: { color: C.avg, width: 2 }, itemStyle: { color: C.avg },
        markLine: { symbol: 'none', data: specLines() },
        markArea: props.recommendedWindow ? {
          silent: true, itemStyle: { color: 'rgba(0,158,115,0.10)' },
          label: { show: true, position: 'insideTop', formatter: '추천 window', fontSize: 9, color: '#009E73' },
          data: [[{ xAxis: props.recommendedWindow.lower }, { xAxis: props.recommendedWindow.upper }]],
        } : undefined,
      },
    ],
  }
}

function multiOption() {
  const groups = props.groups
  const series = groups.map((g, gi) => ({
    name: g.label, type: 'line', smooth: true, symbolSize: 5, z: 3,
    data: g.bins.map((b) => ({ value: [b.bin_center, b.y_avg], n: b.wafer_count, left: b.bin_left, right: b.bin_right })),
    lineStyle: { color: g.color, width: 2 }, itemStyle: { color: g.color },
    ...(gi === 0 ? { markLine: { symbol: 'none', data: specLines() } } : {}),
  }))
  return {
    legend: { data: groups.map((g) => g.label), top: 4, left: 'center', itemWidth: 14, itemHeight: 8, textStyle: { fontSize: 10 } },
    tooltip: {
      trigger: 'axis',
      formatter: (ps) => {
        if (!ps.length) return ''
        const head = `${props.xFeature} ≈ ${(+ps[0].axisValue).toFixed(3)}`
        const lines = ps.map((p) => `${p.marker}${p.seriesName}: ${p.data.value[1] == null ? '-' : p.data.value[1]} (n=${p.data.n})`)
        return [head, ...lines].join('<br/>')
      },
    },
    grid: { left: 54, right: 36, top: 40, bottom: 54 },
    xAxis: { type: 'value', scale: true, name: props.xFeature, nameLocation: 'middle', nameGap: 20, nameTextStyle: { fontSize: 10 } },
    yAxis: { type: 'value', name: `${props.yTarget}`, scale: true, nameTextStyle: { fontSize: 10 } },
    dataZoom: zoom(),
    series,
  }
}

const option = computed(() => (isMulti.value ? multiOption() : singleOption()))
</script>

<template>
  <VChart v-if="hasData" class="chart" :option="option" autoresize />
  <p v-else class="empty">데이터 없음 (이 조합은 관측 표본이 없습니다)</p>
</template>

<style scoped>
.chart { height: 320px; width: 100%; }
.empty { height: 320px; display: flex; align-items: center; justify-content: center; color: #aaa; font-size: 13px; }
</style>
