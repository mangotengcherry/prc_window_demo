<template>
  <div class="analysis-set-layout">
    <PresetTree @load="onPresetLoad" />

    <section class="analysis-set-main">
      <div v-if="presetStore.loadedPreset" class="preset-load-badge" :class="{ 'is-dirty': presetStore.dirty }">
        {{ presetStore.loadedPreset.folderName }} / {{ presetStore.loadedPreset.name }} Rev{{ presetStore.loadedPreset.rev }} 불러옴{{ presetStore.dirty ? ' — 수정됨 *' : '' }}
      </div>

      <FilterPanel title="① FAB 진행 이력 기반" subtitle="제품 · 공정 · 진행기간 · 필터식으로 FAB 물량을 정의합니다. 최대 3개 공정을 join(교집합)할 수 있습니다.">
        <template #actions>
          <el-button plain @click="fillSample">예시 데이터로 미리보기</el-button>
          <el-button :icon="Refresh" plain @click="resetSynthetic">Mock data 재생성</el-button>
        </template>
        <FabHistoryForm v-model:criteria="store.criteria.fab" :error="fabError" />
      </FilterPanel>

      <FilterPanel title="② EDS 아이템 기반" subtitle="BIN/MSR 아이템 · 테스트기간 · part_id로 EDS 값을 정의합니다.">
        <template #actions>
          <el-switch v-model="edsEnabled" active-text="사용" inactive-text="FAB만" />
        </template>
        <EdsItemForm v-if="edsEnabled" v-model:criteria="edsCriteria" :error="edsError" />
        <p v-else class="report-note">EDS 조건 없이 FAB 물량만으로 조회합니다.</p>
      </FilterPanel>

      <div class="form-actions">
        <el-tooltip v-if="!fabValid" content="제품 · 공정 · 진행기간을 모두 입력해야 조회할 수 있습니다">
          <span><el-button type="primary" disabled>물량 조회 →</el-button></span>
        </el-tooltip>
        <el-button v-else type="primary" :loading="store.previewLoading" @click="runQuery">물량 조회 →</el-button>
      </div>
    </section>

    <aside class="analysis-set-preview">
      <FilterPanel title="선정 물량 요약" subtitle="FAB/EDS 조건으로 정의된 물량의 시계열 scatter 미리보기입니다.">
        <SelectionPreview v-model:chart="store.criteria.chart" :preview="store.preview" :loading="store.previewLoading" />
        <div class="form-actions mt-8">
          <el-button @click="savePresetVisible = true">Preset으로 저장(Rev)</el-button>
        </div>
        <div class="form-actions mt-8">
          <el-input v-model="analysisSetName" placeholder="Analysis Set 이름" />
          <el-button :icon="Plus" type="primary" @click="saveAnalysisSet">Analysis Set 저장</el-button>
        </div>
      </FilterPanel>

      <FilterPanel title="저장된 Analysis Set" subtitle="Window Review와 Pending 예측에 사용할 분석 물량을 선택합니다.">
        <div v-if="selected" class="summary-band compact">
          <SummaryCard label="Lot 수" :value="selected.metrics.lot_count" />
          <SummaryCard label="Wafer 수" :value="selected.metrics.wafer_count" />
          <SummaryCard label="FAB coverage" :value="pct(selected.metrics.fab_coverage)" />
          <SummaryCard label="EDS actual" :value="pct(selected.metrics.eds_actual_coverage)" />
        </div>
        <el-table :data="store.analysisSets" size="small" highlight-current-row @current-change="selectSet">
          <el-table-column prop="id" label="ID" width="78" />
          <el-table-column prop="name" label="이름" min-width="150" />
          <el-table-column prop="metrics.wafer_count" label="Wafer" width="90" />
          <el-table-column prop="metrics.eds_pending_count" label="Pending" width="90" />
        </el-table>
      </FilterPanel>
    </aside>

    <SavePresetDialog
      v-model:visible="savePresetVisible"
      :folders="presetStore.tree.folders || []"
      :current-preset="presetStore.loadedPreset ? { id: presetStore.loadedPreset.id, name: presetStore.loadedPreset.name } : null"
      @save="onSavePreset"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Plus, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import FilterPanel from '../components/common/FilterPanel.vue'
import SummaryCard from '../components/common/SummaryCard.vue'
import PresetTree from '../components/analysisSet/PresetTree.vue'
import FabHistoryForm from '../components/analysisSet/FabHistoryForm.vue'
import EdsItemForm from '../components/analysisSet/EdsItemForm.vue'
import SelectionPreview from '../components/analysisSet/SelectionPreview.vue'
import SavePresetDialog from '../components/analysisSet/SavePresetDialog.vue'
import { defaultChartState, defaultEdsCriteria, useAnalysisSetStore } from '../stores/analysisSetStore'
import { usePresetStore } from '../stores/presetStore'
import { useBinGroupStore } from '../stores/binGroupStore'
import { useConditionRuleStore } from '../stores/conditionRuleStore'

const store = useAnalysisSetStore()
const presetStore = usePresetStore()
const binGroups = useBinGroupStore()
const conditionRules = useConditionRuleStore()

const analysisSetName = ref('Ch.Hole CD window review')
const savePresetVisible = ref(false)
const selected = computed(() => store.selectedAnalysisSet)

const edsEnabled = computed({
  get: () => store.criteria.eds !== null,
  set: (value: boolean) => {
    store.criteria.eds = value ? store.criteria.eds || defaultEdsCriteria() : null
  },
})
const edsCriteria = computed(() => store.criteria.eds || defaultEdsCriteria())

const fabValid = computed(() => {
  const fab = store.criteria.fab
  return fab.products.length > 0 && fab.step_conditions.every((c: any) => c.fab_step && c.date_range?.start && c.date_range?.end)
})

const previewError = computed(() => store.preview?.error || null)
const fabError = computed(() => (previewError.value?.stage?.startsWith('fab_filter:') ? previewError.value : null))
const edsError = computed(() => (['eds_items', 'eds_filter'].includes(previewError.value?.stage) ? previewError.value : null))

function pct(value: number) {
  return `${(Number(value || 0) * 100).toFixed(1)}%`
}

function selectSet(row: any) {
  if (row?.id) store.selectedAnalysisSetId = row.id
}

async function runQuery() {
  await store.runPreview()
}

async function saveAnalysisSet() {
  const item = await store.createFromCriteria(analysisSetName.value)
  ElMessage.success(`${item.name} 저장 완료`)
}

async function fillSample() {
  store.fillSampleCriteria()
  await store.runPreview()
}

async function resetSynthetic() {
  await store.reset()
  await Promise.all([binGroups.loadBinGroups(), conditionRules.loadConditionRules(), presetStore.loadTree()])
  ElMessage.success('Synthetic mock data를 재생성했습니다')
}

let suppressDirtyOnce = false

function onPresetLoad(criteria: any, _info: any) {
  suppressDirtyOnce = true
  store.criteria.fab = criteria.fab
  store.criteria.eds = criteria.eds
  store.criteria.chart = criteria.chart || defaultChartState()
  store.preview = null
}

async function onSavePreset(payload: any) {
  const criteria = { fab: store.criteria.fab, eds: store.criteria.eds, chart: store.criteria.chart }
  if (payload.mode === 'new-rev' && presetStore.loadedPreset) {
    await presetStore.addRevision(presetStore.loadedPreset.id, { note: payload.note, criteria })
    presetStore.markLoaded({ ...presetStore.loadedPreset, rev: presetStore.loadedPreset.rev + 1 })
    ElMessage.success('새 Rev로 저장되었습니다')
  } else {
    const preset = await presetStore.create({
      folder_id: payload.folder_id,
      name: payload.name,
      scope: payload.scope,
      note: payload.note,
      criteria,
    })
    const folderName = presetStore.tree.folders.find((f: any) => f.id === payload.folder_id)?.name || ''
    presetStore.markLoaded({ id: preset.id, name: preset.name, rev: 0, folderName, scope: preset.scope, owner: preset.owner })
    ElMessage.success('Preset이 저장되었습니다')
  }
  savePresetVisible.value = false
}

watch(
  () => store.criteria.chart,
  () => {
    if (store.preview && !store.previewLoading) store.runPreview()
  },
  { deep: true },
)

watch(
  () => [store.criteria.fab, store.criteria.eds],
  () => {
    if (suppressDirtyOnce) {
      suppressDirtyOnce = false
      return
    }
    presetStore.markDirty()
  },
  { deep: true },
)

onMounted(() => {
  presetStore.loadTree()
})
</script>
