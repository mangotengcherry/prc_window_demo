import { createRouter, createWebHistory } from 'vue-router'
import AnalysisSetView from '../views/AnalysisSetView.vue'
import BinGroupView from '../views/BinGroupView.vue'
import ConditionRuleView from '../views/ConditionRuleView.vue'
import WindowReviewView from '../views/WindowReviewView.vue'
import PendingPredictionView from '../views/PendingPredictionView.vue'
import ExportReportView from '../views/ExportReportView.vue'
import GuideScenarioView from '../views/GuideScenarioView.vue'

const routes = [
  { path: '/', redirect: '/analysis-set' },
  { path: '/guide', component: GuideScenarioView, meta: { label: '사용 가이드' } },
  { path: '/analysis-set', component: AnalysisSetView, meta: { label: '분석 물량' } },
  { path: '/bin-group', component: BinGroupView, meta: { label: 'BIN Group' } },
  { path: '/condition-rule', component: ConditionRuleView, meta: { label: '조건 Rule' } },
  { path: '/window-review', component: WindowReviewView, meta: { label: 'Window Review' } },
  { path: '/pending-prediction', component: PendingPredictionView, meta: { label: 'Pending 예측' } },
  { path: '/export-report', component: ExportReportView, meta: { label: 'Export / Report' } },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
