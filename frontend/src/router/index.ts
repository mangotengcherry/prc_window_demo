import { createRouter, createWebHistory } from 'vue-router'
import AnalysisSelectionView from '../views/AnalysisSelectionView.vue'
import WindowReviewView from '../views/WindowReviewView.vue'
import ExportReportView from '../views/ExportReportView.vue'
import GuideScenarioView from '../views/GuideScenarioView.vue'

const routes = [
  { path: '/', redirect: '/analysis-selection' },
  { path: '/guide', component: GuideScenarioView, meta: { label: '사용 가이드' } },
  { path: '/analysis-selection', component: AnalysisSelectionView, meta: { label: '분석물량 선정' } },
  { path: '/analysis-set', redirect: '/analysis-selection' },
  { path: '/bin-group', redirect: '/analysis-selection' },
  { path: '/condition-rule', redirect: '/analysis-selection' },
  { path: '/window-review', component: WindowReviewView, meta: { label: 'Window Review' } },
  { path: '/pending-prediction', redirect: '/analysis-selection' },
  { path: '/export-report', component: ExportReportView, meta: { label: 'Export / Report' } },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
