<template>
  <el-dialog v-model="visible" title="파생 컬럼 추가" width="520px" @close="reset">
    <el-form label-position="top">
      <el-form-item label="이름 (영숫자와 _)">
        <el-input v-model="name" placeholder="예: cd_band" />
        <p v-if="name && !nameValid" class="custom-eds-dialog__error">영숫자와 밑줄(_)만 사용할 수 있습니다</p>
        <p v-else-if="name && duplicated" class="custom-eds-dialog__error">이미 존재하는 컬럼과 이름이 겹칩니다</p>
      </el-form-item>
      <el-form-item label="식">
        <ExpressionEditor v-model="expression" context="eds" mode="column" placeholder="예: case when [value] >= 53 then 'high' else 'low' end" @valid-change="(valid) => (exprValid = valid)" />
      </el-form-item>
      <p class="custom-eds-dialog__formula">{{ name || '이름' }} = {{ expression || '식을 입력하세요' }}</p>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">취소</el-button>
      <el-button type="primary" :disabled="!canSave" @click="save">저장</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import ExpressionEditor from './ExpressionEditor.vue'

const props = defineProps<{ existingNames: string[] }>()
const emit = defineEmits<{ (e: 'save', payload: { name: string; expression: string }): void }>()

const visible = defineModel<boolean>('visible', { default: false })

const name = ref('')
const expression = ref('')
const exprValid = ref(true)

const nameValid = computed(() => /^[A-Za-z0-9_]+$/.test(name.value))
const duplicated = computed(() => props.existingNames.includes(name.value))
const canSave = computed(() => nameValid.value && !duplicated.value && expression.value.trim() && exprValid.value)

function reset() {
  name.value = ''
  expression.value = ''
  exprValid.value = true
}

function save() {
  if (!canSave.value) return
  emit('save', { name: name.value, expression: expression.value })
}
</script>
