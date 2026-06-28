import { defineStore } from 'pinia'
import { createConditionRule, fetchConditionRules } from '../api/analysisApi'

export const useConditionRuleStore = defineStore('conditionRule', {
  state: () => ({
    conditionRules: [] as any[],
    selectedConditionRuleId: 'CR001',
  }),
  getters: {
    selectedRule(state) {
      return state.conditionRules.find((rule) => rule.id === state.selectedConditionRuleId) || state.conditionRules[0] || null
    },
  },
  actions: {
    async loadConditionRules() {
      this.conditionRules = await fetchConditionRules()
      if (!this.selectedConditionRuleId && this.conditionRules.length) this.selectedConditionRuleId = this.conditionRules[0].id
    },
    async create(payload: any) {
      const item = await createConditionRule(payload)
      await this.loadConditionRules()
      this.selectedConditionRuleId = item.id
      return item
    },
  },
})
