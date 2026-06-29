<template>
  <PlotlyChart :data="data" :layout="layout" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import PlotlyChart from './PlotlyChart.vue'

const props = defineProps<{ rows: any[]; xTitle?: string }>()

const data = computed(() => [{
  type: 'scatter',
  mode: 'lines+markers',
  name: props.rows[0]?.metric || 'Binned response',
  x: props.rows.map((row) => row.bin_center),
  y: props.rows.map((row) => row.fail_rate),
  error_y: { type: 'data', array: props.rows.map((row) => row.stderr || 0), visible: true },
  line: { color: '#2563eb', width: 2 },
  marker: { size: props.rows.map((row) => Math.max(6, Math.min(18, row.wafer_count / 12))) },
  text: props.rows.map((row) => `${row.wafer_count}매 wafer`),
}])

const layout = computed(() => ({
  xaxis: { title: props.xTitle || 'FAB 관리 인자 bin' },
  yaxis: { title: '평균 fail rate', tickformat: '.1%' },
}))
</script>
