<template>
  <PlotlyChart :data="traces" :layout="layout" @point-click="$emit('point-click', $event)" @points-selected="$emit('points-selected', $event)" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import PlotlyChart from './PlotlyChart.vue'

const props = defineProps<{ points: any[]; xTitle?: string; yTitle?: string }>()
defineEmits<{ (event: 'point-click', point: any): void; (event: 'points-selected', points: any[]): void }>()

const palette = ['#2563eb', '#16a34a', '#ea580c', '#7c3aed', '#0891b2', '#be123c', '#4b5563']

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

const layout = computed(() => ({
  dragmode: 'lasso',
  xaxis: { title: props.xTitle || 'FAB 관리 인자', zeroline: false },
  yaxis: { title: props.yTitle || 'BIN Group fail rate', tickformat: '.1%' },
  legend: { orientation: 'h', y: -0.24 },
}))
</script>
