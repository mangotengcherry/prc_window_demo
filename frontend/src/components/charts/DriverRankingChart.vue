<template>
  <div class="driver-ranking-chart">
    <p class="driver-ranking-chart__caption">상관은 인과가 아님 — 후보 선별용</p>
    <div class="driver-ranking-chart__plot">
      <PlotlyChart :data="data" :layout="layout" @point-click="onClick" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import PlotlyChart from './PlotlyChart.vue'
import { CATEGORICAL_PALETTE } from '../../palette.ts'

const props = defineProps<{ rows: any[] }>()
const emit = defineEmits<{ (event: 'bar-click', parameter: string): void }>()

const sorted = computed(() => [...props.rows].sort((a, b) => a.abs_corr - b.abs_corr))

const data = computed(() => [
  {
    type: 'bar',
    orientation: 'h',
    x: sorted.value.map((row) => row.abs_corr),
    y: sorted.value.map((row) => row.parameter),
    customdata: sorted.value,
    marker: { color: sorted.value.map((row) => (row.corr >= 0 ? CATEGORICAL_PALETTE[5] : CATEGORICAL_PALETTE[0])) },
    text: sorted.value.map((row) => `r=${row.corr} (n=${row.n})`),
    textposition: 'outside',
    hovertemplate: '%{y}<br>|r|=%{x:.3f}<extra></extra>',
  },
])

const layout = computed(() => ({
  xaxis: { title: '|Pearson r|', range: [0, 1] },
  yaxis: { automargin: true },
  margin: { l: 140, r: 24, t: 26, b: 46 },
}))

function onClick(point: any) {
  if (point?.parameter) emit('bar-click', point.parameter)
}
</script>

<style scoped>
.driver-ranking-chart {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.driver-ranking-chart__caption {
  margin: 0 0 6px;
  color: #64748b;
  font-size: 12px;
}

.driver-ranking-chart__plot {
  flex: 1;
  min-height: 0;
}
</style>
