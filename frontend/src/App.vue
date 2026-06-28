<template>
  <el-container class="app-shell">
    <el-aside width="252px" class="left-nav">
      <div class="brand-block">
        <span class="brand-kicker">Synthetic prototype</span>
        <h1>EDS BIN 공정 Window Workbench</h1>
      </div>
      <el-menu router :default-active="$route.path" class="nav-menu">
        <el-menu-item index="/guide"><el-icon><Guide /></el-icon><span>사용 가이드</span></el-menu-item>
        <el-menu-item index="/analysis-set"><el-icon><Filter /></el-icon><span>분석 물량</span></el-menu-item>
        <el-menu-item index="/bin-group"><el-icon><Grid /></el-icon><span>BIN Group</span></el-menu-item>
        <el-menu-item index="/condition-rule"><el-icon><SetUp /></el-icon><span>조건 Rule</span></el-menu-item>
        <el-menu-item index="/window-review"><el-icon><TrendCharts /></el-icon><span>Window Review</span></el-menu-item>
        <el-menu-item index="/pending-prediction"><el-icon><DataLine /></el-icon><span>Pending 예측</span></el-menu-item>
        <el-menu-item index="/export-report"><el-icon><Download /></el-icon><span>Export / Report</span></el-menu-item>
      </el-menu>
      <div class="nav-footer">
        <el-tag type="warning" effect="plain">Mock data only</el-tag>
        <p>실제 사내 DB나 보안 정보 없이 synthetic data만 사용합니다.</p>
      </div>
    </el-aside>

    <el-container>
      <el-header class="topbar" height="74px">
        <div>
          <strong>{{ routeLabel }}</strong>
          <span>{{ activeSummary }}</span>
        </div>
        <div class="topbar-actions">
          <el-button :icon="Refresh" plain @click="refreshAll">새로고침</el-button>
          <el-button :icon="Plus" type="primary" plain @click="ensureDefault">기본 분석 Set</el-button>
        </div>
      </el-header>
      <el-main class="main-surface">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { DataLine, Download, Filter, Grid, Guide, Plus, Refresh, SetUp, TrendCharts } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAnalysisSetStore } from './stores/analysisSetStore'
import { useBinGroupStore } from './stores/binGroupStore'
import { useConditionRuleStore } from './stores/conditionRuleStore'
import { useWindowReviewStore } from './stores/windowReviewStore'

const route = useRoute()
const analysisSets = useAnalysisSetStore()
const binGroups = useBinGroupStore()
const conditionRules = useConditionRuleStore()
const windowReview = useWindowReviewStore()

const routeLabel = computed(() => String(route.meta.label || 'Workbench'))
const activeSummary = computed(() => {
  const set = analysisSets.selectedAnalysisSet
  const groups = binGroups.selectedGroups.map((group) => group.name).join(' + ') || '선택된 BIN Group 없음'
  const rule = conditionRules.selectedRule?.name || '선택된 조건 Rule 없음'
  if (!set) return `${groups} / ${rule}`
  return `${set.name} / ${groups} / ${rule}`
})

async function refreshAll() {
  await Promise.all([
    analysisSets.loadMetadata(),
    analysisSets.loadAnalysisSets(),
    binGroups.loadBinGroups(),
    conditionRules.loadConditionRules(),
    windowReview.loadExclusions(),
  ])
  ElMessage.success('Workbench 기준 정보가 갱신되었습니다')
}

async function ensureDefault() {
  const item = await analysisSets.createDefault()
  ElMessage.success(`${item.name} 생성 완료`)
}

onMounted(async () => {
  await refreshAll()
  if (!analysisSets.analysisSets.length) await ensureDefault()
})
</script>
