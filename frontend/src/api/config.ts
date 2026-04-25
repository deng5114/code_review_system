import client, { extractData } from './client'
import type { AIConfig, AIConfigCreate, TestConnectionResult, TestConnectionRequest } from '../types'

export function fetchConfigs() {
  return extractData<AIConfig[]>(client.get('/ai/configs/'))
}

export function createConfig(data: AIConfigCreate) {
  return extractData<AIConfig>(client.post('/ai/configs/', data))
}

export function updateConfig(id: string, data: Partial<AIConfigCreate>) {
  return extractData<AIConfig>(client.patch(`/ai/configs/${id}/`, data))
}

export function deleteConfig(id: string) {
  return extractData<{ message: string }>(client.delete(`/ai/configs/${id}/`))
}

export function testConnection(params: TestConnectionRequest) {
  return extractData<TestConnectionResult>(client.post('/ai/configs/test-connection/', params))
}
