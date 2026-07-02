import { defineStore } from 'pinia'
import {
  addPresetRevision,
  createPreset,
  createPresetFolder,
  deletePreset,
  duplicatePreset,
  fetchPresetRevision,
  fetchPresetTree,
  patchPreset,
} from '../api/analysisApi'

export function currentUser() {
  return localStorage.getItem('workbench_user') || 'me'
}

export const usePresetStore = defineStore('preset', {
  state: () => ({
    tree: { folders: [] as any[] },
    scopeFilter: 'all' as 'personal' | 'shared' | 'all',
    loadedPreset: null as { id: string; name: string; rev: number; folderName: string; scope: string; owner: string } | null,
    dirty: false,
  }),
  actions: {
    async loadTree() {
      this.tree = await fetchPresetTree()
    },
    async createFolder(name: string) {
      await createPresetFolder(name)
      await this.loadTree()
    },
    async create(payload: any) {
      const preset = await createPreset(payload)
      await this.loadTree()
      return preset
    },
    async addRevision(presetId: string, payload: any) {
      const preset = await addPresetRevision(presetId, payload)
      await this.loadTree()
      return preset
    },
    async duplicate(presetId: string, payload: any) {
      const preset = await duplicatePreset(presetId, payload)
      await this.loadTree()
      return preset
    },
    async setScope(presetId: string, scope: 'personal' | 'shared') {
      await patchPreset(presetId, { scope })
      await this.loadTree()
    },
    async rename(presetId: string, name: string) {
      await patchPreset(presetId, { name })
      await this.loadTree()
    },
    async remove(presetId: string) {
      await deletePreset(presetId)
      await this.loadTree()
    },
    async fetchRevision(presetId: string, rev: number) {
      return fetchPresetRevision(presetId, rev)
    },
    markLoaded(info: { id: string; name: string; rev: number; folderName: string; scope: string; owner: string }) {
      this.loadedPreset = info
      this.dirty = false
    },
    markDirty() {
      if (this.loadedPreset) this.dirty = true
    },
  },
})
