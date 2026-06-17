<script setup>
// 단일 조합 Window 차트: bar = wafer count, line = y avg (U-shape).
// spec lower/upper를 수직선으로 표시.
import { computed } from 'vue'
import VChart from 'vue-echarts'
import '../echarts.js'

const props = defineProps({
  bins: { type: Array, default: () => [] },
  xFeature: { type: String, default: '' },
  yTarget: { type: String, default: '' },
  spec: { type: Object, default: () => ({ lower: null, upper: null }) },
  dcSpec: { type: Object, default: () => ({ lower: null, upper: null }) },
})

const option = computed(() => {
  const counts = props.bins.map((b) => [b.bin_center, b.wafer_count])
  const yavgs = props.bins.map((b) => [b.bin_center, b.y_avg])

  const specLines = []
  // user spec: 빨간 수직선
  if (props.spec.lower != null) specLines.push({ xAxis: props.spec.lower, lineStyle: { color: '#dc2626' } })
  if (props.spec.upper != null) specLines.push({ xAxis: props.spec.upper, lineStyle: { color: '#dc2626' } })
  // DC spec: 검은 수직선
  if (props.dcSpec.lower != null) specLines.push({ xAxis: props.dcSpec.lower, lineStyle: { color: '#1d1d1f' } })
  if (props.dcSpec.upper != null) specLines.push({ xAxis: props.dcSpec.upper, lineStyle: { color: '#1d1d1f' } })

  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 50, right: 80, top: 16, bottom: 30 },
    xAxis: { type: 'value', scale: true, name: props.xFeature, nameLocation: 'middle', nameGap: 22, nameTextStyle: { fontSize: 10 } },
    yAxis: [
      { type: 'value', name: 'count', nameTextStyle: { fontSize: 10 } },
      { type: 'value', name: `${props.yTarget} avg`, position: 'right', offset: 22, nameTextStyle: { fontSize: 10 } },
    ],
    // Y축 sliding scaler (count·avg 두 축을 함께 스케일)
    dataZoom: [
      { type: 'slider', yAxisIndex: [0, 1], right: 4, width: 14, brushSelect: false },
      { type: 'inside', yAxisIndex: [0, 1] },
    ],
    series: [
      { name: 'count', type: 'bar', yAxisIndex: 0, data: counts, itemStyle: { color: '#bfdbfe' } },
      {
        name: 'avg', type: 'line', yAxisIndex: 1, smooth: true, symbolSize: 6,
        data: yavgs, lineStyle: { color: '#2563eb', width: 2 }, itemStyle: { color: '#2563eb' },
        markLine: { symbol: 'none', label: { show: false }, lineStyle: { width: 2 }, data: specLines },
      },
    ],
  }
})
</script>

<template>
  <VChart class="chart" :option="option" autoresize />
</template>

<style scoped>
.chart { height: 240px; width: 100%; }
</style>
