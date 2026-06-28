import { defineStore } from 'pinia'
import { createBinGroup, fetchBinGroups } from '../api/analysisApi'

export const useBinGroupStore = defineStore('binGroup', {
  state: () => ({
    binGroups: [] as any[],
    selectedBinGroupIds: ['BG001', 'BG002'] as string[],
  }),
  getters: {
    selectedGroups(state) {
      return state.binGroups.filter((group) => state.selectedBinGroupIds.includes(group.id))
    },
  },
  actions: {
    async loadBinGroups() {
      this.binGroups = await fetchBinGroups()
      if (!this.selectedBinGroupIds.length && this.binGroups.length) this.selectedBinGroupIds = [this.binGroups[0].id]
    },
    async create(payload: any) {
      const item = await createBinGroup(payload)
      await this.loadBinGroups()
      this.selectedBinGroupIds = [item.id]
      return item
    },
  },
})
