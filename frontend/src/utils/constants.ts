import type { Severity, Dimension, AIProvider } from '../types'

export const SEVERITY_CONFIG: Record<Severity, { label: string; color: string; bg: string }> = {
  critical: { label: '严重', color: '#cf1322', bg: '#fff1f0' },
  high: { label: '高级', color: '#d46b08', bg: '#fff7e6' },
  medium: { label: '中级', color: '#d4b106', bg: '#fffbe6' },
  low: { label: '低级', color: '#0958d9', bg: '#e6f4ff' },
}

export const DIMENSION_LABELS: Record<Dimension, string> = {
  security: '安全性',
  correctness: '正确性',
  performance: '性能',
  maintainability: '可维护性',
  type_safety: '类型安全',
  completeness: '完整性',
  best_practices: '最佳实践',
}

export const PROVIDER_LABELS: Record<AIProvider, string> = {
  openai: 'OpenAI',
  anthropic: 'Anthropic',
  google: 'Google',
  deepseek: 'DeepSeek',
  ollama: 'Ollama',
  openrouter: 'OpenRouter',
}

export const PROVIDER_MODELS: Record<AIProvider, string[]> = {
  openai: ['gpt-4o', 'gpt-4o-mini', 'o3', 'o4-mini'],
  anthropic: ['claude-sonnet-4-6', 'claude-opus-4-7', 'claude-haiku-4-5-20251001'],
  google: ['gemini-2.5-pro', 'gemini-2.5-flash'],
  deepseek: ['deepseek-chat', 'deepseek-coder'],
  ollama: ['qwen3', 'llama3', 'codellama', 'mistral'],
  openrouter: ['anthropic/claude-sonnet-4-6', 'openai/gpt-4o'],
}

export const UPLOAD_ACCEPT = '.zip,.tar.gz,.tar.bz2'
export const MAX_UPLOAD_SIZE = 100 * 1024 * 1024 // 100MB
export const POLL_INTERVAL = 3000 // 3s
