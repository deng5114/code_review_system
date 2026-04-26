import { describe, it, expect } from 'vitest'
import {
  SEVERITY_CONFIG,
  DIMENSION_LABELS,
  PROVIDER_LABELS,
  PROVIDER_MODELS,
  UPLOAD_ACCEPT,
  MAX_UPLOAD_SIZE,
  POLL_INTERVAL,
} from '../constants'
import type { Severity, Dimension, AIProvider } from '../../types'

describe('constants', () => {
  it('SEVERITY_CONFIG has all severity levels', () => {
    const severities: Severity[] = ['critical', 'high', 'medium', 'low']
    for (const s of severities) {
      expect(SEVERITY_CONFIG[s]).toBeDefined()
      expect(SEVERITY_CONFIG[s].label).toBeTruthy()
      expect(SEVERITY_CONFIG[s].color).toBeTruthy()
    }
  })

  it('DIMENSION_LABELS has all dimensions', () => {
    const dimensions: Dimension[] = [
      'security', 'correctness', 'performance', 'maintainability',
      'type_safety', 'completeness', 'best_practices',
    ]
    for (const d of dimensions) {
      expect(DIMENSION_LABELS[d]).toBeTruthy()
    }
  })

  it('PROVIDER_LABELS and PROVIDER_MODELS have same providers', () => {
    const labelKeys = Object.keys(PROVIDER_LABELS)
    const modelKeys = Object.keys(PROVIDER_MODELS)
    expect(labelKeys.sort()).toEqual(modelKeys.sort())
  })

  it('PROVIDER_MODELS has at least one model per provider', () => {
    for (const provider of Object.keys(PROVIDER_MODELS) as AIProvider[]) {
      expect(PROVIDER_MODELS[provider].length).toBeGreaterThan(0)
    }
  })

  it('upload constants have sensible values', () => {
    expect(UPLOAD_ACCEPT).toContain('.zip')
    expect(MAX_UPLOAD_SIZE).toBe(100 * 1024 * 1024)
  })

  it('POLL_INTERVAL is positive', () => {
    expect(POLL_INTERVAL).toBeGreaterThan(0)
  })
})
