<template>
  <div class="page-grid two-col">
    <FilterPanel title="Export / Report" subtitle="현재 분석 기준과 Spotfire 후속 분석용 wafer-level 데이터를 내려받습니다.">
      <div class="toolbar-grid single">
        <el-select v-model="analysis.selectedAnalysisSetId" placeholder="Analysis Set">
          <el-option v-for="item in analysis.analysisSets" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>
      </div>
      <div class="export-actions">
        <el-tooltip v-if="!analysis.selectedAnalysisSet?.id" content="Analysis Set을 선택해야 CSV를 내려받을 수 있습니다">
          <span><el-button :icon="Download" type="primary" disabled>필터링 wafer CSV</el-button></span>
        </el-tooltip>
        <el-button v-else :icon="Download" type="primary" tag="a" :href="analysisCsvUrl" target="_blank">필터링 wafer CSV</el-button>
        <el-button :icon="Download" plain @click="downloadJson('analysis-set.json', analysis.selectedAnalysisSet)">Analysis Set JSON</el-button>
        <el-button :icon="Download" plain @click="downloadJson('bin-groups.json', groups.binGroups)">BIN Group JSON</el-button>
        <el-button :icon="Download" plain @click="downloadJson('condition-rules.json', rules.conditionRules)">Condition Rule JSON</el-button>
        <el-button :icon="Download" plain @click="downloadJson('exclusion-rules.json', store.exclusions)">Exclusion Rule JSON</el-button>
        <el-tooltip v-if="!store.review?.analysis_run_id" content="Window Review를 먼저 실행해야 보고용 요약을 생성할 수 있습니다">
          <span><el-button :icon="Document" plain disabled>보고용 요약 생성</el-button></span>
        </el-tooltip>
        <el-button v-else :icon="Document" plain @click="loadReport">보고용 요약 생성</el-button>
      </div>
    </FilterPanel>

    <FilterPanel title="보고용 요약" subtitle="자동 판정이 아니라 검토 후보 표현으로 생성합니다.">
      <el-input :model-value="reportText" type="textarea" :rows="12" readonly />
      <div class="report-note">
        Spotfire 후속 분석: 필터링 CSV와 BIN Group, Condition Rule, Exclusion Rule JSON을 함께 사용하세요.
      </div>
    </FilterPanel>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { Document, Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import FilterPanel from '../components/common/FilterPanel.vue'
import { exportUrl } from '../api/client.ts'
import { useAnalysisSetStore } from '../stores/analysisSetStore'
import { useBinGroupStore } from '../stores/binGroupStore'
import { useConditionRuleStore } from '../stores/conditionRuleStore'
import { useWindowReviewStore } from '../stores/windowReviewStore'

const analysis = useAnalysisSetStore()
const groups = useBinGroupStore()
const rules = useConditionRuleStore()
const store = useWindowReviewStore()
const analysisCsvUrl = computed(() => analysis.selectedAnalysisSet?.id ? exportUrl(`/export/analysis-set/${analysis.selectedAnalysisSet.id}`) : '#')
const reportText = computed(() => store.report?.summary_text || 'Window Review 실행 후 보고용 요약을 생성할 수 있습니다.')

function downloadJson(filename: string, payload: any) {
  const blob = new Blob([JSON.stringify(payload || {}, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

async function loadReport() {
  if (!store.review?.analysis_run_id) return
  await store.loadReport(store.review.analysis_run_id)
  ElMessage.success('보고용 요약을 생성했습니다')
}

onMounted(() => store.loadExclusions())
</script>
