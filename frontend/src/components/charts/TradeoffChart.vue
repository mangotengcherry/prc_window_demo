<template>
  <PlotlyChart :data="data" :layout="layout" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import PlotlyChart from './PlotlyChart.vue'
import { CATEGORICAL_PALETTE } from '../../palette.ts'

const props = defineProps<{ rows: any[]; xTitle?: string }>()

const balancePoint = computed(() => {
  if (!props.rows.length) return null
  return props.rows.reduce((best, row) => (row.combined_fail_rate < best.combined_fail_rate ? row : best), props.rows[0])
})

const data = computed(() => [
  {
    type: 'scatter',
    mode: 'lines+markers',
    name: 'Hole-to-Hole',
    x: props.rows.map((row) => row.bin_center),
    y: props.rows.map((row) => row.hole_to_hole_fail_rate),
    line: { color: CATEGORICAL_PALETTE[5], width: 2 },
  },
  {
    type: 'scatter',
    mode: 'lines+markers',
    name: 'Ch.Hole Not Open',
    x: props.rows.map((row) => row.bin_center),
    y: props.rows.map((row) => row.not_open_fail_rate),
    line: { color: CATEGORICAL_PALETTE[0], width: 2 },
  },
  {
    type: 'scatter',
    mode: 'lines',
    name: 'Combined',
    x: props.rows.map((row) => row.bin_center),
    y: props.rows.map((row) => row.combined_fail_rate),
    line: { color: '#4b5563', width: 3 },
  },
])

const layout = computed(() => ({
  xaxis: { title: props.xTitle || 'FAB 관리 인자' },
  yaxis: { title: 'Fail rate', tickformat: '.1%' },
  legend: { orientation: 'h', y: -0.24 },
  annotations: balancePoint.value
    ? [
        {
          x: balancePoint.value.bin_center,
          y: balancePoint.value.combined_fail_rate,
          text: '★ 균형점',
          showarrow: true,
          arrowhead: 2,
          ax: 0,
          ay: -32,
          font: { color: '#4b5563', size: 12 },
        },
      ]
    : [],
}))
</script>
