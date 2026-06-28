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
        <el-input-number v-model="bins" :min="4" :max="14" controls-position="right" />
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
        <el-tab-pane label="Raw Scatter" name="scatter">
          <div class="chart-panel">
            <RawScatterChart
              :points="review.scatter_data"
              :x-title="xParameter"
              :y-title="review.context.bin_groups[0]?.name"
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
          <div class="chart-panel"><TimeTrendChart :trend="review.trend_data" /></div>
        </el-tab-pane>
        <el-tab-pane label="Condition Split" name="condition">
          <div class="chart-panel"><RawScatterChart :points="review.scatter_data" :x-title="xParameter" :y-title="review.context.bin_groups[0]?.name" @point-click="openPoint" /></div>
        </el-tab-pane>
        <el-tab-pane label="Zone View" name="zone">
          <div class="chart-panel"><ZoneViewChart :rows="review.zone_data" :x-title="xParameter" /></div>
        </el-tab-pane>
        <el-tab-pane label="Interaction" name="interaction">
          <div class="chart-panel"><InteractionHeatmap :rows="review.interaction_heatmap_data" /></div>
        </el-tab-pane>
        <el-tab-pane label="제외 Rule" name="excluded">
          <FilterPanel title="Exclusion Rule version" subtitle="Wafer를 삭제하지 않고 제외 rule version으로 저장한 뒤 재계산합니다.">
            <div v-if="review.excluded_point_summary" class="summary-band compact">
              <SummaryCard label="제외 Wafer" :value="review.excluded_point_summary.excluded_count" />
              <SummaryCard label="제외 전 corr" :value="review.excluded_point_summary.before?.correlation ?? '-'" />
              <SummaryCard label="제외 후 corr" :value="review.excluded_point_summary.after?.correlation ?? '-'" />
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
import { ElMessage } from 'element-plus'
import FilterPanel from '../components/common/FilterPanel.vue'
import SummaryCard from '../components/common/SummaryCard.vue'
import RawScatterChart from '../components/charts/RawScatterChart.vue'
import BinnedResponseChart from '../components/charts/BinnedResponseChart.vue'
import TradeoffChart from '../components/charts/TradeoffChart.vue'
import TimeTrendChart from '../components/charts/TimeTrendChart.vue'
import ZoneViewChart from '../components/charts/ZoneViewChart.vue'
import InteractionHeatmap from '../components/charts/InteractionHeatmap.vue'
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
const bins = ref(8)
const activeTab = ref('summary')
const selectedPoints = ref<any[]>([])
const selectedPoint = ref<any>(null)
const drawerVisible = ref(false)
const exclusionReason = ref('다른 공정 noise 후보')
const review = computed(() => reviewStore.review)

function payload(extra: Record<string, any> = {}) {
  return {
    analysis_set_id: analysis.selectedAnalysisSet?.id,
    x_parameter: xParameter.value,
    bin_group_ids: groups.selectedBinGroupIds.length ? groups.selectedBinGroupIds : ['BG001'],
    condition_rule_id: rules.selectedConditionRuleId,
    view_options: { bins: bins.value },
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

onMounted(async () => {
  await reviewStore.loadExclusions()
  if (!reviewStore.review && analysis.selectedAnalysisSet) await runReview()
})
</script>
