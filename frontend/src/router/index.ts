import { createRouter, createWebHistory } from 'vue-router'
import AnalysisSetView from '../views/AnalysisSetView.vue'
import WindowReviewView from '../views/WindowReviewView.vue'
import PendingPredictionView from '../views/PendingPredictionView.vue'
import ExportReportView from '../views/ExportReportView.vue'
import GuideScenarioView from '../views/GuideScenarioView.vue'

const routes = [
  { path: '/', redirect: '/analysis-set' },
  { path: '/guide', component: GuideScenarioView, meta: { label: '사용 가이드' } },
  { path: '/analysis-set', component: AnalysisSetView, meta: { label: '분석대상 선정' } },
  { path: '/window-review', component: WindowReviewView, meta: { label: 'Window Review' } },
  { path: '/pending-prediction', component: PendingPredictionView, meta: { label: 'Pending 예측' } },
  { path: '/export-report', component: ExportReportView, meta: { label: 'Export / Report' } },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
