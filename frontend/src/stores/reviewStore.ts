import { create } from 'zustand'
import * as api from '../api/reviews'
import type { Review, ReviewIssue, IssueFilters } from '../types'
import { POLL_INTERVAL } from '../utils/constants'

interface ReviewStore {
  reviews: Review[]
  currentReview: Review | null
  issues: ReviewIssue[]
  filters: IssueFilters
  loading: boolean
  creating: boolean
  polling: boolean
  startReview: (projectId: string, customInstructions?: string) => Promise<Review>
  fetchReview: (id: string) => Promise<void>
  fetchIssues: (reviewId: string, filters?: IssueFilters) => Promise<void>
  setFilters: (filters: Partial<IssueFilters>) => void
  resetFilters: () => void
  pollReviewProgress: (id: string) => void
  stopPolling: () => void
}

let pollingTimer: ReturnType<typeof setInterval> | null = null

export const useReviewStore = create<ReviewStore>((set, get) => ({
  reviews: [],
  currentReview: null,
  issues: [],
  filters: {},
  loading: false,
  creating: false,
  polling: false,

  startReview: async (projectId, customInstructions) => {
    set({ creating: true })
    try {
      const review = await api.createReview(projectId, customInstructions)
      set((s) => ({ reviews: [review, ...s.reviews], currentReview: review, creating: false }))
      return review
    } catch (e) {
      set({ creating: false })
      throw e
    }
  },

  fetchReview: async (id) => {
    set({ loading: true })
    try {
      const review = await api.fetchReview(id)
      set({ currentReview: review, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  fetchIssues: async (reviewId, filters) => {
    set({ loading: true })
    try {
      const result = await api.fetchIssues(reviewId, filters ?? get().filters)
      set({ issues: result.data, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  setFilters: (filters) => {
    set((s) => ({ filters: { ...s.filters, ...filters } }))
  },

  resetFilters: () => set({ filters: {} }),

  pollReviewProgress: (id) => {
    if (pollingTimer) clearInterval(pollingTimer)
    set({ polling: true })

    const poll = async () => {
      try {
        const review = await api.fetchReview(id)
        set({ currentReview: review })

        if (review.status === 'completed' || review.status === 'failed') {
          get().stopPolling()
          if (review.status === 'completed') {
            await get().fetchIssues(id)
          }
        }
      } catch {
        get().stopPolling()
      }
    }

    pollingTimer = setInterval(poll, POLL_INTERVAL)
    poll()
  },

  stopPolling: () => {
    if (pollingTimer) {
      clearInterval(pollingTimer)
      pollingTimer = null
    }
    set({ polling: false })
  },
}))
