<template>
  <el-dialog v-model="visible" title="Preset으로 저장" width="480px" @open="onOpen">
    <el-form label-position="top">
      <el-form-item label="저장 방식">
        <el-radio-group v-model="mode">
          <el-radio value="new">새 Preset</el-radio>
          <el-radio value="new-rev" :disabled="!currentPreset">기존 Preset에 새 Rev ({{ currentPreset?.name || '불러온 조건 없음' }})</el-radio>
        </el-radio-group>
      </el-form-item>
      <template v-if="mode === 'new'">
        <el-form-item label="폴더">
          <el-select v-model="folderId" placeholder="폴더 선택">
            <el-option v-for="folder in folders" :key="folder.id" :label="folder.name" :value="folder.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="이름">
          <el-input v-model="name" placeholder="예: ETCH" />
        </el-form-item>
        <el-form-item label="공유 범위">
          <el-segmented v-model="scope" :options="[{ label: '개인', value: 'personal' }, { label: '공유', value: 'shared' }]" />
        </el-form-item>
      </template>
      <el-form-item label="변경 메모">
        <el-input v-model="note" type="textarea" :rows="2" placeholder="예: ETCH recipe 변경 반영" />
      </el-form-item>
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
  folders: any[]
  currentPreset?: { id: string; name: string; folderId?: string } | null
}>()
const emit = defineEmits<{
  (e: 'save', payload: { mode: 'new' | 'new-rev'; folder_id?: string; name?: string; note: string; scope?: string }): void
}>()

const visible = defineModel<boolean>('visible', { default: false })

const mode = ref<'new' | 'new-rev'>('new')
const folderId = ref('')
const name = ref('')
const scope = ref('personal')
const note = ref('')

function onOpen() {
  mode.value = props.currentPreset ? 'new-rev' : 'new'
  folderId.value = props.folders[0]?.id || ''
  name.value = ''
  scope.value = 'personal'
  note.value = ''
}

const canSave = computed(() => {
  if (mode.value === 'new-rev') return Boolean(props.currentPreset)
  return Boolean(folderId.value && name.value.trim())
})

function save() {
  if (!canSave.value) return
  if (mode.value === 'new-rev') {
    emit('save', { mode: 'new-rev', note: note.value })
  } else {
    emit('save', { mode: 'new', folder_id: folderId.value, name: name.value.trim(), scope: scope.value, note: note.value })
  }
}
</script>
