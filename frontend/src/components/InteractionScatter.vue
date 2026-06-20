<script setup>
// 교호작용 scatter: 두 feature를 x/y축, value_field를 색(visualMap).
//  - x/y dataZoom 슬라이더
//  - 점 클릭 = outlier 제외/복원, 영역 brush = 범위 일괄 제외 → heatmap/rank 즉시 반영(부모가 재계산)
import { computed } from 'vue'
import VChart from 'vue-echarts'
import '../echarts.js'

const props = defineProps({
  points: { type: Array, default: () => [] },          // [{ x, y, value, i }]
  excluded: { type: Object, default: () => new Set() }, // 제외된 i 집합
  xLabel: { type: String, default: 'x' },
  yLabel: { type: String, default: 'y' },
  valueLabel: { type: String, default: 'value' },
  sampled: { type: Boolean, default: false },
})
const emit = defineEmits(['toggle-exclude', 'exclude-region'])

const hasValue = computed(() => props.points.some((p) => p.value != null))
const activeData = computed(() => props.points.filter((p) => !props.excluded.has(p.i)).map((p) => [p.x, p.y, p.value, p.i]))
const excludedData = computed(() => props.points.filter((p) => props.excluded.has(p.i)).map((p) => [p.x, p.y, p.value, p.i]))
const vals = computed(() => activeData.value.map((d) => d[2]).filter((v) => v != null))
function minmax(a) { let lo = Infinity, hi = -Infinity; for (const v of a) { if (v < lo) lo = v; if (v > hi) hi = v } return a.length ? [lo, hi] : [0, 1] }

const option = computed(() => {
  const [vmin, vmax] = minmax(vals.value)
  return {
    tooltip: { trigger: 'item', formatter: (p) =>
      `${props.xLabel}: ${p.data[0]}<br/>${props.yLabel}: ${p.data[1]}` +
      (p.data[2] == null ? '' : `<br/>${props.valueLabel}: ${p.data[2]}`) +
      `<br/><span style="color:#999">클릭 = 제외/복원</span>` },
    toolbox: { show: true, right: 8, top: -2, itemSize: 13,
      feature: { brush: { type: ['rect', 'clear'], title: { rect: '영역 제외', clear: '선택 해제' } } } },
    brush: { xAxisIndex: 0, yAxisIndex: 0, brushType: 'rect', brushMode: 'single',
      throttleType: 'debounce', throttleDelay: 250,
      brushStyle: { color: 'rgba(214,69,0,0.10)', borderColor: 'rgba(214,69,0,0.5)' } },
    visualMap: hasValue.value ? {
      type: 'continuous', dimension: 2, min: vmin, max: vmax, calculable: true, seriesIndex: 0,
      orient: 'horizontal', left: 'center', top: 0, itemWidth: 11, itemHeight: 100, precision: 1,
      text: ['높음', '낮음'], textStyle: { fontSize: 9 }, inRange: { color: ['#440154', '#21918c', '#fde725'] },
    } : undefined,
    grid: { left: 52, right: 40, top: 34, bottom: 46 },
    xAxis: { type: 'value', scale: true, name: props.xLabel, nameLocation: 'middle', nameGap: 23, nameTextStyle: { fontSize: 10 } },
    yAxis: { type: 'value', scale: true, name: props.yLabel, nameTextStyle: { fontSize: 10 } },
    dataZoom: [
      { type: 'slider', xAxisIndex: 0, bottom: 4, height: 14, brushSelect: false, handleSize: 22, moveHandleSize: 8, showDetail: false },
      { type: 'slider', yAxisIndex: 0, right: 6, width: 14, brushSelect: false, handleSize: 22, moveHandleSize: 8, showDetail: false },
    ],
    series: [
      { type: 'scatter', data: activeData.value, symbolSize: 6, itemStyle: hasValue.value ? {} : { color: '#0072B2', opacity: 0.6 } },
      { type: 'scatter', data: excludedData.value, symbolSize: 6, itemStyle: { color: 'transparent', borderColor: '#bbb', borderWidth: 1 } },
    ],
  }
})

function onClick(p) {
  if (p && (p.seriesIndex === 0 || p.seriesIndex === 1) && Array.isArray(p.data)) emit('toggle-exclude', p.data[3])
}
function onBrushSelected(params) {
  const sel = params?.batch?.[0]?.selected?.find((s) => s.seriesIndex === 0)
  if (!sel || !sel.dataIndex?.length) return
  const idx = sel.dataIndex.map((di) => activeData.value[di]?.[3]).filter((v) => v != null)
  if (idx.length) emit('exclude-region', idx)
}
</script>

<template>
  <div class="wrap">
    <span v-if="sampled" class="ds">다운샘플 표시(≤5000)</span>
    <VChart v-if="points.length" class="chart" :option="option" autoresize @click="onClick" @brushselected="onBrushSelected" />
    <p v-else class="empty">데이터 없음</p>
  </div>
</template>

<style scoped>
.wrap { position: relative; }
.ds { position: absolute; top: 0; left: 6px; z-index: 2; font-size: 10px; font-weight: 600; color: #92400e; background: #fde68a; padding: 1px 7px; border-radius: 999px; }
.chart { height: 320px; width: 100%; }
.empty { height: 320px; display: flex; align-items: center; justify-content: center; color: #aaa; font-size: 13px; }
</style>
