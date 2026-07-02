<template>
  <div class="preset-tree-panel">
    <el-segmented v-model="presetStore.scopeFilter" :options="scopeOptions" class="mt-8" />
    <el-tree
      :data="treeData"
      node-key="id"
      :props="{ label: 'label', children: 'children' }"
      default-expand-all
      highlight-current
      class="mt-8"
      @node-click="handleNodeClick"
    >
      <template #default="{ data }">
        <span class="preset-tree-node">
          <span>{{ data.label }}</span>
          <el-tag v-if="data.type === 'revision' && data.scope === 'shared'" size="small" type="info">공유</el-tag>
          <el-dropdown v-if="data.type === 'revision'" trigger="click" @command="(cmd: string) => onCommand(cmd, data)">
            <el-icon class="preset-tree-node__more" @click.stop><MoreFilled /></el-icon>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="load">불러오기</el-dropdown-item>
                <el-dropdown-item command="new-rev" :disabled="data.owner !== me">이 조건으로 새 Rev 저장</el-dropdown-item>
                <el-dropdown-item command="duplicate">복제</el-dropdown-item>
                <el-dropdown-item command="toggle-scope" :disabled="data.owner !== me">
                  {{ data.scope === 'shared' ? '개인으로 전환' : '공유로 전환' }}
                </el-dropdown-item>
                <el-dropdown-item command="rename" :disabled="data.owner !== me">이름 변경</el-dropdown-item>
                <el-dropdown-item command="delete" :disabled="data.owner !== me" divided>삭제</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </span>
      </template>
    </el-tree>
    <el-button text :icon="FolderAdd" class="mt-8" @click="createFolder">+ 폴더</el-button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { FolderAdd, MoreFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { currentUser, usePresetStore } from '../../stores/presetStore'

const props = defineProps<{ hasUnsavedCriteria?: boolean }>()
const emit = defineEmits<{
  (e: 'load', criteria: any, info: { id: string; name: string; rev: number; folderName: string; scope: string; owner: string }): void
}>()

const presetStore = usePresetStore()
const me = currentUser()

const scopeOptions = [
  { label: '내 조건', value: 'personal' },
  { label: '공유', value: 'shared' },
  { label: '전체', value: 'all' },
]

function matchesScope(preset: any) {
  if (presetStore.scopeFilter === 'personal') return preset.owner === me
  if (presetStore.scopeFilter === 'shared') return preset.scope === 'shared'
  return true
}

const treeData = computed(() =>
  (presetStore.tree.folders || []).map((folder: any) => ({
    id: folder.id,
    label: folder.name,
    type: 'folder',
    children: (folder.presets || [])
      .filter(matchesScope)
      .flatMap((preset: any) =>
        preset.revisions.map((rev: any) => ({
          id: `${preset.id}:${rev.rev}`,
          label: `${preset.name} Rev${rev.rev}`,
          type: 'revision',
          presetId: preset.id,
          presetName: preset.name,
          folderId: folder.id,
          folderName: folder.name,
          rev: rev.rev,
          scope: preset.scope,
          owner: preset.owner,
          note: rev.note,
        })),
      ),
  })),
)

async function loadRevision(data: any) {
  if (props.hasUnsavedCriteria) {
    try {
      await ElMessageBox.confirm('현재 입력된 조건이 저장되지 않았습니다. 불러오면 대체됩니다. 계속할까요?', '조건 불러오기', {
        confirmButtonText: '불러오기',
        cancelButtonText: '취소',
        type: 'warning',
      })
    } catch {
      return
    }
  }
  const revision = await presetStore.fetchRevision(data.presetId, data.rev)
  presetStore.markLoaded({
    id: data.presetId,
    name: data.presetName,
    rev: data.rev,
    folderName: data.folderName,
    scope: data.scope,
    owner: data.owner,
  })
  emit('load', revision.criteria, {
    id: data.presetId,
    name: data.presetName,
    rev: data.rev,
    folderName: data.folderName,
    scope: data.scope,
    owner: data.owner,
  })
}

function handleNodeClick(data: any) {
  if (data.type === 'revision') loadRevision(data)
}

async function onCommand(command: string, data: any) {
  if (command === 'load') return loadRevision(data)
  if (command === 'new-rev') {
    const { value: note } = await ElMessageBox.prompt('새 Rev 메모를 입력하세요', '새 Rev 저장', { inputValue: '' })
    const revision = await presetStore.fetchRevision(data.presetId, data.rev)
    await presetStore.addRevision(data.presetId, { note: note || '', criteria: revision.criteria })
    ElMessage.success(`${data.presetName} 새 Rev가 저장되었습니다`)
    return
  }
  if (command === 'duplicate') {
    const { value: name } = await ElMessageBox.prompt('복제본 이름을 입력하세요', '조건 복제', { inputValue: `${data.presetName} 복사본` })
    await presetStore.duplicate(data.presetId, { name })
    ElMessage.success('복제되었습니다')
    return
  }
  if (command === 'toggle-scope') {
    await presetStore.setScope(data.presetId, data.scope === 'shared' ? 'personal' : 'shared')
    ElMessage.success('공유 범위가 변경되었습니다')
    return
  }
  if (command === 'rename') {
    const { value: name } = await ElMessageBox.prompt('새 이름을 입력하세요', '이름 변경', { inputValue: data.presetName })
    await presetStore.rename(data.presetId, name)
    return
  }
  if (command === 'delete') {
    await ElMessageBox.confirm(`${data.presetName}을(를) 삭제할까요?`, '삭제 확인', { type: 'warning' })
    await presetStore.remove(data.presetId)
    ElMessage.success('삭제되었습니다')
  }
}

async function createFolder() {
  const { value: name } = await ElMessageBox.prompt('폴더 이름을 입력하세요 (예: Ch.Hole)', '폴더 추가', { inputValue: '' })
  if (name) await presetStore.createFolder(name)
}
</script>
