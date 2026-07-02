<template>
  <PlotlyChart :data="data" :layout="layout" @point-click="onClick" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import PlotlyChart from './PlotlyChart.vue'

const props = defineProps<{ rows: any[] }>()
const emit = defineEmits<{ (event: 'bar-click', binId: string): void }>()

const data = computed(() => [
  {
    type: 'bar',
    name: '평균 fail rate',
    x: props.rows.map((row) => row.bin_id),
    y: props.rows.map((row) => row.mean_fail_rate),
    customdata: props.rows,
    marker: { color: props.rows.map((row) => (row.in_selected_group ? '#2563eb' : '#94a3b8')) },
    hovertemplate: '%{x}<br>fail rate %{y:.2%}<extra></extra>',
  },
  {
    type: 'scatter',
    mode: 'lines+markers',
    name: '누적 %',
    x: props.rows.map((row) => row.bin_id),
    y: props.rows.map((row) => row.cum_pct),
    yaxis: 'y2',
    line: { color: '#dc2626', width: 2 },
    hovertemplate: '%{x}<br>누적 %{y:.1%}<extra></extra>',
  },
])

const layout = computed(() => ({
  xaxis: { title: 'BIN', tickangle: -45 },
  yaxis: { title: '평균 fail rate', tickformat: '.1%' },
  yaxis2: { title: '누적 기여율', overlaying: 'y', side: 'right', tickformat: '.0%', range: [0, 1] },
  legend: { orientation: 'h', y: -0.3 },
}))

function onClick(point: any) {
  if (point?.bin_id) emit('bar-click', point.bin_id)
}
</script>
