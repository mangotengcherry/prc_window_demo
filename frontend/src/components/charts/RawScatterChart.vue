<template>
  <PlotlyChart :data="traces" :layout="layout" @point-click="$emit('point-click', $event)" @points-selected="$emit('points-selected', $event)" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import PlotlyChart from './PlotlyChart.vue'
import { CATEGORICAL_PALETTE } from '../../palette.ts'

const props = defineProps<{ points: any[]; xTitle?: string; yTitle?: string; safeWindow?: { lower: number | null; upper: number | null } | null }>()
defineEmits<{ (event: 'point-click', point: any): void; (event: 'points-selected', points: any[]): void }>()

const palette = CATEGORICAL_PALETTE

const traces = computed(() => {
  const groups = new Map<string, any[]>()
  props.points.forEach((point) => {
    const key = point.legend || '전체 wafer'
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key)?.push(point)
  })
  return [...groups.entries()].map(([name, rows], index) => ({
    type: 'scattergl',
    mode: 'markers',
    name,
    x: rows.map((row) => row.x_value),
    y: rows.map((row) => row.selected_bin_group_fail_rate),
    customdata: rows,
    text: rows.map((row) => `${row.wafer_id}<br>${row.tool_id}/${row.chamber_id}<br>${row.zone}`),
    marker: {
      color: palette[index % palette.length],
      size: rows.map((row) => Math.max(6, Math.min(16, 6 + row.yield_loss * 180))),
      opacity: 0.72,
      line: { width: 0.5, color: '#ffffff' },
    },
  }))
})

const safeWindowShapes = computed(() => {
  const lower = props.safeWindow?.lower
  const upper = props.safeWindow?.upper
  if (lower == null || upper == null) return []
  return [
    {
      type: 'rect',
      xref: 'x',
      yref: 'paper',
      x0: lower,
      x1: upper,
      y0: 0,
      y1: 1,
      fillcolor: 'rgba(22,163,74,0.08)',
      line: { width: 0 },
      layer: 'below',
    },
    { type: 'line', xref: 'x', yref: 'paper', x0: lower, x1: lower, y0: 0, y1: 1, line: { color: '#16a34a', width: 1, dash: 'dot' } },
    { type: 'line', xref: 'x', yref: 'paper', x0: upper, x1: upper, y0: 0, y1: 1, line: { color: '#16a34a', width: 1, dash: 'dot' } },
  ]
})

const layout = computed(() => ({
  dragmode: 'lasso',
  xaxis: { title: props.xTitle || 'FAB 관리 인자', zeroline: false },
  yaxis: { title: props.yTitle || 'BIN Group fail rate', tickformat: '.1%' },
  legend: { orientation: 'h', y: -0.24 },
  shapes: safeWindowShapes.value,
}))
</script>
