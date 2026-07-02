import { defineStore } from 'pinia'
import { createAnalysisSet, fetchAnalysisSets, fetchMetadata, fetchSelectionPreview } from '../api/analysisApi'

const defaultFabCriteria = () => ({
  products: ['KCAI'],
  step_conditions: [{ fab_step: '', date_range: { start: null, end: null }, filter_expression: '' }],
  primary_step: null as string | null,
  exclude_rework: true,
  exclude_engineering_lot: true,
  exclude_abnormal_route: true,
})

const defaultEdsCriteria = () => ({
  eds_step: 'M',
  eds_category: 'BIN',
  eds_items: [] as string[],
  date_range: { start: null, end: null },
  part_id: 'All',
  filter_expression: '',
})

const defaultChartState = () => ({
  x_axis: 'fab_time',
  legend_by: null as string | null,
  adhoc_filters: [] as string[],
  computed_columns: [] as { name: string; expression: string }[],
})

const defaultCriteria = () => ({
  fab: defaultFabCriteria(),
  eds: defaultEdsCriteria() as ReturnType<typeof defaultEdsCriteria> | null,
  chart: defaultChartState(),
})

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
    criteria: defaultCriteria(),
    preview: null as any,
    previewLoading: false,
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
    async runPreview() {
      this.previewLoading = true
      try {
        this.preview = await fetchSelectionPreview({
          fab: this.criteria.fab,
          eds: this.criteria.eds,
          chart: this.criteria.chart,
          sample_limit: 2000,
        })
      } finally {
        this.previewLoading = false
      }
    },
    async createFromCriteria(name: string) {
      const item = await createAnalysisSet({ name, criteria: this.criteria })
      await this.loadAnalysisSets()
      this.selectedAnalysisSetId = item.id
      return item
    },
    resetCriteria() {
      this.criteria = defaultCriteria()
      this.preview = null
    },
    fillSampleCriteria() {
      const metadata = this.metadata
      if (!metadata) return
      const product = metadata.products?.[0]
      const fabStep = metadata.process_modules?.[0]?.fab_steps?.[0]?.step_id || ''
      const dateRange = {
        start: metadata.date_range?.start_date ?? null,
        end: metadata.date_range?.end_date ?? null,
      }
      const edsItem = metadata.eds_items?.BIN?.[0]

      this.criteria = {
        fab: {
          ...defaultFabCriteria(),
          products: product ? [product] : [],
          step_conditions: [{ fab_step: fabStep, date_range: { ...dateRange }, filter_expression: '' }],
          primary_step: fabStep || null,
        },
        eds: {
          ...defaultEdsCriteria(),
          eds_step: 'M',
          eds_category: 'BIN',
          eds_items: edsItem ? [edsItem] : [],
          date_range: { ...dateRange },
        },
        chart: defaultChartState(),
      }
    },
  },
})

export { defaultChartState, defaultCriteria, defaultEdsCriteria, defaultFabCriteria, defaultFilters }
