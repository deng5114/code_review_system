import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useProjectStore } from '../projectStore'

vi.mock('../../api/projects', () => ({
  uploadProject: vi.fn(),
  fetchProjects: vi.fn(),
  fetchProject: vi.fn(),
  fetchProjectFiles: vi.fn(),
  deleteProject: vi.fn(),
}))

import * as api from '../../api/projects'

const mockProject = {
  id: 'p1', name: 'TestProject', status: 'ready' as const,
  project_type: 'python', created_at: '', updated_at: '',
}

describe('projectStore', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useProjectStore.setState({
      projects: [], currentProject: null, fileList: [], uploading: false, loading: false,
    })
  })

  it('uploadFile adds project to list', async () => {
    vi.mocked(api.uploadProject).mockResolvedValue(mockProject as ReturnType<typeof api.uploadProject>)

    const file = new File(['x'], 'test.zip')
    const result = await useProjectStore.getState().uploadFile('TestProject', file)

    expect(result.id).toBe('p1')
    expect(useProjectStore.getState().projects).toHaveLength(1)
    expect(useProjectStore.getState().uploading).toBe(false)
  })

  it('uploadFile resets uploading on error', async () => {
    vi.mocked(api.uploadProject).mockRejectedValue(new Error('fail'))

    await expect(useProjectStore.getState().uploadFile('X', new File([], '')))
      .rejects.toThrow('fail')
    expect(useProjectStore.getState().uploading).toBe(false)
  })

  it('fetchProjects updates projects list', async () => {
    vi.mocked(api.fetchProjects).mockResolvedValue({
      data: [mockProject],
      meta: { total: 1, page: 1, limit: 20 },
    } as Awaited<ReturnType<typeof api.fetchProjects>>)

    await useProjectStore.getState().fetchProjects()

    expect(useProjectStore.getState().projects).toHaveLength(1)
    expect(useProjectStore.getState().loading).toBe(false)
  })

  it('fetchProjects resets loading on error', async () => {
    vi.mocked(api.fetchProjects).mockRejectedValue(new Error('fail'))

    await useProjectStore.getState().fetchProjects()

    expect(useProjectStore.getState().loading).toBe(false)
    expect(useProjectStore.getState().projects).toHaveLength(0)
  })

  it('fetchProject sets currentProject', async () => {
    vi.mocked(api.fetchProject).mockResolvedValue(mockProject as Awaited<ReturnType<typeof api.fetchProject>>)

    await useProjectStore.getState().fetchProject('p1')

    expect(useProjectStore.getState().currentProject?.id).toBe('p1')
  })

  it('fetchFiles sets fileList', async () => {
    const files = [{ id: 'f1', project: 'p1', file_path: 'a.py', language: 'python', line_count: 10, is_vendor: false, is_generated: false }]
    vi.mocked(api.fetchProjectFiles).mockResolvedValue(files as Awaited<ReturnType<typeof api.fetchProjectFiles>>)

    await useProjectStore.getState().fetchFiles('p1')

    expect(useProjectStore.getState().fileList).toHaveLength(1)
  })

  it('deleteProject removes from list', async () => {
    useProjectStore.setState({ projects: [mockProject] as any })
    vi.mocked(api.deleteProject).mockResolvedValue({ message: 'ok' })

    await useProjectStore.getState().deleteProject('p1')

    expect(useProjectStore.getState().projects).toHaveLength(0)
  })
})
