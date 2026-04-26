import { describe, it, expect } from 'vitest'
import { buildFileTree } from '../fileTree'
import type { ProjectFile, ReviewIssue } from '../../types'

const makeFile = (overrides: Partial<ProjectFile> & { id: string; file_path: string }): ProjectFile => ({
  project: 'proj-1',
  file_path: overrides.file_path,
  language: overrides.language ?? 'python',
  line_count: overrides.line_count ?? 10,
  is_vendor: false,
  is_generated: false,
  ...overrides,
})

const makeIssue = (file_path: string): ReviewIssue => ({
  id: `issue-${file_path}`,
  review: 'rev-1',
  file_path,
  start_line: 1,
  end_line: 5,
  severity: 'high',
  dimension: 'security',
  title: 'Test issue',
  description: 'desc',
  suggestion: '',
  code_snippet: '',
  fix_snippet: '',
  confidence: 0.9,
  created_at: '',
  updated_at: '',
})

describe('buildFileTree', () => {
  it('returns empty array for no files', () => {
    expect(buildFileTree([])).toEqual([])
  })

  it('creates leaf nodes for flat files', () => {
    const files = [
      makeFile({ id: 'f1', file_path: 'app.py' }),
      makeFile({ id: 'f2', file_path: 'utils.py' }),
    ]
    const tree = buildFileTree(files)

    expect(tree).toHaveLength(2)
    expect(tree[0].title).toBe('app.py')
    expect(tree[0].isLeaf).toBe(true)
    expect(tree[1].title).toBe('utils.py')
  })

  it('creates nested folders for paths with slashes', () => {
    const files = [makeFile({ id: 'f1', file_path: 'src/app.py' })]
    const tree = buildFileTree(files)

    expect(tree).toHaveLength(1)
    expect(tree[0].title).toBe('src')
    expect(tree[0].isLeaf).toBeUndefined()
    expect(tree[0].children).toHaveLength(1)
    expect(tree[0].children![0].title).toBe('app.py')
  })

  it('handles deeply nested paths', () => {
    const files = [makeFile({ id: 'f1', file_path: 'src/components/ui/Button.tsx' })]
    const tree = buildFileTree(files)

    expect(tree[0].title).toBe('src')
    expect(tree[0].children![0].title).toBe('components')
    expect(tree[0].children![0].children![0].title).toBe('ui')
    expect(tree[0].children![0].children![0].children![0].title).toBe('Button.tsx')
  })

  it('shares folder nodes for files in same directory', () => {
    const files = [
      makeFile({ id: 'f1', file_path: 'src/a.py' }),
      makeFile({ id: 'f2', file_path: 'src/b.py' }),
    ]
    const tree = buildFileTree(files)

    expect(tree).toHaveLength(1)
    expect(tree[0].title).toBe('src')
    expect(tree[0].children).toHaveLength(2)
  })

  it('skips vendor files', () => {
    const files = [
      makeFile({ id: 'f1', file_path: 'app.py' }),
      makeFile({ id: 'f2', file_path: 'node_modules/lodash/index.js', is_vendor: true } as ProjectFile),
    ]
    const tree = buildFileTree(files)

    expect(tree).toHaveLength(1)
    expect(tree[0].title).toBe('app.py')
  })

  it('skips generated files', () => {
    const files = [
      makeFile({ id: 'f1', file_path: 'app.py' }),
      makeFile({ id: 'f2', file_path: 'dist/bundle.js', is_generated: true } as ProjectFile),
    ]
    const tree = buildFileTree(files)

    expect(tree).toHaveLength(1)
    expect(tree[0].title).toBe('app.py')
  })

  it('annotates leaf nodes with issue counts', () => {
    const files = [makeFile({ id: 'f1', file_path: 'app.py' })]
    const issues = [makeIssue('app.py'), makeIssue('app.py')]

    const tree = buildFileTree(files, issues)

    expect(tree[0].title).toBe('app.py (2)')
  })

  it('does not annotate files with zero issues', () => {
    const files = [makeFile({ id: 'f1', file_path: 'app.py' })]
    const issues = [makeIssue('other.py')]

    const tree = buildFileTree(files, issues)

    expect(tree[0].title).toBe('app.py')
  })

  it('stores file metadata in leaf data', () => {
    const files = [makeFile({ id: 'f1', file_path: 'app.py', language: 'python', line_count: 42 })]
    const tree = buildFileTree(files)

    expect(tree[0].data).toEqual({
      fileId: 'f1',
      filePath: 'app.py',
      language: 'python',
      lineCount: 42,
    })
  })
})
