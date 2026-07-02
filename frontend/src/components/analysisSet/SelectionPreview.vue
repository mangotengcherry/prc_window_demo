<template>
  <div class="analysis-set-preview">
    <div v-if="preview?.summary" class="summary-band compact">
      <SummaryCard label="Lot 수" :value="preview.summary.lot_count" />
      <SummaryCard label="Wafer 수" :value="preview.summary.wafer_count" />
      <SummaryCard label="EDS 매칭" :value="`${preview.summary.eds_matched_count} (${pct(preview.summary.eds_match_ratio)})`" />
    </div>
    <p v-if="joinFlowText" class="join-flow-text" :class="{ 'is-empty': isEmptyResult }">{{ joinFlowText }}</p>

    <div class="form-grid">
      <el-form-item label="x축">
        <el-segmented v-model="chart.x_axis" :options="xAxisOptions" />
      </el-form-item>
      <el-form-item label="legend">
        <el-select v-model="chart.legend_by" clearable placeholder="전체">
          <el-option v-for="col in legendOptions" :key="col" :label="col" :value="col" />
        </el-select>
      </el-form-item>
    </div>

    <div v-if="loading" class="preview-state">불러오는 중...</div>
    <div v-else-if="!preview" class="preview-state">조건을 선택하고 물량 조회를 누르세요</div>
    <div v-else-if="preview.error" class="preview-state">{{ preview.error.message }}</div>
    <div v-else-if="isEmptyResult" class="preview-state">조건에 해당하는 물량 없음 — 기간을 넓혀보세요</div>
    <div v-else-if="!traces.length" class="preview-state">EDS 조건을 추가하면 시계열 미리보기가 표시됩니다</div>
    <div v-else class="chart-panel" style="height: 340px">
      <PlotlyChart :data="traces" :layout="layout" />
    </div>
    <p v-if="preview?.sampled" class="report-note">{{ preview.n_total.toLocaleString() }}개 중 {{ preview.points.length.toLocaleString() }}개 표시</p>

    <div v-if="chart.adhoc_filters.length" class="filter-chip-row">
      <el-tag v-for="(f, idx) in chart.adhoc_filters" :key="idx" closable @close="removeFilter(idx)">{{ f }}</el-tag>
    </div>
    <div class="form-actions">
      <el-button text :icon="Plus" @click="filterDialogVisible = true">+ 필터</el-button>
      <el-button text :icon="Plus" @click="columnDialogVisible = true">+ 파생 컬럼</el-button>
    </div>
    <el-alert v-if="adhocError" :title="adhocError.message" type="error" show-icon :closable="false" class="mt-8" />

    <el-dialog v-model="filterDialogVisible" title="필터 추가" width="480px" @close="draftFilter = ''">
      <ExpressionEditor v-model="draftFilter" context="eds" @valid-change="(v) => (draftFilterValid = v)" />
      <template #footer>
        <el-button @click="filterDialogVisible = false">취소</el-button>
        <el-button type="primary" :disabled="!draftFilter.trim() || !draftFilterValid" @click="addFilter">추가</el-button>
      </template>
    </el-dialog>

    <ComputedColumnDialog v-model:visible="columnDialogVisible" :existing-names="existingColumnNames" @save="addComputedColumn" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import PlotlyChart from '../charts/PlotlyChart.vue'
import SummaryCard from '../common/SummaryCard.vue'
import ExpressionEditor from './ExpressionEditor.vue'
import ComputedColumnDialog from './ComputedColumnDialog.vue'
import { useAnalysisSetStore } from '../../stores/analysisSetStore'
import { CATEGORICAL_PALETTE } from '../../palette.ts'

const props = defineProps<{
  preview: any
  loading: boolean
}>()

const chart = defineModel<any>('chart', { required: true })
const analysis = useAnalysisSetStore()

const filterDialogVisible = ref(false)
const columnDialogVisible = ref(false)
const draftFilter = ref('')
const draftFilterValid = ref(true)

const xAxisOptions = [
  { label: 'FAB 시각', value: 'fab_time' },
  { label: 'EDS 시각', value: 'eds_time' },
]

function pct(value: number) {
  return `${(Number(value || 0) * 100).toFixed(1)}%`
}

const legendOptions = computed(() => props.preview?.columns?.categorical || analysis.metadata?.categorical_columns || [])

const existingColumnNames = computed(() => [
  ...(props.preview?.columns?.categorical || []),
  ...(props.preview?.columns?.numeric || []),
])

const adhocError = computed(() => {
  const stage = props.preview?.error?.stage
  if (stage === 'adhoc' || stage?.startsWith('computed:')) return props.preview.error
  return null
})

const joinFlowText = computed(() => {
  const matches = props.preview?.summary?.fab_step_matches
  if (!matches?.length) return ''
  const chain = matches
    .map((m: any, idx: number) => (idx === 0 ? `${m.fab_step} ${m.matched.toLocaleString()}` : `∩ ${m.fab_step} ${m.matched.toLocaleString()}`))
    .join(' → ')
  return `${chain} → 제외 ${props.preview.summary.wafer_count.toLocaleString()}`
})

const isEmptyResult = computed(() => props.preview && !props.preview.error && props.preview.summary?.wafer_count === 0)

const traces = computed(() => {
  const points = props.preview?.points
  if (!points?.length) return []
  const groups = new Map<string, any[]>()
  points.forEach((point: any) => {
    const key = point.legend || '전체'
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key)!.push(point)
  })
  return [...groups.entries()].map(([name, rows], index) => ({
    type: 'scattergl',
    mode: 'markers',
    name,
    x: rows.map((row) => row.x),
    y: rows.map((row) => row.y),
    text: rows.map((row) => `${row.wafer_id}<br>${row.meta?.tool_id}/${row.meta?.chamber_id}`),
    marker: {
      color: CATEGORICAL_PALETTE[index % CATEGORICAL_PALETTE.length],
      size: 7,
      opacity: 0.75,
      line: { width: 0.5, color: '#ffffff' },
    },
  }))
})

const layout = computed(() => ({
  xaxis: { title: chart.value.x_axis === 'eds_time' ? 'EDS 시각' : 'FAB 시각', type: 'date' },
  yaxis: { title: props.preview?.points?.[0]?.meta?.eds_item || 'value' },
  legend: { orientation: 'h', y: -0.24 },
}))

function removeFilter(idx: number) {
  chart.value.adhoc_filters.splice(idx, 1)
}

function addFilter() {
  chart.value.adhoc_filters.push(draftFilter.value)
  draftFilter.value = ''
  filterDialogVisible.value = false
}

function addComputedColumn(payload: { name: string; expression: string }) {
  chart.value.computed_columns.push(payload)
  columnDialogVisible.value = false
}
</script>
