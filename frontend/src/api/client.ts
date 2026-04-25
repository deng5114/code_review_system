import axios from 'axios'
import type { ApiResponse } from '../types'

const client = axios.create({
  baseURL: '/api',
  timeout: 120000,
})

client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.data?.error) {
      return Promise.reject(new Error(error.response.data.error.message))
    }
    if (error.response?.data?.detail) {
      return Promise.reject(new Error(error.response.data.detail))
    }
    return Promise.reject(error)
  },
)

export async function extractData<T>(promise: Promise<{ data: ApiResponse<T> }>): Promise<T> {
  const { data } = await promise
  if (!data.success) {
    throw new Error(data.error?.message ?? '请求失败')
  }
  return data.data
}

export default client
