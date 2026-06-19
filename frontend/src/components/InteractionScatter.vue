<script setup>
// 교호작용 scatter: 선택한 두 feature를 x/y축, value_field를 색으로(visualMap).
import { computed } from 'vue'
import VChart from 'vue-echarts'
import '../echarts.js'

const props = defineProps({
  points: { type: Array, default: () => [] },   // [{ x, y, value }]
  xLabel: { type: String, default: 'x' },
  yLabel: { type: String, default: 'y' },
  valueLabel: { type: String, default: 'value' },
  sampled: { type: Boolean, default: false },
})

const hasValue = computed(() => props.points.some((p) => p.value != null))
const vals = computed(() => props.points.filter((p) => p.value != null).map((p) => p.value))

const option = computed(() => {
  const data = props.points.map((p) => [p.x, p.y, p.value])
  const vmin = hasValue.value ? Math.min(...vals.value) : 0
  const vmax = hasValue.value ? Math.max(...vals.value) : 1
  return {
    tooltip: {
      trigger: 'item',
      formatter: (p) => `${props.xLabel}: ${p.value[0]}<br/>${props.yLabel}: ${p.value[1]}` +
        (p.value[2] == null ? '' : `<br/>${props.valueLabel}: ${p.value[2]}`),
    },
    grid: { left: 56, right: hasValue.value ? 72 : 20, top: 16, bottom: 50 },
    xAxis: { type: 'value', scale: true, name: props.xLabel, nameLocation: 'middle', nameGap: 26, nameTextStyle: { fontSize: 10 } },
    yAxis: { type: 'value', scale: true, name: props.yLabel, nameTextStyle: { fontSize: 10 } },
    visualMap: hasValue.value ? {
      type: 'continuous', dimension: 2, min: vmin, max: vmax,
      right: 4, top: 'middle', itemHeight: 120, precision: 1, text: ['높음', '낮음'],
      textStyle: { fontSize: 9 }, calculable: true,
      inRange: { color: ['#440154', '#21918c', '#fde725'] },  // viridis(색맹 안전)
    } : undefined,
    dataZoom: [
      { type: 'inside', xAxisIndex: 0 }, { type: 'inside', yAxisIndex: 0 },
    ],
    series: [{
      type: 'scatter', data, symbolSize: 5,
      itemStyle: hasValue.value ? {} : { color: '#0072B2', opacity: 0.6 },
    }],
  }
})
</script>

<template>
  <div class="wrap">
    <span v-if="sampled" class="ds">다운샘플 표시(≤3000)</span>
    <VChart v-if="points.length" class="chart" :option="option" autoresize />
    <p v-else class="empty">데이터 없음</p>
  </div>
</template>

<style scoped>
.wrap { position: relative; }
.ds { position: absolute; top: 0; right: 6px; z-index: 2; font-size: 10px; font-weight: 600; color: #92400e; background: #fde68a; padding: 1px 7px; border-radius: 999px; }
.chart { height: 300px; width: 100%; }
.empty { height: 300px; display: flex; align-items: center; justify-content: center; color: #aaa; font-size: 13px; }
</style>
