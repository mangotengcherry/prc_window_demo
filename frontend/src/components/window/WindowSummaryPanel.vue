<template>
  <section class="summary-band">
    <SummaryCard label="분석 물량" :value="summary.waferText" :detail="`${summary.actualText} / ${summary.pendingText}`" />
    <SummaryCard label="High-side fail" :value="summary.failRateText" :detail="`Low-side ${summary.lowFailRateText}`" />
    <SummaryCard label="X-Y correlation" :value="summary.correlationText" :detail="`${summary.xParameter} -> ${summary.yMetric} (${summary.correlationSampleText})`" />
    <SummaryCard label="Safe window" :value="summary.safeWindowText" detail="후보 범위" />
    <SummaryCard label="Safe window 점유율" :value="summary.safeWindowOccupancyText" detail="Window 안에 있는 wafer 비율" />
    <SummaryCard label="최근 30일 fail 추세" :value="summary.recentTrendText" detail="직전 30일 대비" />
    <div class="candidate-callout">
      <span>판정 후보</span>
      <strong>{{ summary.primaryCandidate }}</strong>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import SummaryCard from '../common/SummaryCard.vue'
import { summarizeWindowReview } from '../../workbenchSummary.js'

const props = defineProps<{ review: any }>()
const summary = computed(() => summarizeWindowReview(props.review))
</script>
