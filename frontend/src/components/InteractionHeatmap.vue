<script setup>
// 교호작용 heatmap: x_bin×y_bin 격자, cell 색 = value(평균/중앙값). 저카운트 셀 디엠퍼시스.
// cells는 부모(InteractionPanel)가 scatter 점(제외 반영)으로 즉시 계산해 내려줌.
import { computed, ref, watch } from 'vue'
import VChart from 'vue-echarts'
import '../echarts.js'
import { HEAT_RAMP } from '../palette.js'

const props = defineProps({
  cells: { type: Array, default: () => [] },   // [{ x_bin, y_bin, x_bin_label, y_bin_label, value, count }]
  xBins: { type: Number, default: 10 },
  yBins: { type: Number, default: 10 },
  xLabel: { type: String, default: 'x' },
  yLabel: { type: String, default: 'y' },
  valueLabel: { type: String, default: 'value' },
  minCount: { type: Number, default: 10 },
  highlight: { type: Object, default: null },  // { x_bin, y_bin } — 순위 테이블 hover와 연동
})
const emit = defineEmits(['cellhover'])

// 셀(x_bin,y_bin) → data 배열 인덱스. 테이블 hover 시 해당 셀을 강조(dispatchAction).
const chart = ref(null)
const cellIndex = computed(() => { const m = new Map(); props.cells.forEach((c, i) => m.set(c.x_bin + ',' + c.y_bin, i)); return m })
watch(() => props.highlight, (h) => {
  const c = chart.value
  if (!c) return
  c.dispatchAction({ type: 'downplay', seriesIndex: 0 })
  if (!h) return
  const di = cellIndex.value.get(h.x_bin + ',' + h.y_bin)
  if (di != null) c.dispatchAction({ type: 'highlight', seriesIndex: 0, dataIndex: di })
})
const onOver = (p) => { if (p.data?.value) emit('cellhover', { x_bin: p.data.value[0], y_bin: p.data.value[1] }) }
const onOut = () => emit('cellhover', null)

const xLabels = computed(() => { const a = Array(props.xBins).fill(''); props.cells.forEach((c) => { a[c.x_bin] = c.x_bin_label }); return a })
const yLabels = computed(() => { const a = Array(props.yBins).fill(''); props.cells.forEach((c) => { a[c.y_bin] = c.y_bin_label }); return a })
const vals = computed(() => props.cells.map((c) => c.value).filter((v) => v != null))
function minmax(a) { let lo = Infinity, hi = -Infinity; for (const v of a) { if (v < lo) lo = v; if (v > hi) hi = v } return a.length ? [lo, hi] : [0, 1] }

const option = computed(() => {
  // 대부분 셀이 thin이면(희소 데이터) 디엠퍼시스가 무의미 → 색을 살림
  const thinFrac = props.cells.length ? props.cells.filter((c) => c.count < props.minCount).length / props.cells.length : 0
  const dimThin = thinFrac <= 0.6
  const data = props.cells.map((c) => ({
    value: [c.x_bin, c.y_bin, c.value], count: c.count, xl: c.x_bin_label, yl: c.y_bin_label,
    itemStyle: (dimThin && c.count < props.minCount) ? { opacity: 0.4 } : {},
  }))
  const [vmin, vmax] = minmax(vals.value)
  return {
    tooltip: { position: 'top', formatter: (p) =>
      `${props.xLabel}: ${p.data.xl}<br/>${props.yLabel}: ${p.data.yl}` +
      `<br/>${props.valueLabel}: ${p.data.value[2]}<br/>n = ${p.data.count}` +
      (p.data.count < props.minCount ? ` <span style="color:#b45309">(표본 부족)</span>` : '') },
    visualMap: {
      type: 'continuous', min: vmin, max: vmax, calculable: true,
      orient: 'horizontal', left: 'center', top: 0, itemWidth: 11, itemHeight: 110, precision: 1,
      text: ['집계 높음', '낮음'], textStyle: { fontSize: 9 }, inRange: { color: HEAT_RAMP },
    },
    grid: { left: 64, right: 40, top: 32, bottom: 72 },
    xAxis: { type: 'category', data: xLabels.value, name: props.xLabel, nameLocation: 'middle', nameGap: 52,
      nameTextStyle: { fontSize: 10 }, axisLabel: { fontSize: 8, rotate: 40, interval: 0 } },
    yAxis: { type: 'category', data: yLabels.value, name: props.yLabel, nameTextStyle: { fontSize: 10 },
      axisLabel: { fontSize: 8, interval: 0 } },
    dataZoom: [
      { type: 'slider', xAxisIndex: 0, bottom: 2, height: 12, brushSelect: false, handleSize: 20, moveHandleSize: 7, showDetail: false, labelFormatter: '' },
      { type: 'slider', yAxisIndex: 0, right: 6, width: 12, brushSelect: false, handleSize: 20, moveHandleSize: 7, showDetail: false, labelFormatter: '' },
    ],
    series: [{ type: 'heatmap', data, label: { show: false },
      emphasis: { itemStyle: { borderColor: '#111827', borderWidth: 2.5, shadowBlur: 4, shadowColor: 'rgba(0,0,0,0.4)' } } }],
  }
})
</script>

<template>
  <div class="wrap">
    <VChart v-if="cells.length" ref="chart" class="chart" :option="option" autoresize @mouseover="onOver" @globalout="onOut" />
    <p v-else class="empty">데이터 없음</p>
  </div>
</template>

<style scoped>
.wrap { position: relative; }
.chart { height: 320px; width: 100%; }
.empty { height: 320px; display: flex; align-items: center; justify-content: center; color: #aaa; font-size: 13px; }
</style>
