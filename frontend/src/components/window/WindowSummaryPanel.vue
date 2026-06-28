<template>
  <section class="summary-band">
    <SummaryCard label="분석 물량" :value="summary.waferText" :detail="`${summary.actualText} / ${summary.pendingText}`" />
    <SummaryCard label="High-side fail" :value="summary.failRateText" :detail="`Low-side ${summary.lowFailRateText}`" />
    <SummaryCard label="X-Y correlation" :value="summary.correlationText" :detail="`${summary.xParameter} -> ${summary.yMetric}`" />
    <SummaryCard label="Safe window" :value="summary.safeWindowText" detail="후보 범위" />
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
