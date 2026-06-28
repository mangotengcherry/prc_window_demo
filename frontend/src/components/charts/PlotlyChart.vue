<template>
  <div ref="chartEl" class="plotly-chart" />
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import Plotly from 'plotly.js-dist-min'

const props = withDefaults(defineProps<{
  data: any[]
  layout?: Record<string, any>
  config?: Record<string, any>
}>(), {
  layout: () => ({}),
  config: () => ({}),
})

const emit = defineEmits<{
  (event: 'point-click', point: any): void
  (event: 'points-selected', points: any[]): void
}>()

const chartEl = ref<HTMLElement | null>(null)

function draw() {
  if (!chartEl.value) return
  Plotly.react(chartEl.value, props.data, {
    autosize: true,
    margin: { l: 52, r: 24, t: 26, b: 46 },
    paper_bgcolor: 'rgba(255,255,255,0)',
    plot_bgcolor: 'rgba(255,255,255,0)',
    font: { family: 'Inter, system-ui, sans-serif', color: '#233043', size: 12 },
    hovermode: 'closest',
    ...props.layout,
  }, { displaylogo: false, responsive: true, ...props.config })
}

function payloadFromEvent(event: any) {
  return (event?.points || []).map((point: any) => point.customdata ?? point.data?.customdata?.[point.pointIndex])
}

onMounted(() => {
  draw()
  if (!chartEl.value) return
  chartEl.value.on('plotly_click', (event: any) => emit('point-click', payloadFromEvent(event)[0]))
  chartEl.value.on('plotly_selected', (event: any) => emit('points-selected', payloadFromEvent(event)))
})

watch(() => [props.data, props.layout], draw, { deep: true })

onBeforeUnmount(() => {
  if (chartEl.value) Plotly.purge(chartEl.value)
})
</script>
