import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useReviewWebSocket } from '../useReviewWebSocket'

class MockWebSocket {
  static instances: MockWebSocket[] = []
  url: string
  readyState: number = WebSocket.CONNECTING
  onopen: ((ev: Event) => void) | null = null
  onclose: ((ev: CloseEvent) => void) | null = null
  onerror: ((ev: Event) => void) | null = null
  onmessage: ((ev: MessageEvent) => void) | null = null

  constructor(url: string) {
    this.url = url
    MockWebSocket.instances.push(this)
  }

  send = vi.fn()
  close = vi.fn(() => {
    this.readyState = WebSocket.CLOSED
    this.onclose?.({ code: 1000, reason: '' } as CloseEvent)
  })

  simulateOpen() {
    this.readyState = WebSocket.OPEN
    this.onopen?.({ type: 'open' } as Event)
  }

  simulateMessage(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) } as MessageEvent)
  }

  simulateError() {
    this.readyState = WebSocket.CLOSED
    this.onerror?.({ type: 'error' } as Event)
    this.onclose?.({ code: 1006, reason: '' } as CloseEvent)
  }
}

const originalWebSocket = globalThis.WebSocket

beforeEach(() => {
  MockWebSocket.instances = []
  vi.useFakeTimers()
  globalThis.WebSocket = MockWebSocket as any
})

afterEach(() => {
  vi.useRealTimers()
  globalThis.WebSocket = originalWebSocket
})

describe('useReviewWebSocket', () => {
  it('creates WebSocket connection on mount', () => {
    const onMessage = vi.fn()
    renderHook(() => useReviewWebSocket({ reviewId: 'r1', onMessage }))

    expect(MockWebSocket.instances).toHaveLength(1)
    expect(MockWebSocket.instances[0].url).toContain('r1')
  })

  it('reports connected status after open', () => {
    const onMessage = vi.fn()
    const { result } = renderHook(() => useReviewWebSocket({ reviewId: 'r1', onMessage }))

    act(() => {
      MockWebSocket.instances[0].simulateOpen()
    })

    expect(result.current.status).toBe('connected')
  })

  it('calls onMessage with parsed data', () => {
    const onMessage = vi.fn()
    renderHook(() => useReviewWebSocket({ reviewId: 'r1', onMessage }))

    const ws = MockWebSocket.instances[0]
    act(() => ws.simulateOpen())

    act(() => {
      ws.simulateMessage({
        type: 'review_progress', progress: 50, status: 'running', message: 'Halfway',
      })
    })

    expect(onMessage).toHaveBeenCalledWith({
      type: 'review_progress', progress: 50, status: 'running', message: 'Halfway',
    })
  })

  it('reconnects with exponential backoff on close', () => {
    const onMessage = vi.fn()
    renderHook(() => useReviewWebSocket({ reviewId: 'r1', onMessage, maxRetries: 3 }))

    const ws = MockWebSocket.instances[0]
    act(() => ws.simulateOpen())

    const initialCount = MockWebSocket.instances.length
    act(() => ws.simulateError())

    // First retry after ~1s
    act(() => { vi.advanceTimersByTime(1100) })
    expect(MockWebSocket.instances.length).toBeGreaterThan(initialCount)
  })

  it('marks unavailable after max retries', () => {
    const onMessage = vi.fn()
    const { result } = renderHook(() =>
      useReviewWebSocket({ reviewId: 'r1', onMessage, maxRetries: 2 }),
    )

    // Simulate failures until unavailable
    for (let i = 0; i <= 2; i++) {
      const ws = MockWebSocket.instances[MockWebSocket.instances.length - 1]
      act(() => {
        if (ws.readyState === WebSocket.CONNECTING) ws.simulateError()
      })
      act(() => { vi.advanceTimersByTime(35000) })
    }

    expect(result.current.status).toBe('unavailable')
  })

  it('does not connect when disabled', () => {
    const onMessage = vi.fn()
    renderHook(() => useReviewWebSocket({ reviewId: 'r1', onMessage, enabled: false }))

    expect(MockWebSocket.instances).toHaveLength(0)
  })

  it('reconnect resets retry counter', () => {
    const onMessage = vi.fn()
    const { result } = renderHook(() =>
      useReviewWebSocket({ reviewId: 'r1', onMessage, maxRetries: 1 }),
    )

    // Fail once
    act(() => MockWebSocket.instances[0].simulateError())
    act(() => { vi.advanceTimersByTime(1100) })

    // New connection succeeds
    const ws2 = MockWebSocket.instances[1]
    act(() => ws2.simulateOpen())
    expect(result.current.status).toBe('connected')

    // Fail again — should retry because counter was reset
    act(() => ws2.simulateError())
    act(() => { vi.advanceTimersByTime(1100) })

    expect(MockWebSocket.instances.length).toBeGreaterThanOrEqual(3)
  })
})
