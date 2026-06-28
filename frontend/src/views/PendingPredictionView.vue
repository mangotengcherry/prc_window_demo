<template>
  <div class="page-stack">
    <FilterPanel title="EDS Pending 예측" subtitle="Actual EDS wafer로 설명 가능한 회귀 모델을 학습하고, Pending 물량의 BIN Group risk를 예측 범위와 함께 확인합니다.">
      <template #actions>
        <el-button :icon="DataAnalysis" type="primary" :loading="store.loading" @click="runPrediction">예측 실행</el-button>
      </template>
      <div class="toolbar-grid">
        <el-select v-model="analysis.selectedAnalysisSetId" placeholder="Analysis Set">
          <el-option v-for="item in analysis.analysisSets" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>
        <el-select v-model="groups.selectedBinGroupIds" multiple collapse-tags placeholder="BIN Group">
          <el-option v-for="item in groups.binGroups" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>
        <el-select v-model="rules.selectedConditionRuleId" placeholder="조건 Rule">
          <el-option v-for="item in rules.conditionRules" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>
        <el-select v-model="xParameters" multiple collapse-tags placeholder="X feature">
          <el-option v-for="item in analysis.metadata?.parameters || []" :key="item" :label="item" :value="item" />
        </el-select>
        <el-select v-model="modelType" placeholder="Model">
          <el-option label="Ridge" value="ridge" />
          <el-option label="LinearRegression" value="linear" />
          <el-option label="HuberRegressor" value="huber" />
          <el-option label="Polynomial degree 2" value="polynomial2" />
        </el-select>
      </div>
    </FilterPanel>

    <template v-if="prediction">
      <PredictionPerformancePanel :metrics="prediction.model_performance" />
      <div class="chart-panel">
        <PlotlyChart :data="trendData" :layout="trendLayout" />
      </div>
      <PendingRiskTable :rows="prediction.pending_predictions" />
    </template>
    <el-empty v-else description="예측 실행 후 Pending risk table과 backtest metric이 표시됩니다" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { DataAnalysis } from '@element-plus/icons-vue'
import FilterPanel from '../components/common/FilterPanel.vue'
import PlotlyChart from '../components/charts/PlotlyChart.vue'
import PendingRiskTable from '../components/prediction/PendingRiskTable.vue'
import PredictionPerformancePanel from '../components/prediction/PredictionPerformancePanel.vue'
import { useAnalysisSetStore } from '../stores/analysisSetStore'
import { useBinGroupStore } from '../stores/binGroupStore'
import { useConditionRuleStore } from '../stores/conditionRuleStore'
import { useWindowReviewStore } from '../stores/windowReviewStore'

const analysis = useAnalysisSetStore()
const groups = useBinGroupStore()
const rules = useConditionRuleStore()
const store = useWindowReviewStore()
const xParameters = ref(['metro_ch_hole_cd', 'metro_thickness', 'metro_uniformity'])
const modelType = ref('ridge')
const prediction = computed(() => store.prediction)

const trendData = computed(() => [
  {
    type: 'scatter',
    mode: 'lines+markers',
    name: 'Actual EDS',
    x: prediction.value?.trend?.actual?.map((row: any) => row.date) || [],
    y: prediction.value?.trend?.actual?.map((row: any) => row.actual_fail_rate) || [],
    line: { color: '#111827', width: 2 },
  },
  {
    type: 'scatter',
    mode: 'lines+markers',
    name: 'Predicted Pending EDS',
    x: prediction.value?.trend?.predicted?.map((row: any) => row.date) || [],
    y: prediction.value?.trend?.predicted?.map((row: any) => row.predicted_fail_rate) || [],
    line: { color: '#f59e0b', width: 2, dash: 'dash' },
  },
])

const trendLayout = {
  xaxis: { title: '예상 EDS일 / 공정일' },
  yaxis: { title: 'BIN Group fail rate', tickformat: '.1%' },
  legend: { orientation: 'h', y: -0.24 },
}

async function runPrediction() {
  if (!analysis.selectedAnalysisSet?.id) await analysis.createDefault()
  await store.runPrediction({
    analysis_set_id: analysis.selectedAnalysisSet.id,
    x_parameters: xParameters.value,
    bin_group_ids: groups.selectedBinGroupIds.length ? groups.selectedBinGroupIds : ['BG001'],
    condition_rule_id: rules.selectedConditionRuleId,
    model_type: modelType.value,
  })
}
</script>
