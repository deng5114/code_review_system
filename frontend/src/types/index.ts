// === API 响应 ===

export interface ApiResponse<T> {
  success: boolean
  data: T
  error?: {
    code: string
    message: string
    status_code: number
  }
}

export interface Pagination {
  count: number
  next: string | null
  previous: string | null
}

export interface PaginatedData<T> {
  data: T[]
  pagination: Pagination
}

// === Project ===

export type ProjectStatus = 'uploading' | 'parsing' | 'ready' | 'error'
export type ProjectType = 'nodejs' | 'python' | 'go' | 'rust' | 'java' | 'typescript' | 'unknown'

export interface Project {
  id: string
  name: string
  status: ProjectStatus
  project_type: ProjectType
  detected_languages: Record<string, number>
  detected_frameworks: string[]
  total_files: number
  total_lines: number
  error_message: string | null
  files_count: number
  created_at: string
  updated_at: string
}

export interface ProjectFile {
  id: string
  file_path: string
  language: string
  line_count: number
  is_vendor: boolean
  is_generated: boolean
  file_size: number
  created_at: string
  updated_at: string
}

export interface FileContent {
  path: string
  language: string
  content: string
  line_count: number
}

// === Review ===

export type ReviewStatus = 'pending' | 'running' | 'completed' | 'failed'
export type Severity = 'critical' | 'high' | 'medium' | 'low'
export type Dimension =
  | 'security'
  | 'correctness'
  | 'performance'
  | 'maintainability'
  | 'type_safety'
  | 'completeness'
  | 'best_practices'

export interface Review {
  id: string
  project: string
  project_name: string
  status: ReviewStatus
  ai_model: string
  ai_provider: string
  progress: number
  total_issues: number
  critical_count: number
  high_count: number
  medium_count: number
  low_count: number
  summary: string
  error_message: string | null
  custom_instructions: string
  started_at: string | null
  completed_at: string | null
  created_at: string
  updated_at: string
}

export interface ReviewIssue {
  id: string
  file_path: string
  start_line: number
  end_line: number
  severity: Severity
  dimension: Dimension
  title: string
  description: string
  suggestion: string
  code_snippet: string
  fix_snippet: string
  confidence: number
  created_at: string
}

export interface IssueFilters {
  severity?: Severity[]
  dimension?: Dimension[]
  file_path?: string
  search?: string
}

// === AI Config ===

export type AIProvider = 'openai' | 'anthropic' | 'google' | 'deepseek' | 'ollama' | 'openrouter'

export interface AIConfig {
  id: string
  provider: AIProvider
  display_name: string
  masked_api_key: string
  model_name: string
  base_url: string
  is_default: boolean
  is_active: boolean
  extra_settings: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface AIConfigCreate {
  provider: AIProvider
  display_name: string
  api_key: string
  model_name: string
  base_url?: string
  is_default?: boolean
  is_active?: boolean
  extra_settings?: Record<string, unknown>
}

export interface TestConnectionResult {
  connected: boolean
  response_preview?: string
  tokens_used?: number
  error?: string
}

export interface TestConnectionRequest {
  config_id?: string
  provider?: AIProvider
  model_name?: string
  api_key?: string
  base_url?: string
}

// === Report ===

export interface ReviewReport {
  project_name: string
  ai_model: string
  summary: string
  total_issues: number
  issues: ReviewIssue[]
  stats: {
    total: number
    critical_count: number
    high_count: number
    medium_count: number
    low_count: number
  }
}

export interface MarkdownReport {
  format: 'markdown'
  content: string
}

// === TreeNode ===

export interface TreeNode {
  key: string
  title: string
  children?: TreeNode[]
  isLeaf?: boolean
  data?: {
    fileId: string
    filePath: string
    language: string
    lineCount: number
  }
}
