import { describe, it, expect } from 'vitest'
import { extractData } from '../client'
import type { ApiResponse } from '../../types'

describe('extractData', () => {
  it('returns data on successful response', async () => {
    const promise = Promise.resolve({
      data: { success: true, data: { id: '1', name: 'test' } } as ApiResponse<{ id: string; name: string }>,
    })
    const result = await extractData(promise)
    expect(result).toEqual({ id: '1', name: 'test' })
  })

  it('throws on unsuccessful response', async () => {
    const promise = Promise.resolve({
      data: { success: false, error: { message: 'Not found' } } as ApiResponse<never>,
    })
    await expect(extractData(promise)).rejects.toThrow('Not found')
  })

  it('throws default message when no error message', async () => {
    const promise = Promise.resolve({
      data: { success: false } as ApiResponse<never>,
    })
    await expect(extractData(promise)).rejects.toThrow('请求失败')
  })
})
