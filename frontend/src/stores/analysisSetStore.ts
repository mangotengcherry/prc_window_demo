import { defineStore } from 'pinia'
import {
  copyAnalysisConditionToPersonal,
  createAnalysisSet,
  createAnalysisSetFromCondition,
  fetchAnalysisConditions,
  fetchAnalysisSets,
  fetchMetadata,
  resetMockData,
  updateAnalysisCondition,
} from '../api/analysisApi'

const defaultFilters = () => ({
  product: ['DRAM_A'],
  layer: ['M1'],
  step: ['ETCH_CONTACT'],
  parameter: ['metro_ch_hole_cd'],
  tool: [],
  chamber: [],
  ppid: [],
  eco: [],
  eds_status: 'actual_only',
  exclude_rework: true,
  exclude_engineering_lot: true,
  exclude_abnormal_route: true,
})

export const useAnalysisSetStore = defineStore('analysisSet', {
  state: () => ({
    metadata: null as any,
    analysisSets: [] as any[],
    conditionLibrary: { shared: [], personal: [] } as any,
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
    async loadAnalysisConditions() {
      this.conditionLibrary = await fetchAnalysisConditions()
      return this.conditionLibrary
    },
    async copyConditionToPersonal(conditionId: string, payload: any) {
      const item = await copyAnalysisConditionToPersonal(conditionId, payload)
      await this.loadAnalysisConditions()
      return item
    },
    async updateCondition(conditionId: string, payload: any) {
      const item = await updateAnalysisCondition(conditionId, payload)
      await this.loadAnalysisConditions()
      return item
    },
    async createFromCondition(conditionId: string) {
      const item = await createAnalysisSetFromCondition(conditionId)
      await this.loadAnalysisSets()
      this.selectedAnalysisSetId = item.id
      return item
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
      await this.loadAnalysisConditions()
    },
  },
})

export { defaultFilters }
