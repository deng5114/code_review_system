import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useConfigStore } from '../configStore'

vi.mock('../../api/config', () => ({
  fetchConfigs: vi.fn(),
  createConfig: vi.fn(),
  updateConfig: vi.fn(),
  deleteConfig: vi.fn(),
  testConnection: vi.fn(),
}))

import * as api from '../../api/config'

const mockConfig = {
  id: 'c1', provider: 'openai', display_name: 'GPT-4o', model_name: 'gpt-4o',
  base_url: '', is_default: true, is_active: true, priority: 1, fallback_enabled: false,
  created_at: '', updated_at: '',
}

describe('configStore', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useConfigStore.setState({ configs: [], defaultConfig: null, loading: false })
  })

  it('fetchConfigs populates configs and defaultConfig', async () => {
    vi.mocked(api.fetchConfigs).mockResolvedValue([mockConfig] as Awaited<ReturnType<typeof api.fetchConfigs>>)

    await useConfigStore.getState().fetchConfigs()

    expect(useConfigStore.getState().configs).toHaveLength(1)
    expect(useConfigStore.getState().defaultConfig?.id).toBe('c1')
    expect(useConfigStore.getState().loading).toBe(false)
  })

  it('fetchConfigs sets defaultConfig to null when no default', async () => {
    vi.mocked(api.fetchConfigs).mockResolvedValue([{ ...mockConfig, is_default: false }] as any)

    await useConfigStore.getState().fetchConfigs()

    expect(useConfigStore.getState().defaultConfig).toBeNull()
  })

  it('saveConfig adds to list and updates default', async () => {
    vi.mocked(api.createConfig).mockResolvedValue(mockConfig as Awaited<ReturnType<typeof api.createConfig>>)

    await useConfigStore.getState().saveConfig({
      provider: 'openai', display_name: 'GPT-4o', model_name: 'gpt-4o',
      base_url: '', api_key: 'sk-test', is_default: true, is_active: true,
    })

    expect(useConfigStore.getState().configs).toHaveLength(1)
    expect(useConfigStore.getState().defaultConfig?.id).toBe('c1')
  })

  it('updateConfig replaces config in list', async () => {
    useConfigStore.setState({ configs: [mockConfig] as any, defaultConfig: mockConfig as any })

    const updated = { ...mockConfig, display_name: 'Updated' }
    vi.mocked(api.updateConfig).mockResolvedValue(updated as Awaited<ReturnType<typeof api.updateConfig>>)

    await useConfigStore.getState().updateConfig('c1', { display_name: 'Updated' })

    expect(useConfigStore.getState().configs[0].display_name).toBe('Updated')
  })

  it('deleteConfig removes from list', async () => {
    useConfigStore.setState({ configs: [mockConfig] as any, defaultConfig: mockConfig as any })
    vi.mocked(api.deleteConfig).mockResolvedValue({ message: 'ok' })

    await useConfigStore.getState().deleteConfig('c1')

    expect(useConfigStore.getState().configs).toHaveLength(0)
    expect(useConfigStore.getState().defaultConfig).toBeNull()
  })

  it('deleteConfig preserves default if different id', async () => {
    useConfigStore.setState({
      configs: [mockConfig, { ...mockConfig, id: 'c2', is_default: false }] as any,
      defaultConfig: mockConfig as any,
    })
    vi.mocked(api.deleteConfig).mockResolvedValue({ message: 'ok' })

    await useConfigStore.getState().deleteConfig('c2')

    expect(useConfigStore.getState().defaultConfig?.id).toBe('c1')
  })

  it('testConnection delegates to API', async () => {
    const mockResult = { success: true, message: 'ok', model_name: 'gpt-4o' }
    vi.mocked(api.testConnection).mockResolvedValue(mockResult as Awaited<ReturnType<typeof api.testConnection>>)

    const result = await useConfigStore.getState().testConnection('c1')

    expect(api.testConnection).toHaveBeenCalledWith({ config_id: 'c1' })
    expect(result.success).toBe(true)
  })
})
