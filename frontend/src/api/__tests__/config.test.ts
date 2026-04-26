import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as config from '../config'

vi.mock('../client', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
  extractData: vi.fn((promise) => promise.then((r: { data: { success: boolean; data: unknown } }) => {
    if (!r.data.success) throw new Error('fail')
    return r.data.data
  })),
}))

import client from '../client'

const mockClient = vi.mocked(client)

describe('config API', () => {
  beforeEach(() => vi.clearAllMocks())

  it('fetchConfigs calls correct endpoint', async () => {
    mockClient.get.mockResolvedValue({ data: { success: true, data: [] } })

    await config.fetchConfigs()

    expect(mockClient.get).toHaveBeenCalledWith('/ai/configs/')
  })

  it('createConfig posts to configs endpoint', async () => {
    mockClient.post.mockResolvedValue({ data: { success: true, data: { id: 'c1' } } })

    await config.createConfig({
      provider: 'openai', display_name: 'Test', model_name: 'gpt-4o',
      base_url: '', api_key: 'sk-test', is_default: true, is_active: true,
    })

    expect(mockClient.post).toHaveBeenCalledWith('/ai/configs/', {
      provider: 'openai', display_name: 'Test', model_name: 'gpt-4o',
      base_url: '', api_key: 'sk-test', is_default: true, is_active: true,
    })
  })

  it('updateConfig patches specific config', async () => {
    mockClient.patch.mockResolvedValue({ data: { success: true, data: { id: 'c1' } } })

    await config.updateConfig('c1', { display_name: 'Updated' })

    expect(mockClient.patch).toHaveBeenCalledWith('/ai/configs/c1/', { display_name: 'Updated' })
  })

  it('deleteConfig deletes specific config', async () => {
    mockClient.delete.mockResolvedValue({ data: { success: true, data: { message: 'ok' } } })

    await config.deleteConfig('c1')

    expect(mockClient.delete).toHaveBeenCalledWith('/ai/configs/c1/')
  })

  it('testConnection posts to test endpoint', async () => {
    mockClient.post.mockResolvedValue({ data: { success: true, data: { success: true, message: 'ok', model_name: 'gpt-4o' } } })

    await config.testConnection({ config_id: 'c1' })

    expect(mockClient.post).toHaveBeenCalledWith('/ai/configs/test-connection/', { config_id: 'c1' })
  })
})
