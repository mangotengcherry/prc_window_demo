import { defineStore } from 'pinia'
import { createAnalysisSet, fetchAnalysisSets, fetchMetadata, resetMockData } from '../api/analysisApi'

const defaultFilters = () => ({
  product: ['KCAI'],
  layer: ['M1'],
  step: ['CR860200'],
  parameter: ['metro_ch_hole_cd'],
  tool: [],
  chamber: [],
  ppid: [],
  eco: [],
  eds_status: 'include_pending',
  exclude_rework: true,
  exclude_engineering_lot: true,
  exclude_abnormal_route: true,
})

export const useAnalysisSetStore = defineStore('analysisSet', {
  state: () => ({
    metadata: null as any,
    analysisSets: [] as any[],
    selectedAnalysisSetId: '',
    loading: false,
  }),
  getters: {
    selectedAnalysisSet(state) {
      return state.analysisSets.find((item) => item.id === state.selectedAnalysisSetId) || state.analysisSets[0] || null
    },
  },
  actions: {
    async loadMetadata() {
      this.metadata = await fetchMetadata()
    },
    async loadAnalysisSets() {
      this.analysisSets = await fetchAnalysisSets()
      if (!this.selectedAnalysisSetId && this.analysisSets.length) this.selectedAnalysisSetId = this.analysisSets[0].id
    },
    async createDefault() {
      const item = await createAnalysisSet({
        name: '기본 Ch.Hole Window 점검',
        filters: defaultFilters(),
      })
      await this.loadAnalysisSets()
      this.selectedAnalysisSetId = item.id
      return item
    },
    async create(payload: any) {
      const item = await createAnalysisSet(payload)
      await this.loadAnalysisSets()
      this.selectedAnalysisSetId = item.id
      return item
    },
    async reset() {
      await resetMockData()
      await this.loadMetadata()
      await this.loadAnalysisSets()
    },
  },
})

export { defaultFilters }
