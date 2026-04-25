import { create } from 'zustand'
import * as api from '../api/config'
import type { AIConfig, AIConfigCreate, TestConnectionResult } from '../types'

interface ConfigStore {
  configs: AIConfig[]
  defaultConfig: AIConfig | null
  loading: boolean
  fetchConfigs: () => Promise<void>
  saveConfig: (data: AIConfigCreate) => Promise<void>
  updateConfig: (id: string, data: Partial<AIConfigCreate>) => Promise<void>
  deleteConfig: (id: string) => Promise<void>
  testConnection: (id: string) => Promise<TestConnectionResult>
}

export const useConfigStore = create<ConfigStore>((set) => ({
  configs: [],
  defaultConfig: null,
  loading: false,

  fetchConfigs: async () => {
    set({ loading: true })
    try {
      const configs = await api.fetchConfigs()
      const defaultConfig = configs.find((c) => c.is_default) ?? null
      set({ configs, defaultConfig, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  saveConfig: async (data) => {
    const config = await api.createConfig(data)
    set((s) => {
      const configs = [config, ...s.configs]
      const defaultConfig = config.is_default ? config : s.defaultConfig
      return { configs, defaultConfig }
    })
  },

  updateConfig: async (id, data) => {
    const config = await api.updateConfig(id, data)
    set((s) => {
      const configs = s.configs.map((c) => (c.id === id ? config : c))
      const defaultConfig = configs.find((c) => c.is_default) ?? null
      return { configs, defaultConfig }
    })
  },

  deleteConfig: async (id) => {
    await api.deleteConfig(id)
    set((s) => {
      const configs = s.configs.filter((c) => c.id !== id)
      const defaultConfig = s.defaultConfig?.id === id ? null : s.defaultConfig
      return { configs, defaultConfig }
    })
  },

  testConnection: async (id) => {
    return await api.testConnection({ config_id: id })
  },
}))
