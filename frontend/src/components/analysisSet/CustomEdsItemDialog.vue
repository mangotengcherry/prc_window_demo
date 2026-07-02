<template>
  <el-dialog v-model="visible" title="커스텀 EDS 아이템 만들기" width="540px" @close="reset">
    <el-form label-position="top">
      <el-form-item label="이름 (영숫자와 _, 2~30자)">
        <el-input v-model="name" placeholder="예: H2H_NET" />
        <p v-if="serverError" class="custom-eds-dialog__error">{{ serverError }}</p>
        <p v-else-if="name && !nameValid" class="custom-eds-dialog__error">영숫자와 밑줄(_)만 2~30자로 입력하세요</p>
      </el-form-item>
      <el-form-item label="더할 아이템 (+)">
        <el-select v-model="plusItems" multiple filterable placeholder="아이템 선택">
          <el-option v-for="item in items" :key="item" :label="item" :value="item" />
        </el-select>
      </el-form-item>
      <el-form-item label="뺄 아이템 (−)">
        <el-select v-model="minusItems" multiple filterable placeholder="아이템 선택">
          <el-option v-for="item in items" :key="item" :label="item" :value="item" />
        </el-select>
      </el-form-item>
      <p class="custom-eds-dialog__formula">{{ formulaPreview }}</p>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">취소</el-button>
      <el-button type="primary" :disabled="!canSave" @click="save">저장</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

const props = defineProps<{
  category: 'BIN' | 'MSR'
  items: string[]
  serverError?: string
}>()
const emit = defineEmits<{ (e: 'save', payload: { name: string; category: string; terms: { item: string; sign: 1 | -1 }[] }): void }>()

const visible = defineModel<boolean>('visible', { default: false })

const name = ref('')
const plusItems = ref<string[]>([])
const minusItems = ref<string[]>([])

const nameValid = computed(() => /^[A-Za-z0-9_]{2,30}$/.test(name.value))
const terms = computed(() => [
  ...plusItems.value.map((item) => ({ item, sign: 1 as const })),
  ...minusItems.value.map((item) => ({ item, sign: -1 as const })),
])
const formulaPreview = computed(() => {
  if (!terms.value.length) return `${name.value || '이름'} = (아이템을 선택하세요)`
  const body = terms.value.map((term, index) => (index === 0 ? term.item : `${term.sign > 0 ? '+' : '−'} ${term.item}`)).join(' ')
  return `${name.value || '이름'} = ${body}`
})
const canSave = computed(() => nameValid.value && terms.value.length >= 2)

function reset() {
  name.value = ''
  plusItems.value = []
  minusItems.value = []
}

function save() {
  if (!canSave.value) return
  emit('save', { name: name.value, category: props.category, terms: terms.value })
}

defineExpose({ reset })
</script>
