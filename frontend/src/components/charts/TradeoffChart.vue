<template>
  <PlotlyChart :data="data" :layout="layout" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import PlotlyChart from './PlotlyChart.vue'

const props = defineProps<{ rows: any[]; xTitle?: string }>()

const data = computed(() => [
  {
    type: 'scatter',
    mode: 'lines+markers',
    name: 'Hole-to-Hole',
    x: props.rows.map((row) => row.bin_center),
    y: props.rows.map((row) => row.hole_to_hole_fail_rate),
    line: { color: '#dc2626', width: 2 },
  },
  {
    type: 'scatter',
    mode: 'lines+markers',
    name: 'Ch.Hole Not Open',
    x: props.rows.map((row) => row.bin_center),
    y: props.rows.map((row) => row.not_open_fail_rate),
    line: { color: '#2563eb', width: 2 },
  },
])

const layout = computed(() => ({
  xaxis: { title: props.xTitle || 'FAB 관리 인자' },
  yaxis: { title: 'Fail rate', tickformat: '.1%' },
  legend: { orientation: 'h', y: -0.24 },
}))
</script>
