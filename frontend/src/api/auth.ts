import client from './client'
import type { ApiResponse, AuthTokens, LoginRequest, RegisterRequest, User } from '../types'

export async function login(data: LoginRequest): Promise<AuthTokens> {
  const res = await client.post<AuthTokens>('/auth/login/', data)
  return res.data
}

export async function register(data: RegisterRequest): Promise<User> {
  const res = await client.post<ApiResponse<User>>('/auth/register/', data)
  return res.data.data
}

export async function refreshToken(refresh: string): Promise<AuthTokens> {
  const res = await client.post<AuthTokens>('/auth/token/refresh/', { refresh })
  return res.data
}

export async function getMe(): Promise<User> {
  const res = await client.get<ApiResponse<User>>('/auth/me/')
  return res.data.data
}
