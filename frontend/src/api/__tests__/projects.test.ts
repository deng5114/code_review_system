import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as projects from '../projects'

vi.mock('../client', () => {
  return {
    default: {
      post: vi.fn(),
      get: vi.fn(),
      delete: vi.fn(),
    },
    extractData: vi.fn((promise) => promise.then((r: { data: { success: boolean; data: unknown } }) => {
      if (!r.data.success) throw new Error('fail')
      return r.data.data
    })),
  }
})

import client from '../client'

const mockClient = vi.mocked(client)

describe('projects API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('uploadProject sends multipart form', async () => {
    const mockData = { success: true, data: { id: '1', name: 'Test' } }
    mockClient.post.mockResolvedValue({ data: mockData })

    const file = new File(['content'], 'test.zip', { type: 'application/zip' })
    const result = await projects.uploadProject('Test', file)

    expect(mockClient.post).toHaveBeenCalledWith('/projects/', expect.any(FormData))
    expect(result).toEqual({ id: '1', name: 'Test' })
  })

  it('fetchProjects calls correct endpoint', async () => {
    const mockData = { success: true, data: { data: [], meta: { total: 0, page: 1, limit: 20 } } }
    mockClient.get.mockResolvedValue({ data: mockData })

    await projects.fetchProjects(2)

    expect(mockClient.get).toHaveBeenCalledWith('/projects/', { params: { page: 2 } })
  })

  it('fetchProject calls correct endpoint', async () => {
    const mockData = { success: true, data: { id: 'abc', name: 'X' } }
    mockClient.get.mockResolvedValue({ data: mockData })

    await projects.fetchProject('abc')

    expect(mockClient.get).toHaveBeenCalledWith('/projects/abc/')
  })

  it('fetchProjectFiles calls correct endpoint', async () => {
    mockClient.get.mockResolvedValue({ data: { success: true, data: [] } })

    await projects.fetchProjectFiles('proj-1')

    expect(mockClient.get).toHaveBeenCalledWith('/projects/proj-1/files/')
  })

  it('fetchFileContent calls correct endpoint', async () => {
    mockClient.get.mockResolvedValue({ data: { success: true, data: {} } })

    await projects.fetchFileContent('proj-1', 'file-1')

    expect(mockClient.get).toHaveBeenCalledWith('/projects/proj-1/files/file-1/')
  })

  it('deleteProject calls correct endpoint', async () => {
    mockClient.delete.mockResolvedValue({ data: { success: true, data: { message: 'ok' } } })

    await projects.deleteProject('proj-1')

    expect(mockClient.delete).toHaveBeenCalledWith('/projects/proj-1/')
  })
})
