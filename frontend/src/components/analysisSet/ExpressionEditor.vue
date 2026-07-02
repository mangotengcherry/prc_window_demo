<template>
  <div class="expr-editor">
    <div class="expr-editor__toolbar">
      <el-popover trigger="click" width="240" placement="bottom-start">
        <template #reference>
          <el-button size="small" text>컬럼 삽입 ▾</el-button>
        </template>
        <div class="expr-editor__columns">
          <el-button v-for="col in columns" :key="col" size="small" text @click="insertColumn(col)">{{ col }}</el-button>
        </div>
      </el-popover>
      <span v-if="statusText" class="expr-editor__status" :class="statusClass">
        <el-icon v-if="checking"><Loading /></el-icon>
        <el-icon v-else-if="isValid === true"><CircleCheck /></el-icon>
        <el-icon v-else-if="isValid === false"><CircleClose /></el-icon>
        {{ statusText }}
      </span>
    </div>
    <el-input
      ref="inputRef"
      v-model="model"
      type="textarea"
      :rows="2"
      :placeholder="placeholder ?? defaultPlaceholder"
      @input="scheduleValidate"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { CircleCheck, CircleClose, Loading } from '@element-plus/icons-vue'
import { validateExpression } from '../../api/analysisApi'
import { useAnalysisSetStore } from '../../stores/analysisSetStore'

const props = withDefaults(
  defineProps<{
    context: 'fab' | 'eds'
    mode?: 'filter' | 'column'
    placeholder?: string
  }>(),
  { mode: 'filter' },
)

const emit = defineEmits<{ (e: 'valid-change', valid: boolean): void }>()
const model = defineModel<string>({ default: '' })

const analysis = useAnalysisSetStore()
const inputRef = ref<any>(null)
const checking = ref(false)
const isValid = ref<boolean | null>(null)
const errorMessage = ref('')
let timer: ReturnType<typeof setTimeout> | null = null

const defaultPlaceholder = 'case when [PPID] != "TT_TEST" then ... — Spotfire/SQL 문법 모두 지원'

const extraColumns = computed(() => (props.context === 'eds' ? ['value', 'part_id', 'eds_step', 'test_time'] : []))
const columns = computed(() => [
  ...extraColumns.value,
  ...(analysis.metadata?.categorical_columns || []),
  ...(analysis.metadata?.numeric_columns || []),
])

const statusText = computed(() => {
  if (checking.value) return '확인 중'
  if (isValid.value === true) return '유효'
  if (isValid.value === false) return errorMessage.value
  return ''
})
const statusClass = computed(() => ({
  'is-valid': isValid.value === true,
  'is-invalid': isValid.value === false,
}))

function insertColumn(col: string) {
  const textarea = inputRef.value?.textarea as HTMLTextAreaElement | undefined
  const token = `[${col}]`
  const current = model.value || ''
  if (!textarea) {
    model.value = current + token
    scheduleValidate()
    return
  }
  const start = textarea.selectionStart ?? current.length
  const end = textarea.selectionEnd ?? current.length
  model.value = current.slice(0, start) + token + current.slice(end)
  scheduleValidate()
  requestAnimationFrame(() => {
    textarea.focus()
    const pos = start + token.length
    textarea.setSelectionRange(pos, pos)
  })
}

function scheduleValidate() {
  if (timer) clearTimeout(timer)
  if (!model.value?.trim()) {
    isValid.value = null
    errorMessage.value = ''
    emit('valid-change', true)
    return
  }
  timer = setTimeout(runValidate, 500)
}

async function runValidate() {
  checking.value = true
  try {
    const result = await validateExpression({ expression: model.value, mode: props.mode, context: props.context })
    isValid.value = result.valid
    errorMessage.value = result.valid ? '' : result.error
    emit('valid-change', result.valid)
  } catch {
    isValid.value = false
    errorMessage.value = '검증 요청 실패'
    emit('valid-change', false)
  } finally {
    checking.value = false
  }
}

watch(() => model.value, scheduleValidate, { immediate: true })

onBeforeUnmount(() => {
  if (timer) clearTimeout(timer)
})
</script>
