<template>
  <div class="page-stack">
    <FilterPanel title="Window Review Pack" subtitle="FAB X와 EDS BIN Group 관계를 condition legend, 제외 rule, zone, interaction 관점으로 함께 확인합니다.">
      <template #actions>
        <el-button :icon="View" type="primary" :loading="reviewStore.loading" @click="runReview()">Review 실행</el-button>
      </template>
      <div class="toolbar-grid">
        <el-select v-model="analysis.selectedAnalysisSetId" placeholder="Analysis Set">
          <el-option v-for="item in analysis.analysisSets" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>
        <el-select v-model="xParameter" placeholder="X 관리 인자">
          <el-option v-for="item in analysis.metadata?.parameters || []" :key="item" :label="item" :value="item" />
        </el-select>
        <el-select v-model="groups.selectedBinGroupIds" multiple collapse-tags collapse-tags-tooltip placeholder="BIN Group">
          <el-option v-for="item in groups.binGroups" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>
        <el-select v-model="rules.selectedConditionRuleId" placeholder="조건 Rule">
          <el-option v-for="item in rules.conditionRules" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>
        <el-input-number v-model="reviewStore.viewOptions.bins" :min="4" :max="14" controls-position="right" />
      </div>
    </FilterPanel>

    <template v-if="review">
      <WindowSummaryPanel :review="review" />
      <el-tabs v-model="activeTab" class="chart-tabs">
        <el-tab-pane label="요약" name="summary">
          <div class="page-grid two-col">
            <FilterPanel title="판정 후보">
              <el-timeline>
                <el-timeline-item v-for="candidate in review.decision_candidates" :key="candidate.type" :timestamp="candidate.type">
                  {{ candidate.basis }}
                </el-timeline-item>
              </el-timeline>
            </FilterPanel>
            <FilterPanel title="핵심 근거">
              <ul class="evidence-list">
                <li v-for="item in review.evidence" :key="item">{{ item }}</li>
              </ul>
            </FilterPanel>
          </div>
        </el-tab-pane>
        <el-tab-pane label="BIN Pareto" name="pareto">
          <div class="chart-panel"><ParetoChart :rows="review.pareto_data" @bar-click="onParetoBarClick" /></div>
        </el-tab-pane>
        <el-tab-pane label="Driver Ranking" name="driver">
          <div class="chart-panel"><DriverRankingChart :rows="review.driver_ranking" @bar-click="onDriverBarClick" /></div>
        </el-tab-pane>
        <el-tab-pane label="Raw Scatter" name="scatter">
          <div class="tab-toolbar">
            <span class="tab-toolbar__label">Y축</span>
            <el-select v-model="reviewStore.viewOptions.y_axis_metric" placeholder="BIN Group fail (기본)" clearable style="width: 220px" @change="runReview()">
              <el-option v-for="g in groups.selectedGroups" :key="g.id" :label="g.name" :value="g.id" />
              <el-option label="Yield" value="yield" />
            </el-select>
          </div>
          <div class="chart-panel">
            <RawScatterChart
              :points="review.scatter_data"
              :x-title="xParameter"
              :y-title="yAxisTitle"
              :safe-window="review.summary_metrics?.safe_window"
              @point-click="openPoint"
              @points-selected="selectedPoints = $event.filter(Boolean)"
            />
          </div>
          <div class="selection-bar">
            <span>제외 후보 wafer {{ selectedPoints.length }}매 선택</span>
            <el-input v-model="exclusionReason" placeholder="제외 사유" />
            <el-button :icon="Delete" type="danger" plain :disabled="!selectedPoints.length" @click="saveSelectedExclusion">Exclusion Rule 저장</el-button>
          </div>
        </el-tab-pane>
        <el-tab-pane label="Binned Response" name="binned">
          <div class="chart-panel"><BinnedResponseChart :rows="review.binned_response_data" :x-title="xParameter" /></div>
        </el-tab-pane>
        <el-tab-pane label="Trade-off" name="tradeoff">
          <div class="chart-panel"><TradeoffChart :rows="review.tradeoff_data" :x-title="xParameter" /></div>
        </el-tab-pane>
        <el-tab-pane label="Time Trend" name="trend">
          <div class="tab-toolbar">
            <el-tag v-if="review.trend_data?.spc" :type="review.trend_data.spc.violations.length ? 'danger' : 'success'" size="small">
              SPC 위반 {{ review.trend_data.spc.violations.length }}건
            </el-tag>
            <el-tag v-else type="info" size="small">일별 데이터 20건 미만 — SPC 관리한계 생략</el-tag>
          </div>
          <div class="chart-panel"><TimeTrendChart :trend="review.trend_data" :spc="review.trend_data?.spc" /></div>
        </el-tab-pane>
        <el-tab-pane label="Commonality" name="commonality">
          <CommonalityPanel :rows="review.commonality_data" />
        </el-tab-pane>
        <el-tab-pane label="Zone View" name="zone">
          <div class="chart-panel"><ZoneViewChart :rows="review.zone_data" :points="review.scatter_data" :x-title="xParameter" /></div>
        </el-tab-pane>
        <el-tab-pane label="Interaction" name="interaction">
          <div class="tab-toolbar">
            <span class="tab-toolbar__label">X 인자</span>
            <el-select v-model="reviewStore.viewOptions.interaction_x" placeholder="기본: 관리 인자" clearable style="width: 200px" @change="runReview()">
              <el-option v-for="item in analysis.metadata?.numeric_columns || []" :key="item" :label="item" :value="item" />
            </el-select>
            <span class="tab-toolbar__label">Y 인자</span>
            <el-select v-model="reviewStore.viewOptions.interaction_y" placeholder="기본: 자동 선택" clearable style="width: 200px" @change="runReview()">
              <el-option v-for="item in analysis.metadata?.numeric_columns || []" :key="item" :label="item" :value="item" />
            </el-select>
          </div>
          <div class="chart-panel"><InteractionHeatmap :rows="review.interaction_heatmap_data" /></div>
        </el-tab-pane>
        <el-tab-pane label="제외 Rule" name="excluded">
          <FilterPanel title="Exclusion Rule version" subtitle="Wafer를 삭제하지 않고 제외 rule version으로 저장한 뒤 재계산합니다.">
            <div v-if="review.excluded_point_summary" class="summary-band compact">
              <SummaryCard label="제외 Wafer" :value="review.excluded_point_summary.excluded_count" />
              <SummaryCard label="제외 전 corr" :value="review.excluded_point_summary.before?.correlation ?? '-'" />
              <SummaryCard label="제외 후 corr" :value="review.excluded_point_summary.after?.correlation ?? '-'" />
              <div class="summary-card">
                <div class="summary-card__label">|corr| 변화</div>
                <div class="summary-card__value" :class="exclusionDelta == null ? '' : exclusionDelta > 0 ? 'delta-up' : 'delta-down'">
                  {{ exclusionDelta == null ? '-' : `${exclusionDelta > 0 ? '▲' : '▼'} ${Math.abs(exclusionDelta).toFixed(3)}` }}
                </div>
              </div>
            </div>
            <ExcludedPointsTable :rules="reviewStore.exclusions" />
          </FilterPanel>
        </el-tab-pane>
      </el-tabs>
      <WaferDetailDrawer v-model:visible="drawerVisible" :point="selectedPoint" @exclude="saveDrawerExclusion" />
    </template>
    <el-empty v-else description="Review 실행 후 chart pack이 표시됩니다" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Delete, View } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import FilterPanel from '../components/common/FilterPanel.vue'
import SummaryCard from '../components/common/SummaryCard.vue'
import RawScatterChart from '../components/charts/RawScatterChart.vue'
import BinnedResponseChart from '../components/charts/BinnedResponseChart.vue'
import TradeoffChart from '../components/charts/TradeoffChart.vue'
import TimeTrendChart from '../components/charts/TimeTrendChart.vue'
import ZoneViewChart from '../components/charts/ZoneViewChart.vue'
import InteractionHeatmap from '../components/charts/InteractionHeatmap.vue'
import ParetoChart from '../components/charts/ParetoChart.vue'
import DriverRankingChart from '../components/charts/DriverRankingChart.vue'
import CommonalityPanel from '../components/window/CommonalityPanel.vue'
import WindowSummaryPanel from '../components/window/WindowSummaryPanel.vue'
import WaferDetailDrawer from '../components/window/WaferDetailDrawer.vue'
import ExcludedPointsTable from '../components/window/ExcludedPointsTable.vue'
import { useAnalysisSetStore } from '../stores/analysisSetStore'
import { useBinGroupStore } from '../stores/binGroupStore'
import { useConditionRuleStore } from '../stores/conditionRuleStore'
import { useWindowReviewStore } from '../stores/windowReviewStore'

const analysis = useAnalysisSetStore()
const groups = useBinGroupStore()
const rules = useConditionRuleStore()
const reviewStore = useWindowReviewStore()
const xParameter = ref('metro_ch_hole_cd')
const activeTab = ref('summary')
const selectedPoints = ref<any[]>([])
const selectedPoint = ref<any>(null)
const drawerVisible = ref(false)
const exclusionReason = ref('다른 공정 noise 후보')
const review = computed(() => reviewStore.review)

const yAxisTitle = computed(() => {
  const metric = reviewStore.viewOptions.y_axis_metric
  if (metric === 'yield') return 'Yield'
  if (metric) return groups.binGroups.find((g) => g.id === metric)?.name || metric
  return review.value?.context?.bin_groups?.[0]?.name
})

const exclusionDelta = computed(() => {
  const before = review.value?.excluded_point_summary?.before?.correlation
  const after = review.value?.excluded_point_summary?.after?.correlation
  if (before == null || after == null) return null
  return Math.abs(after) - Math.abs(before)
})

function payload(extra: Record<string, any> = {}) {
  return {
    analysis_set_id: analysis.selectedAnalysisSet?.id,
    x_parameter: xParameter.value,
    bin_group_ids: groups.selectedBinGroupIds.length ? groups.selectedBinGroupIds : ['BG001'],
    condition_rule_id: rules.selectedConditionRuleId,
    view_options: { ...reviewStore.viewOptions },
    ...extra,
  }
}

async function runReview(extra: Record<string, any> = {}) {
  if (!analysis.selectedAnalysisSet?.id) {
    await analysis.createDefault()
  }
  await reviewStore.runReview(payload(extra))
  selectedPoints.value = []
}

function openPoint(point: any) {
  selectedPoint.value = point
  drawerVisible.value = true
}

async function saveSelectedExclusion() {
  const item = await reviewStore.saveExclusion({
    name: `Window Review 제외 ${new Date().toLocaleTimeString()}`,
    analysis_set_id: analysis.selectedAnalysisSet.id,
    wafer_ids: selectedPoints.value.map((point) => point.wafer_id),
    reason: exclusionReason.value,
  })
  await runReview({ exclusion_rule_id: item.id })
  ElMessage.success(`${item.excluded_count}매 wafer를 Exclusion Rule로 제외했습니다`)
}

async function saveDrawerExclusion(event: any) {
  const item = await reviewStore.saveExclusion({
    name: `Wafer ${event.waferIds[0]} 제외`,
    analysis_set_id: analysis.selectedAnalysisSet.id,
    wafer_ids: event.waferIds,
    reason: event.reason,
  })
  drawerVisible.value = false
  await runReview({ exclusion_rule_id: item.id })
}

async function onParetoBarClick(binId: string) {
  try {
    await ElMessageBox.confirm(`${binId} 단일 BIN으로 임시 BIN Group을 만들어 review를 재실행할까요?`, '임시 BIN Group', {
      confirmButtonText: '재실행',
      cancelButtonText: '취소',
      type: 'warning',
    })
  } catch {
    return
  }
  await groups.create({ name: `임시 · ${binId}`, description: 'Pareto bar 클릭으로 생성된 임시 그룹', failure_mode: '', bin_ids: [binId] })
  await runReview()
}

async function onDriverBarClick(parameter: string) {
  xParameter.value = parameter
  await runReview()
}

onMounted(async () => {
  await reviewStore.loadExclusions()
  if (!reviewStore.review && analysis.selectedAnalysisSet) await runReview()
})
</script>

<style scoped>
.tab-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.tab-toolbar__label {
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.delta-up {
  color: #16a34a;
}

.delta-down {
  color: #dc2626;
}
</style>
