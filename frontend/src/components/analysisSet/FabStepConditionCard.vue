<template>
  <div class="fab-step-card">
    <div class="fab-step-card__head">
      <span class="fab-step-card__title">공정 {{ index + 1 }}</span>
      <el-radio :model-value="isPrimary" :value="true" @change="$emit('set-primary')">기준공정</el-radio>
      <el-button v-if="removable" text :icon="Close" @click="$emit('remove')">제거</el-button>
    </div>
    <div class="form-grid">
      <el-form-item label="공정">
        <el-select v-model="condition.fab_step" filterable placeholder="공정 선택">
          <el-option-group v-for="module in processModules" :key="module.name" :label="module.name">
            <el-option
              v-for="step in module.fab_steps"
              :key="step.step_id"
              :label="`${step.label} (${step.step_id})`"
              :value="step.step_id"
              :disabled="usedSteps.includes(step.step_id)"
            />
          </el-option-group>
        </el-select>
      </el-form-item>
      <el-form-item label="진행기간">
        <el-date-picker
          v-model="dateRangeModel"
          type="daterange"
          value-format="YYYY-MM-DD"
          start-placeholder="시작일"
          end-placeholder="종료일"
        />
      </el-form-item>
    </div>
    <el-form-item label="FAB 필터식 (Spotfire/SQL)">
      <ExpressionEditor v-model="condition.filter_expression" context="fab" @valid-change="onExprValid" />
    </el-form-item>
    <el-alert v-if="error" :title="error.message" type="error" show-icon :closable="false" class="mt-8" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Close } from '@element-plus/icons-vue'
import ExpressionEditor from './ExpressionEditor.vue'
import { useAnalysisSetStore } from '../../stores/analysisSetStore'

defineProps<{
  index: number
  isPrimary: boolean
  removable: boolean
  usedSteps: string[]
  error?: { stage: string; message: string } | null
}>()
const emit = defineEmits<{
  (e: 'remove'): void
  (e: 'set-primary'): void
  (e: 'valid-change', valid: boolean): void
}>()

const condition = defineModel<any>('condition', { required: true })
const analysis = useAnalysisSetStore()
const processModules = computed(() => analysis.metadata?.process_modules || [])

const dateRangeModel = computed({
  get: () => (condition.value.date_range?.start && condition.value.date_range?.end
    ? [condition.value.date_range.start, condition.value.date_range.end]
    : null),
  set: (value: [string, string] | null) => {
    condition.value.date_range = { start: value?.[0] ?? null, end: value?.[1] ?? null }
  },
})

function onExprValid(valid: boolean) {
  emit('valid-change', valid)
}
</script>
