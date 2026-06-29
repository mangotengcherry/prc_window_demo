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
  }),
  actions: {
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
