<template>
  <div class="page-grid two-col">
    <FilterPanel title="분석 물량 정의" subtitle="검토 대상 wafer 모집단, 제외 조건, EDS 완료 범위를 먼저 고정합니다.">
      <template #actions>
        <el-button :icon="Refresh" plain @click="resetSynthetic">Mock data 재생성</el-button>
      </template>
      <el-form label-position="top" class="dense-form">
        <div class="form-grid">
          <el-form-item label="기간">
            <el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD" start-placeholder="시작일" end-placeholder="종료일" />
          </el-form-item>
          <el-form-item label="Product">
            <el-select v-model="filters.product" multiple filterable>
              <el-option v-for="item in metadata?.products || []" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="Layer">
            <el-select v-model="filters.layer" multiple filterable>
              <el-option v-for="item in metadata?.layers || []" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="Step">
            <el-select v-model="filters.step" multiple filterable>
              <el-option v-for="item in metadata?.steps || []" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="FAB 관리 인자">
            <el-select v-model="filters.parameter" multiple filterable>
              <el-option v-for="item in metadata?.parameters || []" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="Tool / Chamber">
            <el-select v-model="filters.tool" multiple filterable placeholder="전체 Tool">
              <el-option v-for="item in metadata?.tools || []" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="PPID / ECO">
            <el-select v-model="filters.ppid" multiple filterable placeholder="전체 PPID">
              <el-option v-for="item in metadata?.ppids || []" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="EDS 완료 상태">
            <el-segmented v-model="filters.eds_status" :options="edsOptions" />
          </el-form-item>
        </div>
        <div class="check-row">
          <el-checkbox v-model="filters.exclude_rework">Rework 제외</el-checkbox>
          <el-checkbox v-model="filters.exclude_engineering_lot">Engineering lot 제외</el-checkbox>
          <el-checkbox v-model="filters.exclude_abnormal_route">Abnormal route 제외</el-checkbox>
        </div>
        <div class="form-actions">
          <el-input v-model="name" placeholder="Analysis Set 이름" />
          <el-button :icon="Plus" type="primary" @click="createSet">Analysis Set 저장</el-button>
        </div>
      </el-form>
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
        <el-table-column prop="name" label="이름" min-width="190" />
        <el-table-column prop="metrics.wafer_count" label="Wafer" width="100" />
        <el-table-column prop="metrics.eds_pending_count" label="Pending" width="100" />
      </el-table>
    </FilterPanel>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { Plus, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import FilterPanel from '../components/common/FilterPanel.vue'
import SummaryCard from '../components/common/SummaryCard.vue'
import { defaultFilters, useAnalysisSetStore } from '../stores/analysisSetStore'
import { useBinGroupStore } from '../stores/binGroupStore'
import { useConditionRuleStore } from '../stores/conditionRuleStore'

const store = useAnalysisSetStore()
const binGroups = useBinGroupStore()
const conditionRules = useConditionRuleStore()
const filters = reactive(defaultFilters())
const name = ref('Ch.Hole CD window review')
const dateRange = ref<[string, string] | ''>('')
const metadata = computed(() => store.metadata)
const selected = computed(() => store.selectedAnalysisSet)
const edsOptions = [
  { label: 'Actual only', value: 'actual_only' },
  { label: 'Pending 포함', value: 'include_pending' },
]

watch(metadata, (value) => {
  if (value?.date_range && !dateRange.value) dateRange.value = [value.date_range.start_date, value.date_range.end_date]
}, { immediate: true })

function pct(value: number) {
  return `${(Number(value || 0) * 100).toFixed(1)}%`
}

function selectSet(row: any) {
  if (row?.id) store.selectedAnalysisSetId = row.id
}

async function createSet() {
  const payload = {
    name: name.value,
    filters: {
      ...filters,
      start_date: Array.isArray(dateRange.value) ? dateRange.value[0] : undefined,
      end_date: Array.isArray(dateRange.value) ? dateRange.value[1] : undefined,
    },
  }
  const item = await store.create(payload)
  ElMessage.success(`${item.name} 저장 완료`)
}

async function resetSynthetic() {
  await store.reset()
  await Promise.all([binGroups.loadBinGroups(), conditionRules.loadConditionRules()])
  ElMessage.success('Synthetic mock data를 재생성했습니다')
}
</script>
