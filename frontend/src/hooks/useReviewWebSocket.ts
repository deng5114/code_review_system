import { useCallback, useEffect, useRef, useState } from 'react'

export type WebSocketStatus = 'connecting' | 'connected' | 'disconnected' | 'unavailable'

export interface ReviewProgressMessage {
  type: 'review_progress'
  progress: number
  status: string
  message: string
}

interface UseReviewWebSocketOptions {
  reviewId: string
  onMessage: (data: ReviewProgressMessage) => void
  enabled?: boolean
  maxRetries?: number
}

interface UseReviewWebSocketReturn {
  status: WebSocketStatus
  reconnect: () => void
}

function buildWebSocketUrl(reviewId: string): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host || 'localhost:8000'
  return `${protocol}//${host}/ws/reviews/${reviewId}/progress/`
}

export function useReviewWebSocket({
  reviewId,
  onMessage,
  enabled = true,
  maxRetries = 5,
}: UseReviewWebSocketOptions): UseReviewWebSocketReturn {
  const [status, setStatus] = useState<WebSocketStatus>('disconnected')
  const wsRef = useRef<WebSocket | null>(null)
  const retriesRef = useRef(0)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const onMessageRef = useRef(onMessage)

  onMessageRef.current = onMessage

  const cleanup = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
    if (wsRef.current) {
      wsRef.current.onopen = null
      wsRef.current.onclose = null
      wsRef.current.onerror = null
      wsRef.current.onmessage = null
      if (wsRef.current.readyState === WebSocket.OPEN ||
          wsRef.current.readyState === WebSocket.CONNECTING) {
        wsRef.current.close()
      }
      wsRef.current = null
    }
  }, [])

  const connect = useCallback(() => {
    if (!enabled || !reviewId) return

    cleanup()
    setStatus('connecting')

    const url = buildWebSocketUrl(reviewId)
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      retriesRef.current = 0
      setStatus('connected')
    }

    ws.onmessage = (event: MessageEvent) => {
      try {
        const data: ReviewProgressMessage = JSON.parse(event.data)
        onMessageRef.current(data)
      } catch {
        // Ignore malformed messages
      }
    }

    ws.onclose = () => {
      setStatus('disconnected')

      // Auto-reconnect with exponential backoff
      if (enabled && retriesRef.current < maxRetries) {
        const delay = Math.min(1000 * 2 ** retriesRef.current, 30000)
        retriesRef.current += 1
        timerRef.current = setTimeout(connect, delay)
      } else if (retriesRef.current >= maxRetries) {
        setStatus('unavailable')
      }
    }

    ws.onerror = () => {
      // onclose will fire after onerror
    }

    // Connection timeout: mark unavailable if no open within 5s
    timerRef.current = setTimeout(() => {
      if (ws.readyState !== WebSocket.OPEN) {
        cleanup()
        setStatus('unavailable')
      }
    }, 5000)
  }, [enabled, reviewId, maxRetries, cleanup])

  useEffect(() => {
    connect()
    return cleanup
  }, [connect, cleanup])

  const reconnect = useCallback(() => {
    retriesRef.current = 0
    connect()
  }, [connect])

  return { status, reconnect }
}
