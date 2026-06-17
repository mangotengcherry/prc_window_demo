<script setup>
// 단일 조합 시계열: 위 = 이 조합의 target, 아래 = 이 조합의 feature. 시간축 공유.
//  - feature의 spec lower/upper를 아래 차트에 수평선으로 표시
//  - 각 차트에 '이동평균(moving average) 추세선'을 scatter와 대비되는 색으로 함께 표시
import { computed } from 'vue'
import VChart from 'vue-echarts'
import '../echarts.js'

const props = defineProps({
  targetPoints: { type: Array, default: () => [] }, // [[iso, v], ...] (시간 오름차순)
  featurePoints: { type: Array, default: () => [] },
  yTarget: { type: String, default: '' },
  xFeature: { type: String, default: '' },
  spec: { type: Object, default: () => ({ lower: null, upper: null }) },
})

// 중심 이동평균(centered moving average) — 시간순 정렬된 점들의 추세선
function movingAverage(points) {
  const n = points.length
  if (!n) return []
  const win = Math.max(5, Math.round(n / 15)) // 데이터 양에 맞춰 윈도우 자동 조절
  const half = Math.floor(win / 2)
  const out = []
  for (let i = 0; i < n; i++) {
    let sum = 0, cnt = 0
    for (let j = Math.max(0, i - half); j <= Math.min(n - 1, i + half); j++) { sum += points[j][1]; cnt++ }
    out.push([points[i][0], +(sum / cnt).toFixed(4)])
  }
  return out
}

const option = computed(() => {
  const maTarget = movingAverage(props.targetPoints)
  const maFeature = movingAverage(props.featurePoints)

  // feature 차트의 spec 수평선
  const specLines = []
  if (props.spec.lower != null) specLines.push({ yAxis: props.spec.lower, lineStyle: { color: '#dc2626' }, label: { formatter: 'L', position: 'start' } })
  if (props.spec.upper != null) specLines.push({ yAxis: props.spec.upper, lineStyle: { color: '#dc2626' }, label: { formatter: 'U', position: 'start' } })

  return {
    axisPointer: { link: [{ xAxisIndex: 'all' }] },
    tooltip: { trigger: 'axis' },
    legend: { top: 0, right: 8, itemWidth: 16, itemHeight: 8, textStyle: { fontSize: 10 }, data: ['이동평균(target)', '이동평균(feature)'] },
    grid: [
      { left: 56, right: 36, top: 22, height: '34%' },
      { left: 56, right: 36, top: '60%', height: '34%' },
    ],
    xAxis: [
      { type: 'time', gridIndex: 0, axisLabel: { show: false } },
      { type: 'time', gridIndex: 1 },
    ],
    yAxis: [
      { type: 'value', gridIndex: 0, name: props.yTarget, scale: true, nameTextStyle: { fontSize: 10 } },
      { type: 'value', gridIndex: 1, name: props.xFeature, scale: true, nameTextStyle: { fontSize: 10 } },
    ],
    dataZoom: [
      { type: 'inside', xAxisIndex: [0, 1] },
      // 각 차트 Y축 sliding scaler (위 target / 아래 feature)
      { type: 'slider', yAxisIndex: 0, right: 6, top: 22, height: '34%', width: 14, brushSelect: false },
      { type: 'slider', yAxisIndex: 1, right: 6, top: '60%', height: '34%', width: 14, brushSelect: false },
      { type: 'inside', yAxisIndex: 0 },
      { type: 'inside', yAxisIndex: 1 },
    ],
    series: [
      {
        name: props.yTarget, type: 'scatter', xAxisIndex: 0, yAxisIndex: 0, data: props.targetPoints,
        symbolSize: 4, itemStyle: { color: 'rgba(37, 99, 235, 0.55)' },
      },
      {
        name: '이동평균(target)', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: maTarget,
        smooth: true, showSymbol: false, z: 5, lineStyle: { color: '#f97316', width: 3 }, itemStyle: { color: '#f97316' },
      },
      {
        name: props.xFeature, type: 'scatter', xAxisIndex: 1, yAxisIndex: 1, data: props.featurePoints,
        symbolSize: 4, itemStyle: { color: 'rgba(22, 163, 74, 0.5)' },
        markLine: { symbol: 'none', data: specLines },
      },
      {
        name: '이동평균(feature)', type: 'line', xAxisIndex: 1, yAxisIndex: 1, data: maFeature,
        smooth: true, showSymbol: false, z: 5, lineStyle: { color: '#7c3aed', width: 3 }, itemStyle: { color: '#7c3aed' },
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
