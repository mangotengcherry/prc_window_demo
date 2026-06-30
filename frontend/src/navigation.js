import { Download, Guide, List, TrendCharts } from '@element-plus/icons-vue'

export const workbenchNavItems = [
  { path: '/guide', label: '사용 가이드', icon: Guide },
  { path: '/analysis-selection', label: '분석물량 선정', icon: List },
  { path: '/window-review', label: 'Window Review', icon: TrendCharts },
  { path: '/export-report', label: 'Export / Report', icon: Download },
]

export function getWorkbenchNavItems() {
  return workbenchNavItems
}
