<template>
  <div class="fab-history-form">
    <div class="form-grid">
      <el-form-item label="제품명">
        <el-select v-model="criteria.products" multiple filterable placeholder="전체 제품">
          <el-option v-for="item in analysis.metadata?.products || []" :key="item" :label="item" :value="item" />
        </el-select>
      </el-form-item>
    </div>
    <div class="check-row">
      <el-checkbox v-model="criteria.exclude_rework">Rework 제외</el-checkbox>
      <el-checkbox v-model="criteria.exclude_engineering_lot">Engineering lot 제외</el-checkbox>
      <el-checkbox v-model="criteria.exclude_abnormal_route">Abnormal route 제외</el-checkbox>
    </div>

    <template v-for="(condition, index) in criteria.step_conditions" :key="index">
      <div v-if="expandedIndex !== index" class="fab-step-summary" @click="expandedIndex = index">
        <span>{{ summaryText(condition, index) }}</span>
        <el-icon><EditPen /></el-icon>
      </div>
      <FabStepConditionCard
        v-else
        v-model:condition="criteria.step_conditions[index]"
        :index="index"
        :is-primary="isPrimary(condition)"
        :removable="criteria.step_conditions.length > 1"
        :used-steps="usedStepsExcluding(index)"
        :error="blockError(condition)"
        @remove="removeBlock(index)"
        @set-primary="setPrimary(condition)"
        @valid-change="(valid) => (validity[index] = valid)"
      />
    </template>

    <div class="join-actions">
      <el-button
        :icon="Plus"
        plain
        :disabled="!canAddBlock"
        @click="addBlock"
      >+ 다른 공정 조건 추가 (join)</el-button>
      <p v-if="joinHint" class="join-hint">{{ joinHint }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { EditPen, Plus } from '@element-plus/icons-vue'
import FabStepConditionCard from './FabStepConditionCard.vue'
import { useAnalysisSetStore } from '../../stores/analysisSetStore'

const props = defineProps<{
  error?: { stage: string; message: string } | null
}>()

const criteria = defineModel<any>('criteria', { required: true })
const analysis = useAnalysisSetStore()

const expandedIndex = ref(criteria.value.step_conditions.length - 1)
const validity = reactive<Record<number, boolean>>({})

function isPrimary(condition: any) {
  if (criteria.value.primary_step) return criteria.value.primary_step === condition.fab_step
  return criteria.value.step_conditions[0] === condition
}

function setPrimary(condition: any) {
  criteria.value.primary_step = condition.fab_step
}

function usedStepsExcluding(index: number) {
  return criteria.value.step_conditions.filter((_: any, i: number) => i !== index).map((c: any) => c.fab_step)
}

function blockValid(condition: any, index: number) {
  return Boolean(condition.fab_step && condition.date_range?.start && condition.date_range?.end && validity[index] !== false)
}

const lastIndex = computed(() => criteria.value.step_conditions.length - 1)
const canAddBlock = computed(
  () => criteria.value.step_conditions.length < 3 && blockValid(criteria.value.step_conditions[lastIndex.value], lastIndex.value),
)
const joinHint = computed(() => {
  const last = criteria.value.step_conditions[lastIndex.value]
  if (canAddBlock.value) return `${last.fab_step} 조건 완료 — 다른 공정을 join 하시겠습니까?`
  return ''
})

function summaryText(condition: any, index: number) {
  const range = condition.date_range?.start && condition.date_range?.end
    ? `${condition.date_range.start} ~ ${condition.date_range.end}`
    : '기간 미설정'
  const filterCount = condition.filter_expression?.trim() ? '필터 1건' : '필터 없음'
  return `공정 ${index + 1} · ${condition.fab_step || '미선택'} · ${range} · ${filterCount}`
}

function addBlock() {
  criteria.value.step_conditions.push({ fab_step: '', date_range: { start: null, end: null }, filter_expression: '' })
  expandedIndex.value = criteria.value.step_conditions.length - 1
}

function removeBlock(index: number) {
  const removed = criteria.value.step_conditions[index]
  criteria.value.step_conditions.splice(index, 1)
  if (criteria.value.primary_step === removed.fab_step) criteria.value.primary_step = null
  expandedIndex.value = criteria.value.step_conditions.length - 1
}

function blockError(condition: any) {
  if (props.error?.stage === `fab_filter:${condition.fab_step}`) return props.error
  return null
}

watch(
  () => criteria.value.step_conditions.length,
  (length) => {
    if (expandedIndex.value > length - 1) expandedIndex.value = length - 1
  },
)
</script>
