import { defineStore } from 'pinia'
import { createExclusionRule, fetchExclusionRules, fetchPendingPrediction, fetchReport, fetchWindowReview } from '../api/analysisApi'

export const useWindowReviewStore = defineStore('windowReview', {
  state: () => ({
    review: null as any,
    prediction: null as any,
    exclusions: [] as any[],
    report: null as any,
    loading: false,
    lastRequest: null as any,
    viewOptions: {
      bins: 8,
      y_axis_metric: null as string | null,
      interaction_x: null as string | null,
      interaction_y: null as string | null,
    },
  }),
  actions: {
    setViewOption(key: 'bins' | 'y_axis_metric' | 'interaction_x' | 'interaction_y', value: any) {
      ;(this.viewOptions as any)[key] = value
    },
    async runReview(payload: any) {
      this.loading = true
      try {
        this.lastRequest = payload
        this.review = await fetchWindowReview(payload)
        return this.review
      } finally {
        this.loading = false
      }
    },
    async saveExclusion(payload: any) {
      const item = await createExclusionRule(payload)
      await this.loadExclusions()
      return item
    },
    async loadExclusions() {
      this.exclusions = await fetchExclusionRules()
    },
    async runPrediction(payload: any) {
      this.loading = true
      try {
        this.prediction = await fetchPendingPrediction(payload)
        return this.prediction
      } finally {
        this.loading = false
      }
    },
    async loadReport(runId: string) {
      this.report = await fetchReport(runId)
      return this.report
    },
  },
})
