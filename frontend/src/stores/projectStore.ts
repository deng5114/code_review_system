import { create } from 'zustand'
import * as api from '../api/projects'
import type { Project, ProjectFile } from '../types'

interface ProjectStore {
  projects: Project[]
  currentProject: Project | null
  fileList: ProjectFile[]
  uploading: boolean
  loading: boolean
  uploadFile: (name: string, file: File) => Promise<Project>
  fetchProjects: () => Promise<void>
  fetchProject: (id: string) => Promise<void>
  fetchFiles: (projectId: string) => Promise<void>
  deleteProject: (id: string) => Promise<void>
}

export const useProjectStore = create<ProjectStore>((set) => ({
  projects: [],
  currentProject: null,
  fileList: [],
  uploading: false,
  loading: false,

  uploadFile: async (name, file) => {
    set({ uploading: true })
    try {
      const project = await api.uploadProject(name, file)
      set((s) => ({ projects: [project, ...s.projects], uploading: false }))
      return project
    } catch (e) {
      set({ uploading: false })
      throw e
    }
  },

  fetchProjects: async () => {
    set({ loading: true })
    try {
      const result = await api.fetchProjects()
      set({ projects: result.data, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  fetchProject: async (id) => {
    set({ loading: true })
    try {
      const project = await api.fetchProject(id)
      set({ currentProject: project, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  fetchFiles: async (projectId) => {
    set({ loading: true })
    try {
      const files = await api.fetchProjectFiles(projectId)
      set({ fileList: files, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  deleteProject: async (id) => {
    await api.deleteProject(id)
    set((s) => ({ projects: s.projects.filter((p) => p.id !== id) }))
  },
}))
