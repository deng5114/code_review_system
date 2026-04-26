import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useReviewStore } from '../reviewStore'

vi.mock('../../api/reviews', () => ({
  createReview: vi.fn(),
  fetchReviews: vi.fn(),
  fetchReview: vi.fn(),
  fetchIssues: vi.fn(),
  downloadReport: vi.fn(),
}))

import * as api from '../../api/reviews'

const mockReview = {
  id: 'r1', project: 'p1', project_name: 'Test',
  status: 'pending' as const, progress: 0,
  ai_model: '', ai_provider: '',
  total_issues: 0, critical_count: 0, high_count: 0, medium_count: 0, low_count: 0,
  summary: '', error_message: null,
  started_at: null, completed_at: null,
  custom_instructions: '',
  created_at: '', updated_at: '',
}

describe('reviewStore', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useReviewStore.setState({
      reviews: [], currentReview: null, issues: [], filters: {},
      loading: false, creating: false, polling: false,
    })
  })

  it('startReview adds review to list', async () => {
    vi.mocked(api.createReview).mockResolvedValue(mockReview as Awaited<ReturnType<typeof api.createReview>>)

    const result = await useReviewStore.getState().startReview('p1')

    expect(result.id).toBe('r1')
    expect(useReviewStore.getState().currentReview?.id).toBe('r1')
    expect(useReviewStore.getState().creating).toBe(false)
  })

  it('startReview resets creating on error', async () => {
    vi.mocked(api.createReview).mockRejectedValue(new Error('fail'))

    await expect(useReviewStore.getState().startReview('p1')).rejects.toThrow('fail')
    expect(useReviewStore.getState().creating).toBe(false)
  })

  it('fetchReview sets currentReview', async () => {
    vi.mocked(api.fetchReview).mockResolvedValue(mockReview as Awaited<ReturnType<typeof api.fetchReview>>)

    await useReviewStore.getState().fetchReview('r1')

    expect(useReviewStore.getState().currentReview?.id).toBe('r1')
    expect(useReviewStore.getState().loading).toBe(false)
  })

  it('fetchIssues updates issues list', async () => {
    const issues = [{ id: 'i1', file_path: 'a.py', start_line: 1, end_line: 5, severity: 'high' as const, dimension: 'security' as const, title: 'X', description: 'd', suggestion: '', code_snippet: '', fix_snippet: '', confidence: 0.9, created_at: '' }]
    vi.mocked(api.fetchIssues).mockResolvedValue({
      data: issues,
      pagination: { count: 1, next: null, previous: null },
    } as Awaited<ReturnType<typeof api.fetchIssues>>)

    await useReviewStore.getState().fetchIssues('r1')

    expect(useReviewStore.getState().issues).toHaveLength(1)
  })

  it('setFilters merges filters', () => {
    useReviewStore.getState().setFilters({ severity: ['critical'] })
    useReviewStore.getState().setFilters({ dimension: ['security'] })

    const { filters } = useReviewStore.getState()
    expect(filters.severity).toEqual(['critical'])
    expect(filters.dimension).toEqual(['security'])
  })

  it('resetFilters clears all filters', () => {
    useReviewStore.getState().setFilters({ severity: ['high'], search: 'test' })
    useReviewStore.getState().resetFilters()

    expect(useReviewStore.getState().filters).toEqual({})
  })

  it('stopPolling clears polling state', () => {
    useReviewStore.setState({ polling: true })
    useReviewStore.getState().stopPolling()
    expect(useReviewStore.getState().polling).toBe(false)
  })

  it('updateReviewProgress updates progress', () => {
    useReviewStore.setState({ currentReview: { ...mockReview, id: 'r1' } as any })

    useReviewStore.getState().updateReviewProgress('r1', {
      type: 'review_progress', progress: 50, status: 'running', message: 'Halfway',
    })

    expect(useReviewStore.getState().currentReview?.progress).toBe(50)
  })

  it('updateReviewProgress ignores different review id', () => {
    useReviewStore.setState({ currentReview: { ...mockReview, id: 'r1', progress: 0 } as any })

    useReviewStore.getState().updateReviewProgress('r2', {
      type: 'review_progress', progress: 50, status: 'running', message: '',
    })

    expect(useReviewStore.getState().currentReview?.progress).toBe(0)
  })

  it('updateReviewProgress sets status to completed', () => {
    useReviewStore.setState({ currentReview: { ...mockReview, id: 'r1' } as any })

    useReviewStore.getState().updateReviewProgress('r1', {
      type: 'review_progress', progress: 100, status: 'completed', message: 'Done',
    })

    expect(useReviewStore.getState().currentReview?.status).toBe('completed')
    expect(useReviewStore.getState().currentReview?.progress).toBe(100)
  })

  it('updateReviewProgress sets status to failed and fetches issues on completed', () => {
    vi.mocked(api.fetchIssues).mockResolvedValue({
      data: [], pagination: { count: 0, next: null, previous: null },
    } as Awaited<ReturnType<typeof api.fetchIssues>>)

    useReviewStore.setState({ currentReview: { ...mockReview, id: 'r1' } as any })

    useReviewStore.getState().updateReviewProgress('r1', {
      type: 'review_progress', progress: 100, status: 'completed', message: 'Done',
    })

    expect(api.fetchIssues).toHaveBeenCalledWith('r1', {})
  })
})
