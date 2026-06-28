<template>
  <section class="summary-card">
    <div class="summary-card__label">{{ label }}</div>
    <div class="summary-card__value">{{ value }}</div>
    <div v-if="detail" class="summary-card__detail">{{ detail }}</div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  label: string
  value: string | number
  detail?: string
}>()
</script>
