<template>
  <section class="summary-band compact">
    <SummaryCard label="MAE" :value="fmt(metrics?.mae)" detail="Backtest" />
    <SummaryCard label="RMSE" :value="fmt(metrics?.rmse)" detail="Backtest" />
    <SummaryCard label="Bias" :value="fmt(metrics?.bias)" detail="Actual - Predicted" />
    <SummaryCard label="Hit rate" :value="pct(metrics?.high_risk_hit_rate)" detail="High-risk 적중" />
    <SummaryCard label="PI coverage" :value="pct(metrics?.prediction_interval_coverage)" detail="예측 범위 포함률" />
  </section>
</template>

<script setup lang="ts">
import SummaryCard from '../common/SummaryCard.vue'

defineProps<{ metrics: any }>()
const fmt = (value: number) => (value == null ? '-' : Number(value).toFixed(4))
const pct = (value: number) => (value == null ? '-' : `${(Number(value) * 100).toFixed(1)}%`)
</script>
