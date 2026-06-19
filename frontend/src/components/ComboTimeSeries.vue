<script setup>
// 단일 조합 시계열 (M1): 위=target(scatter+이동평균+관리한계 ±3σ), 아래=feature(scatter+이동평균+spec).
import { computed } from 'vue'
import VChart from 'vue-echarts'
import '../echarts.js'
import { PALETTE as C } from '../palette.js'

const props = defineProps({
  target: { type: Object, default: null },   // { observed_points, avg, control_limits, unit, ... }
  feature: { type: Object, default: null },  // { points, avg, control_limits, unit, ... }
  yTarget: { type: String, default: '' },
  xFeature: { type: String, default: '' },
  spec: { type: Object, default: () => ({ lower: null, upper: null }) },
  dcSpec: { type: Object, default: () => ({ lower: null, upper: null }) },
  sampled: { type: Boolean, default: false },
})

function movingAverage(points) {
  const n = points.length
  if (!n) return []
  const win = Math.max(5, Math.round(n / 15))
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
  const tp = (props.target?.observed_points || []).map((p) => [p.time, p.value])
  const fp = props.feature?.points || []

  // 관리한계 (±3σ) — backend가 풀데이터로 계산해 내려준 값
  const tcl = props.target?.control_limits
  const clMark = (cl, color) => {
    if (!cl) return []
    return [
      { yAxis: cl.ucl, lineStyle: { color, type: 'dashed', width: 1, opacity: 0.7 }, label: { formatter: 'UCL', fontSize: 9, color, position: 'start' } },
      { yAxis: cl.lcl, lineStyle: { color, type: 'dashed', width: 1, opacity: 0.7 }, label: { formatter: 'LCL', fontSize: 9, color, position: 'start' } },
    ]
  }
  // feature spec (user/DC) 수평선 — 라벨은 왼쪽(start)에 둬서 우측 y슬라이더와 겹치지 않게
  const hl = (v, color, label) => ({ yAxis: v, lineStyle: { color, type: 'dashed', width: 2 }, label: { formatter: label, fontSize: 9, color, position: 'start' } })
  const featLines = []
  if (props.spec.lower != null) featLines.push(hl(props.spec.lower, C.specUser, 'USL'))
  if (props.spec.upper != null) featLines.push(hl(props.spec.upper, C.specUser, 'USU'))
  if (props.dcSpec.lower != null) featLines.push(hl(props.dcSpec.lower, C.specDc, 'DC-L'))
  if (props.dcSpec.upper != null) featLines.push(hl(props.dcSpec.upper, C.specDc, 'DC-U'))

  return {
    axisPointer: { link: [{ xAxisIndex: 'all' }] },
    tooltip: { trigger: 'axis' },
    legend: { top: 2, left: 'center', itemWidth: 14, itemHeight: 8, textStyle: { fontSize: 10 },
      data: [`${props.yTarget}`, '이동평균(target)', `${props.xFeature}`, '이동평균(feature)'] },
    grid: [{ left: 58, right: 38, top: 42, height: '30%' }, { left: 58, right: 38, top: '56%', height: '30%' }],
    xAxis: [{ type: 'time', gridIndex: 0, axisLabel: { show: false } }, { type: 'time', gridIndex: 1 }],
    yAxis: [
      { type: 'value', gridIndex: 0, name: props.yTarget, scale: true, nameTextStyle: { fontSize: 10 } },
      { type: 'value', gridIndex: 1, name: props.xFeature, scale: true, nameTextStyle: { fontSize: 10 } },
    ],
    dataZoom: [
      { type: 'inside', xAxisIndex: [0, 1] },
      { type: 'slider', yAxisIndex: 0, right: 6, top: 42, height: '30%', width: 22, brushSelect: false, handleSize: 24, moveHandleSize: 9, showDetail: false },
      { type: 'slider', yAxisIndex: 1, right: 6, top: '56%', height: '30%', width: 22, brushSelect: false, handleSize: 24, moveHandleSize: 9, showDetail: false },
      { type: 'inside', yAxisIndex: 0 }, { type: 'inside', yAxisIndex: 1 },
      { type: 'slider', xAxisIndex: [0, 1], left: 58, right: 38, bottom: 6, height: 16, brushSelect: false, handleSize: 24, moveHandleSize: 9, showDetail: false },
    ],
    series: [
      { name: `${props.yTarget}`, type: 'scatter', xAxisIndex: 0, yAxisIndex: 0, data: tp, symbolSize: 4,
        itemStyle: { color: C.tsTarget }, markLine: { symbol: 'none', data: clMark(tcl, C.faint) } },
      { name: '이동평균(target)', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: movingAverage(tp),
        smooth: true, showSymbol: false, z: 5, lineStyle: { color: C.tsTargetMa, width: 3 }, itemStyle: { color: C.tsTargetMa } },
      { name: `${props.xFeature}`, type: 'scatter', xAxisIndex: 1, yAxisIndex: 1, data: fp, symbolSize: 4,
        itemStyle: { color: C.tsFeature }, markLine: { symbol: 'none', data: featLines } },
      { name: '이동평균(feature)', type: 'line', xAxisIndex: 1, yAxisIndex: 1, data: movingAverage(fp),
        smooth: true, showSymbol: false, z: 5, lineStyle: { color: C.tsFeatureMa, width: 3 }, itemStyle: { color: C.tsFeatureMa } },
    ],
  }
})
</script>

<template>
  <div class="ts">
    <span v-if="sampled" class="ds">다운샘플 표시</span>
    <VChart v-if="target || feature" class="chart" :option="option" autoresize />
    <p v-else class="empty">시계열 데이터 없음</p>
  </div>
</template>

<style scoped>
.ts { position: relative; height: 100%; }
.ds { position: absolute; top: 2px; left: 56px; z-index: 2; font-size: 10px; font-weight: 600; color: #92400e; background: #fde68a; padding: 1px 7px; border-radius: 999px; }
.chart { height: 400px; width: 100%; }
.empty { height: 400px; display: flex; align-items: center; justify-content: center; color: #aaa; font-size: 13px; }
</style>
