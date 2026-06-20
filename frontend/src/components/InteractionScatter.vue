<script setup>
// 교호작용 scatter: 두 feature를 x/y축, value를 색으로(높음=빨강, 낮음=회색).
//  - x/y dataZoom 슬라이더
//  - 영역 brush(드래그) = 그 구간 데이터로 재계산(focus). 시계열 차트의 기간 brush와 동일한 의미.
//    선택 영역 안의 점만 색, 밖은 회색으로 표시.
import { computed } from 'vue'
import VChart from 'vue-echarts'
import '../echarts.js'
import { HEAT_RAMP } from '../palette.js'

const props = defineProps({
  points: { type: Array, default: () => [] },   // [{ x, y, value, i }]
  focus: { type: Object, default: null },        // { x:[lo,hi], y:[lo,hi] } | null
  xLabel: { type: String, default: 'x' },
  yLabel: { type: String, default: 'y' },
  valueLabel: { type: String, default: 'value' },
  sampled: { type: Boolean, default: false },
})
const emit = defineEmits(['focus'])

const inRegion = (p) => !props.focus ||
  (p.x >= props.focus.x[0] && p.x <= props.focus.x[1] && p.y >= props.focus.y[0] && p.y <= props.focus.y[1])
const hasValue = computed(() => props.points.some((p) => p.value != null))
const inData = computed(() => props.points.filter(inRegion).map((p) => [p.x, p.y, p.value, p.i]))
const outData = computed(() => props.focus ? props.points.filter((p) => !inRegion(p)).map((p) => [p.x, p.y, p.value, p.i]) : [])
const allVals = computed(() => props.points.map((p) => p.value).filter((v) => v != null))
function minmax(a) { let lo = Infinity, hi = -Infinity; for (const v of a) { if (v < lo) lo = v; if (v > hi) hi = v } return a.length ? [lo, hi] : [0, 1] }

const option = computed(() => {
  const [vmin, vmax] = minmax(allVals.value)
  return {
    tooltip: { trigger: 'item', formatter: (p) =>
      `${props.xLabel}: ${p.data[0]}<br/>${props.yLabel}: ${p.data[1]}` +
      (p.data[2] == null ? '' : `<br/>${props.valueLabel}: ${p.data[2]}`) },
    toolbox: { show: true, right: 8, top: -2, itemSize: 13,
      feature: { brush: { type: ['rect', 'clear'], title: { rect: '영역 선택(재계산)', clear: '전체 보기' } } } },
    brush: { xAxisIndex: 0, yAxisIndex: 0, brushType: 'rect', brushMode: 'single',
      throttleType: 'debounce', throttleDelay: 250,
      brushStyle: { color: 'rgba(214,69,0,0.08)', borderColor: 'rgba(214,69,0,0.5)' } },
    visualMap: hasValue.value ? {
      type: 'continuous', dimension: 2, min: vmin, max: vmax, calculable: true, seriesIndex: 0,
      orient: 'horizontal', left: 'center', top: 0, itemWidth: 11, itemHeight: 100, precision: 1,
      text: ['높음', '낮음'], textStyle: { fontSize: 9 }, inRange: { color: HEAT_RAMP },
    } : undefined,
    grid: { left: 52, right: 40, top: 34, bottom: 46 },
    xAxis: { type: 'value', scale: true, name: props.xLabel, nameLocation: 'middle', nameGap: 23, nameTextStyle: { fontSize: 10 } },
    yAxis: { type: 'value', scale: true, name: props.yLabel, nameTextStyle: { fontSize: 10 } },
    dataZoom: [
      { type: 'slider', xAxisIndex: 0, bottom: 4, height: 14, brushSelect: false, handleSize: 22, moveHandleSize: 8, showDetail: false },
      { type: 'slider', yAxisIndex: 0, right: 6, width: 14, brushSelect: false, handleSize: 22, moveHandleSize: 8, showDetail: false },
    ],
    series: [
      { type: 'scatter', data: inData.value, symbolSize: 6, itemStyle: hasValue.value ? {} : { color: '#737373', opacity: 0.7 } },
      { type: 'scatter', data: outData.value, symbolSize: 5, itemStyle: { color: '#d4d4d4', opacity: 0.5 } },
    ],
  }
})

// 영역 brush → 선택 구간(x/y 범위) 방출. 비우면 전체로 복귀.
function onBrushEnd(params) {
  const a = params?.areas?.[0]
  if (!a || !a.coordRange) { emit('focus', null); return }
  const cr = a.coordRange
  const xr = cr[0], yr = cr[1]
  if (!xr || !yr) return
  emit('focus', { x: [Math.min(...xr), Math.max(...xr)], y: [Math.min(...yr), Math.max(...yr)] })
}
</script>

<template>
  <div class="wrap">
    <span v-if="sampled" class="ds">다운샘플 표시(≤5000)</span>
    <VChart v-if="points.length" class="chart" :option="option" autoresize @brushend="onBrushEnd" />
    <p v-else class="empty">데이터 없음</p>
  </div>
</template>

<style scoped>
.wrap { position: relative; }
.ds { position: absolute; top: 0; left: 6px; z-index: 2; font-size: 10px; font-weight: 600; color: #92400e; background: #fde68a; padding: 1px 7px; border-radius: 999px; }
.chart { height: 320px; width: 100%; }
.empty { height: 320px; display: flex; align-items: center; justify-content: center; color: #aaa; font-size: 13px; }
</style>
