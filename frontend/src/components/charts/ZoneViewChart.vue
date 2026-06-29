<template>
  <PlotlyChart :data="data" :layout="layout" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import PlotlyChart from './PlotlyChart.vue'

const props = defineProps<{ rows: any[]; xTitle?: string }>()
const palette: Record<string, string> = { center: '#2563eb', middle: '#16a34a', ring: '#ea580c', edge: '#be123c' }

const data = computed(() => [...new Set(props.rows.map((row) => row.zone))].map((zone) => {
  const rows = props.rows.filter((row) => row.zone === zone)
  return {
    type: 'scatter',
    mode: 'lines+markers',
    name: zone,
    x: rows.map((row) => row.bin_center),
    y: rows.map((row) => row.fail_rate),
    line: { color: palette[String(zone)] || '#4b5563', width: 2 },
  }
}))

const layout = computed(() => ({
  xaxis: { title: props.xTitle || 'FAB 관리 인자 bin' },
  yaxis: { title: 'Zone별 fail rate', tickformat: '.1%' },
  legend: { orientation: 'h', y: -0.24 },
}))
</script>
