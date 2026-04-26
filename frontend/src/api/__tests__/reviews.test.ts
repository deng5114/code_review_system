import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as reviews from '../reviews'

vi.mock('../client', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
    delete: vi.fn(),
  },
  extractData: vi.fn((promise) => promise.then((r: { data: { success: boolean; data: unknown } }) => {
    if (!r.data.success) throw new Error('fail')
    return r.data.data
  })),
}))

import client from '../client'

const mockClient = vi.mocked(client)

describe('reviews API', () => {
  beforeEach(() => vi.clearAllMocks())

  it('createReview sends project_id', async () => {
    mockClient.post.mockResolvedValue({ data: { success: true, data: { id: 'r1' } } })

    await reviews.createReview('proj-1', 'check security')

    expect(mockClient.post).toHaveBeenCalledWith('/reviews/', {
      project_id: 'proj-1',
      custom_instructions: 'check security',
    })
  })

  it('createReview sends empty string when no instructions', async () => {
    mockClient.post.mockResolvedValue({ data: { success: true, data: { id: 'r1' } } })

    await reviews.createReview('proj-1')

    expect(mockClient.post).toHaveBeenCalledWith('/reviews/', {
      project_id: 'proj-1',
      custom_instructions: '',
    })
  })

  it('fetchReviews passes params', async () => {
    mockClient.get.mockResolvedValue({ data: { success: true, data: { data: [] } } })

    await reviews.fetchReviews({ project_id: 'p1', page: 2 })

    expect(mockClient.get).toHaveBeenCalledWith('/reviews/', { params: { project_id: 'p1', page: 2 } })
  })

  it('fetchReview calls correct endpoint', async () => {
    mockClient.get.mockResolvedValue({ data: { success: true, data: { id: 'r1' } } })

    await reviews.fetchReview('r1')

    expect(mockClient.get).toHaveBeenCalledWith('/reviews/r1/')
  })

  it('fetchIssues joins array filters', async () => {
    mockClient.get.mockResolvedValue({ data: { success: true, data: { data: [] } } })

    await reviews.fetchIssues('r1', {
      severity: ['critical', 'high'],
      dimension: ['security'],
    })

    expect(mockClient.get).toHaveBeenCalledWith('/reviews/r1/issues/', {
      params: { severity: 'critical,high', dimension: 'security' },
    })
  })

  it('fetchIssues sends search and file_path', async () => {
    mockClient.get.mockResolvedValue({ data: { success: true, data: { data: [] } } })

    await reviews.fetchIssues('r1', { file_path: 'app.py', search: 'inject' })

    expect(mockClient.get).toHaveBeenCalledWith('/reviews/r1/issues/', {
      params: { file_path: 'app.py', search: 'inject' },
    })
  })

  it('fetchReport defaults to json', async () => {
    mockClient.get.mockResolvedValue({ data: { success: true, data: {} } })

    await reviews.fetchReport('r1')

    expect(mockClient.get).toHaveBeenCalledWith('/reviews/r1/report/', { params: { output: 'json' } })
  })

  it('fetchReport sends markdown param', async () => {
    mockClient.get.mockResolvedValue({ data: { success: true, data: {} } })

    await reviews.fetchReport('r1', 'markdown')

    expect(mockClient.get).toHaveBeenCalledWith('/reviews/r1/report/', { params: { output: 'markdown' } })
  })

  it('downloadReport creates blob link and clicks it', async () => {
    const clickSpy = vi.fn()
    const createObjectURLSpy = vi.fn(() => 'blob:mock')
    const revokeObjectURLSpy = vi.fn()

    vi.stubGlobal('URL', { createObjectURL: createObjectURLSpy, revokeObjectURL: revokeObjectURLSpy })
    vi.spyOn(document, 'createElement').mockReturnValue({
      href: '', download: '', click: clickSpy, remove: vi.fn(),
      style: {}, setAttribute: vi.fn(), getAttribute: vi.fn(),
    } as unknown as HTMLAnchorElement)
    vi.spyOn(document.body, 'appendChild').mockImplementation(((el: Node) => el))

    mockClient.get.mockResolvedValue({ data: { data: { content: '# Report' } } })

    await reviews.downloadReport('r1', 'My Project')

    expect(createObjectURLSpy).toHaveBeenCalled()
    expect(clickSpy).toHaveBeenCalled()
    expect(revokeObjectURLSpy).toHaveBeenCalledWith('blob:mock')

    vi.restoreAllMocks()
  })
})
