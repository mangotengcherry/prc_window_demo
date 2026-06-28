<template>
  <PlotlyChart :data="data" :layout="layout" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import PlotlyChart from './PlotlyChart.vue'

const props = defineProps<{ rows: any[] }>()

const data = computed(() => {
  const xs = [...new Set(props.rows.map((row) => row.x_bin))]
  const ys = [...new Set(props.rows.map((row) => row.y_bin))]
  const z = ys.map((y) => xs.map((x) => props.rows.find((row) => row.x_bin === x && row.y_bin === y)?.fail_rate ?? null))
  return [{
    type: 'heatmap',
    x: xs,
    y: ys,
    z,
    colorscale: 'YlOrRd',
    hovertemplate: 'X %{x}<br>Y %{y}<br>Fail %{z:.2%}<extra></extra>',
  }]
})

const layout = computed(() => ({
  xaxis: { title: props.rows[0]?.x_parameter || 'FAB 관리 인자 A' },
  yaxis: { title: props.rows[0]?.y_parameter || 'FAB 관리 인자 B' },
}))
</script>
