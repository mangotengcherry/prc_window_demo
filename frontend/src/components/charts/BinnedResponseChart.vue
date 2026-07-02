<template>
  <PlotlyChart :data="data" :layout="layout" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import PlotlyChart from './PlotlyChart.vue'

const props = defineProps<{ rows: any[]; xTitle?: string }>()

const LOW_SAMPLE_THRESHOLD = 15

const segments = computed(() => {
  const rows = props.rows
  const list = []
  for (let i = 0; i < rows.length - 1; i++) {
    const low = rows[i].wafer_count < LOW_SAMPLE_THRESHOLD || rows[i + 1].wafer_count < LOW_SAMPLE_THRESHOLD
    list.push({
      type: 'scatter',
      mode: 'lines',
      x: [rows[i].bin_center, rows[i + 1].bin_center],
      y: [rows[i].fail_rate, rows[i + 1].fail_rate],
      line: { color: low ? '#94a3b8' : '#2563eb', width: 2, dash: low ? 'dot' : 'solid' },
      showlegend: false,
      hoverinfo: 'skip',
    })
  }
  return list
})

const data = computed(() => [
  ...segments.value,
  {
    type: 'scatter',
    mode: 'markers',
    name: props.rows[0]?.metric || 'Binned response',
    x: props.rows.map((row) => row.bin_center),
    y: props.rows.map((row) => row.fail_rate),
    error_y: { type: 'data', array: props.rows.map((row) => row.stderr || 0), visible: true },
    marker: {
      size: props.rows.map((row) => Math.max(6, Math.min(18, row.wafer_count / 12))),
      color: props.rows.map((row) => (row.wafer_count < LOW_SAMPLE_THRESHOLD ? '#94a3b8' : '#2563eb')),
      opacity: props.rows.map((row) => (row.wafer_count < LOW_SAMPLE_THRESHOLD ? 0.55 : 1)),
    },
    text: props.rows.map((row) => `${row.wafer_count}매 wafer${row.wafer_count < LOW_SAMPLE_THRESHOLD ? ' (저표본)' : ''}`),
  },
  {
    type: 'bar',
    name: 'wafer 수',
    x: props.rows.map((row) => row.bin_center),
    y: props.rows.map((row) => row.wafer_count),
    yaxis: 'y2',
    marker: { color: 'rgba(148,163,184,0.35)' },
    showlegend: false,
  },
])

const layout = computed(() => ({
  xaxis: { title: props.xTitle || 'FAB 관리 인자 bin' },
  yaxis: { title: '평균 fail rate', tickformat: '.1%' },
  yaxis2: { title: 'wafer 수', overlaying: 'y', side: 'right', rangemode: 'tozero', showgrid: false },
}))
</script>
