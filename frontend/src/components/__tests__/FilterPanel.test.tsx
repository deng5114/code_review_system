import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import FilterPanel from '../FilterPanel'

describe('FilterPanel', () => {
  const defaultProps = {
    filters: {} as Record<string, unknown>,
    onChange: vi.fn(),
    availableFiles: ['app.py', 'utils.ts'],
    totalIssues: 10,
    filteredCount: 10,
  }

  it('renders severity and dimension selects', () => {
    render(<FilterPanel {...defaultProps} />)

    expect(screen.getByText('严重性')).toBeInTheDocument()
    expect(screen.getByText('维度')).toBeInTheDocument()
  })

  it('renders search input', () => {
    render(<FilterPanel {...defaultProps} />)

    expect(screen.getByPlaceholderText('搜索标题或描述...')).toBeInTheDocument()
  })

  it('renders issue count tag', () => {
    render(<FilterPanel {...defaultProps} totalIssues={10} filteredCount={3} />)

    expect(screen.getByText(/显示 3 \/ 10 个问题/)).toBeInTheDocument()
  })

  it('renders preset buttons', () => {
    render(<FilterPanel {...defaultProps} />)

    expect(screen.getByText('仅安全问题')).toBeInTheDocument()
    expect(screen.getByText('所有关键问题')).toBeInTheDocument()
    expect(screen.getByText('清除筛选')).toBeInTheDocument()
  })

  it('calls onChange with security preset when clicked', async () => {
    const onChange = vi.fn()
    render(<FilterPanel {...defaultProps} onChange={onChange} />)

    await userEvent.click(screen.getByText('仅安全问题'))

    expect(onChange).toHaveBeenCalledWith({
      severity: ['critical', 'high'],
      dimension: ['security'],
    })
  })

  it('calls onChange with high severity preset', async () => {
    const onChange = vi.fn()
    render(<FilterPanel {...defaultProps} onChange={onChange} />)

    await userEvent.click(screen.getByText('所有关键问题'))

    expect(onChange).toHaveBeenCalledWith({
      severity: ['critical', 'high'],
    })
  })

  it('calls onChange with empty filters on clear', async () => {
    const onChange = vi.fn()
    render(<FilterPanel {...defaultProps} onChange={onChange} filters={{ severity: ['high'] } as any} />)

    await userEvent.click(screen.getByText('清除筛选'))

    expect(onChange).toHaveBeenCalledWith({})
  })
})
