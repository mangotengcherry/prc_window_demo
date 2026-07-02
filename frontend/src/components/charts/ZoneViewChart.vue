<template>
  <div class="zone-view-chart">
    <div class="zone-view-chart__pane">
      <PlotlyChart :data="data" :layout="layout" />
    </div>
    <div class="zone-view-chart__pane">
      <PlotlyChart :data="boxData" :layout="boxLayout" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import PlotlyChart from './PlotlyChart.vue'
import { CATEGORICAL_PALETTE } from '../../palette.ts'

const props = defineProps<{ rows: any[]; points?: any[]; xTitle?: string }>()
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

function erf(x: number): number {
  const sign = x < 0 ? -1 : 1
  const ax = Math.abs(x)
  const a1 = 0.254829592
  const a2 = -0.284496736
  const a3 = 1.421413741
  const a4 = -1.453152027
  const a5 = 1.061405429
  const p = 0.3275911
  const t = 1 / (1 + p * ax)
  const y = 1 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * Math.exp(-ax * ax)
  return sign * y
}

function normalCdf(z: number): number {
  return 0.5 * (1 + erf(z / Math.SQRT2))
}

// Wilson-Hilferty 근사 — chi-square 상단꼬리 p-value
function chiSquarePValue(x: number, df: number): number {
  if (x <= 0 || df <= 0) return 1
  const h = 2 / (9 * df)
  const z = (Math.pow(x / df, 1 / 3) - (1 - h)) / Math.sqrt(h)
  return Math.max(0, Math.min(1, 1 - normalCdf(z)))
}

function kruskalWallis(groups: number[][]): number | null {
  const k = groups.filter((g) => g.length >= 5).length
  if (k < 2) return null
  const entries: { value: number; group: number }[] = []
  groups.forEach((g, gi) => {
    if (g.length < 5) return
    g.forEach((value) => entries.push({ value, group: gi }))
  })
  const n = entries.length
  const sorted = [...entries].sort((a, b) => a.value - b.value)
  let tieSum = 0
  let i = 0
  const ranks: number[] = new Array(n)
  while (i < n) {
    let j = i
    while (j + 1 < n && sorted[j + 1].value === sorted[i].value) j++
    const avgRank = (i + j) / 2 + 1
    for (let m = i; m <= j; m++) ranks[m] = avgRank
    const t = j - i + 1
    tieSum += t * t * t - t
    i = j + 1
  }
  const rankSums = new Map<number, number>()
  const groupSizes = new Map<number, number>()
  sorted.forEach((item, idx) => {
    rankSums.set(item.group, (rankSums.get(item.group) || 0) + ranks[idx])
    groupSizes.set(item.group, (groupSizes.get(item.group) || 0) + 1)
  })
  let h = 0
  for (const [group, rankSum] of rankSums) {
    h += (rankSum * rankSum) / (groupSizes.get(group) || 1)
  }
  h = (12 / (n * (n + 1))) * h - 3 * (n + 1)
  const correction = 1 - tieSum / (n * n * n - n)
  if (correction > 0) h = h / correction
  return chiSquarePValue(h, rankSums.size - 1)
}

const zoneGroups = computed(() => {
  const map = new Map<string, number[]>()
  ;(props.points || []).forEach((point: any) => {
    if (point.zone == null || point.selected_bin_group_fail_rate == null) return
    const key = String(point.zone)
    if (!map.has(key)) map.set(key, [])
    map.get(key)?.push(point.selected_bin_group_fail_rate)
  })
  return map
})

const pValue = computed(() => kruskalWallis([...zoneGroups.value.values()]))

const boxData = computed(() =>
  [...zoneGroups.value.entries()].map(([zone, values]) => ({
    type: 'box',
    name: zone,
    y: values,
    marker: { color: palette[zone] || CATEGORICAL_PALETTE[0] },
    boxmean: true,
  })),
)

const boxLayout = computed(() => ({
  title: {
    text: pValue.value == null ? 'Zone별 fail rate 분포 (표본 부족으로 검정 생략)' : `Zone별 fail rate 분포 — Kruskal-Wallis p = ${pValue.value.toFixed(4)}${pValue.value < 0.05 ? ' (유의)' : ''}`,
    font: { size: 13 },
  },
  yaxis: { title: 'Fail rate', tickformat: '.1%' },
  showlegend: false,
}))
</script>

<style scoped>
.zone-view-chart {
  display: flex;
  gap: 12px;
  height: 100%;
  min-width: 0;
}

.zone-view-chart__pane {
  flex: 1;
  min-width: 0;
  height: 100%;
}
</style>
