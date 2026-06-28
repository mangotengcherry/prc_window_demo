<template>
  <PlotlyChart :data="data" :layout="layout" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import PlotlyChart from './PlotlyChart.vue'

const props = defineProps<{ trend: any }>()

const data = computed(() => [
  {
    type: 'scatter',
    mode: 'lines+markers',
    name: 'Actual EDS',
    x: props.trend?.actual?.map((row: any) => row.date) || [],
    y: props.trend?.actual?.map((row: any) => row.actual_fail_rate) || [],
    line: { color: '#111827', width: 2 },
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

const layout = {
  xaxis: { title: '일자' },
  yaxis: { title: 'Actual fail rate', tickformat: '.1%' },
  yaxis2: { title: 'Pending wafer 수', overlaying: 'y', side: 'right', rangemode: 'tozero' },
  legend: { orientation: 'h', y: -0.24 },
}
</script>
