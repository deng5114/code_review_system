import client, { extractData } from './client'
import type { Project, ProjectFile, FileContent, PaginatedData } from '../types'

export function uploadProject(name: string, file: File) {
  const form = new FormData()
  form.append('name', name)
  form.append('file', file)
  return extractData<Project>(client.post('/projects/', form))
}

export function fetchProjects(page = 1) {
  return extractData<PaginatedData<Project>>(client.get('/projects/', { params: { page } }))
}

export function fetchProject(id: string) {
  return extractData<Project>(client.get(`/projects/${id}/`))
}

export function fetchProjectFiles(projectId: string) {
  return extractData<ProjectFile[]>(client.get(`/projects/${projectId}/files/`))
}

export function fetchFileContent(projectId: string, fileId: string) {
  return extractData<FileContent>(client.get(`/projects/${projectId}/files/${fileId}/`))
}

export function deleteProject(id: string) {
  return extractData<{ message: string }>(client.delete(`/projects/${id}/`))
}
