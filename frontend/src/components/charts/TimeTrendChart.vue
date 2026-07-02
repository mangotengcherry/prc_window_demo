<template>
  <PlotlyChart :data="data" :layout="layout" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import PlotlyChart from './PlotlyChart.vue'

const props = defineProps<{ trend: any; spc?: any }>()

const actualDates = computed(() => props.trend?.actual?.map((row: any) => row.date) || [])
const violationDates = computed(() => {
  const map = new Map<string, string>()
  ;(props.spc?.violations || []).forEach((v: any) => map.set(v.date, v.type))
  return map
})

const data = computed(() => [
  {
    type: 'scatter',
    mode: 'lines+markers',
    name: 'Actual EDS',
    x: actualDates.value,
    y: props.trend?.actual?.map((row: any) => row.actual_fail_rate) || [],
    line: { color: '#111827', width: 2 },
    marker: {
      color: actualDates.value.map((date: string) => (violationDates.value.get(date) === 'beyond_3sigma' ? '#dc2626' : '#111827')),
      size: actualDates.value.map((date: string) => (violationDates.value.get(date) === 'beyond_3sigma' ? 9 : 6)),
    },
  },
  {
    type: 'scatter',
    mode: 'lines+markers',
    name: 'Pending FAB 물량',
    x: props.trend?.pending?.map((row: any) => row.date) || [],
    y: props.trend?.pending?.map((row: any) => row.pending_wafer_count) || [],
    yaxis: 'y2',
    line: { color: '#f59e0b', width: 2, dash: 'dash' },
  },
])

const spcShapes = computed(() => {
  if (!props.spc) return []
  const shapes: any[] = [
    { type: 'line', xref: 'paper', x0: 0, x1: 1, yref: 'y', y0: props.spc.center, y1: props.spc.center, line: { color: '#4b5563', width: 1, dash: 'dash' } },
    { type: 'line', xref: 'paper', x0: 0, x1: 1, yref: 'y', y0: props.spc.ucl, y1: props.spc.ucl, line: { color: '#dc2626', width: 1, dash: 'dot' } },
    { type: 'line', xref: 'paper', x0: 0, x1: 1, yref: 'y', y0: props.spc.lcl, y1: props.spc.lcl, line: { color: '#dc2626', width: 1, dash: 'dot' } },
  ]
  const dates = actualDates.value
  ;(props.spc.violations || [])
    .filter((v: any) => v.type === 'run_of_7')
    .forEach((v: any) => {
      const idx = dates.indexOf(v.date)
      if (idx < 0) return
      const startIdx = Math.max(0, idx - 6)
      shapes.push({
        type: 'rect',
        xref: 'x',
        yref: 'paper',
        x0: dates[startIdx],
        x1: dates[idx],
        y0: 0,
        y1: 1,
        fillcolor: 'rgba(245,158,11,0.15)',
        line: { width: 0 },
        layer: 'below',
      })
    })
  return shapes
})

const layout = computed(() => ({
  xaxis: { title: '일자' },
  yaxis: { title: 'Actual fail rate', tickformat: '.1%' },
  yaxis2: { title: 'Pending wafer 수', overlaying: 'y', side: 'right', rangemode: 'tozero' },
  legend: { orientation: 'h', y: -0.24 },
  shapes: spcShapes.value,
}))
</script>
