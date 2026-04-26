import client, { extractData } from './client'
import type { Review, ReviewIssue, IssueFilters, ReviewReport, MarkdownReport, PaginatedData } from '../types'

export function createReview(projectId: string, customInstructions?: string) {
  return extractData<Review>(client.post('/reviews/', {
    project_id: projectId,
    custom_instructions: customInstructions || '',
  }))
}

export function fetchReviews(params?: { project_id?: string; page?: number }) {
  return extractData<PaginatedData<Review>>(client.get('/reviews/', { params }))
}

export function fetchReview(id: string) {
  return extractData<Review>(client.get(`/reviews/${id}/`))
}

export function fetchIssues(reviewId: string, filters?: IssueFilters) {
  const params: Record<string, string> = {}
  if (filters?.severity?.length) params.severity = filters.severity.join(',')
  if (filters?.dimension?.length) params.dimension = filters.dimension.join(',')
  if (filters?.file_path) params.file_path = filters.file_path
  if (filters?.search) params.search = filters.search
  return extractData<PaginatedData<ReviewIssue>>(client.get(`/reviews/${reviewId}/issues/`, { params }))
}

export function fetchReport(reviewId: string, output: 'json' | 'markdown' = 'json') {
  if (output === 'markdown') {
    return extractData<MarkdownReport>(client.get(`/reviews/${reviewId}/report/`, { params: { output: 'markdown' } }))
  }
  return extractData<ReviewReport>(client.get(`/reviews/${reviewId}/report/`, { params: { output: 'json' } }))
}

export async function downloadReport(reviewId: string, projectName: string): Promise<void> {
  const response = await client.get(`/reviews/${reviewId}/report/`, {
    params: { output: 'markdown' },
  })
  const mdContent = response.data?.data?.content ?? response.data
  const safeName = projectName.replace(/[/\\:*?"<>|]/g, '-').replace(/\s+/g, '-')
  const blob = new Blob([mdContent], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${safeName}-review-report.md`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
