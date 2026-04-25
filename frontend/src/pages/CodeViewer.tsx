import { useEffect, useState, useRef, useMemo } from 'react'
import { useParams, useLocation, useNavigate } from 'react-router-dom'
import { Card, Tree, Space, Tag, Typography, Empty, Button } from 'antd'
import { ArrowLeftOutlined } from '@ant-design/icons'
import MonacoEditor, { type OnMount } from '@monaco-editor/react'
import * as monaco from 'monaco-editor'
import { useReviewStore } from '../stores/reviewStore'
import { useProjectStore } from '../stores/projectStore'
import { buildFileTree } from '../utils/fileTree'
import * as projectApi from '../api/projects'
import { SEVERITY_CONFIG, DIMENSION_LABELS } from '../utils/constants'
import type { FileContent, ReviewIssue, Severity } from '../types'

const { Title, Text, Paragraph } = Typography

const SEVERITY_MONACO_COLOR: Record<Severity, string> = {
  critical: 'rgba(255, 77, 79, 0.15)',
  high: 'rgba(250, 140, 22, 0.15)',
  medium: 'rgba(250, 219, 20, 0.12)',
  low: 'rgba(24, 144, 255, 0.10)',
}

const LANGUAGE_MAP: Record<string, string> = {
  python: 'python', javascript: 'javascript', typescript: 'typescript',
  go: 'go', rust: 'rust', java: 'java', cpp: 'cpp', c: 'c',
  html: 'html', css: 'css', json: 'json', yaml: 'yaml', markdown: 'markdown',
}

export default function CodeViewer() {
  const { id } = useParams<{ id: string }>()
  const location = useLocation()
  const navigate = useNavigate()
  const { currentReview, issues, fetchReview, fetchIssues } = useReviewStore()
  const { fileList, fetchProject, fetchFiles } = useProjectStore()

  const [selectedFile, setSelectedFile] = useState<FileContent | null>(null)
  const [selectedIssue, setSelectedIssue] = useState<ReviewIssue | null>(null)
  const [fileIssues, setFileIssues] = useState<ReviewIssue[]>([])
  const editorRef = useRef<Parameters<NonNullable<Parameters<typeof MonacoEditor>[0]['onMount']>>[0]>(null)
  const decorationsRef = useRef<string[]>([])

  const stateIssueId = (location.state as { issueId?: string })?.issueId

  useEffect(() => {
    if (!id) return
    fetchReview(id)
  }, [id])

  useEffect(() => {
    if (currentReview?.status === 'completed' && id) {
      fetchIssues(id)
    }
  }, [currentReview?.status])

  useEffect(() => {
    if (currentReview && id) {
      fetchProject(currentReview.project)
      fetchFiles(currentReview.project)
    }
  }, [currentReview])

  // Jump to issue from navigation state
  useEffect(() => {
    if (!stateIssueId || issues.length === 0) return
    const issue = issues.find((i) => i.id === stateIssueId)
    if (issue) {
      const file = fileList.find((f) => f.file_path === issue.file_path)
      if (file) loadFile(file.id, issue)
    }
  }, [stateIssueId, issues, fileList])

  const treeData = useMemo(() => buildFileTree(fileList, issues), [fileList, issues])

  const loadFile = async (fileId: string, focusIssue?: ReviewIssue) => {
    if (!currentReview) return
    try {
      const content = await projectApi.fetchFileContent(currentReview.project, fileId)
      setSelectedFile(content)
      const matching = issues.filter((i) => i.file_path === content.path)
      setFileIssues(matching)
      if (focusIssue) setSelectedIssue(focusIssue)
    } catch {
      // ignore
    }
  }

  const handleEditorMount: OnMount = (editor) => {
    editorRef.current = editor
  }

  useEffect(() => {
    const editor = editorRef.current
    if (!editor || fileIssues.length === 0) return

    const decorations = fileIssues.map((issue) => ({
      range: new monaco.Range(issue.start_line, 1, issue.end_line + 1, 1),
      options: {
        isWholeLine: true,
        inlineClassName: `issue-bg-${issue.severity}`,
        overviewRuler: {
          color: SEVERITY_CONFIG[issue.severity].color,
          position: monaco.editor.OverviewRulerLane.Full,
        },
      },
    }))

    decorationsRef.current = editor.deltaDecorations(decorationsRef.current, decorations)
  }, [selectedFile, fileIssues])

  const onSelectFile = (selectedKeys: React.Key[]) => {
    if (selectedKeys.length === 0) return
    const nodeId = selectedKeys[0] as string
    loadFile(nodeId)
  }

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Space>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(`/reviews/${id}`)}>
          返回审查结果
        </Button>
        <Title level={4} style={{ margin: 0 }}>代码查看器</Title>
      </Space>

      <div style={{ display: 'flex', gap: 16 }}>
        <Card
          title="文件树"
          style={{ width: 280, flexShrink: 0 }}
          bodyStyle={{ padding: 8, maxHeight: 'calc(100vh - 220px)', overflow: 'auto' }}
        >
          {treeData.length > 0 ? (
            <Tree treeData={treeData} onSelect={onSelectFile} defaultExpandAll={false} />
          ) : (
            <Empty description="无文件" />
          )}
        </Card>

        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 12 }}>
          <Card
            title={selectedFile ? selectedFile.path : '选择文件'}
            bodyStyle={{ padding: 0 }}
          >
            {selectedFile ? (
              <div style={{ height: 'calc(100vh - 400px)', minHeight: 400 }}>
                <MonacoEditor
                  height="100%"
                  language={LANGUAGE_MAP[selectedFile.language] || 'plaintext'}
                  value={selectedFile.content}
                  theme="vs"
                  options={{
                    readOnly: true,
                    minimap: { enabled: false },
                    lineNumbers: 'on',
                    scrollBeyondLastLine: false,
                    automaticLayout: true,
                  }}
                  onMount={handleEditorMount}
                />
              </div>
            ) : (
              <Empty description="点击左侧文件树选择文件" style={{ padding: 40 }} />
            )}
          </Card>

          {selectedIssue && (
            <Card
              title={
                <Space>
                  <Tag color={SEVERITY_CONFIG[selectedIssue.severity].color}>
                    {SEVERITY_CONFIG[selectedIssue.severity].label}
                  </Tag>
                  <Tag>{DIMENSION_LABELS[selectedIssue.dimension]}</Tag>
                  <Text>{selectedIssue.title}</Text>
                </Space>
              }
              extra={<Button size="small" onClick={() => setSelectedIssue(null)}>关闭</Button>}
            >
              <Paragraph>{selectedIssue.description}</Paragraph>
              {selectedIssue.suggestion && (
                <>
                  <Text strong>修复建议:</Text>
                  <Paragraph>{selectedIssue.suggestion}</Paragraph>
                </>
              )}
              {selectedIssue.code_snippet && (
                <>
                  <Text strong>问题代码:</Text>
                  <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 6, overflow: 'auto' }}>
                    {selectedIssue.code_snippet}
                  </pre>
                </>
              )}
              {selectedIssue.fix_snippet && (
                <>
                  <Text strong>建议修复:</Text>
                  <pre style={{ background: '#f0fff0', padding: 12, borderRadius: 6, overflow: 'auto' }}>
                    {selectedIssue.fix_snippet}
                  </pre>
                </>
              )}
            </Card>
          )}

          {fileIssues.length > 0 && !selectedIssue && (
            <Card title={`该文件问题 (${fileIssues.length})`} size="small">
              {fileIssues.map((issue) => (
                <Card.Grid
                  key={issue.id}
                  style={{ width: '100%', cursor: 'pointer', padding: '8px 12px' }}
                  hoverable
                  onClick={() => setSelectedIssue(issue)}
                >
                  <Space>
                    <Tag color={SEVERITY_CONFIG[issue.severity].color}>
                      {SEVERITY_CONFIG[issue.severity].label}
                    </Tag>
                    <Tag>{DIMENSION_LABELS[issue.dimension]}</Tag>
                    <Text>第 {issue.start_line}-{issue.end_line} 行</Text>
                    <Text strong>{issue.title}</Text>
                  </Space>
                </Card.Grid>
              ))}
            </Card>
          )}
        </div>
      </div>

      <style>{`
        .issue-bg-critical { background-color: ${SEVERITY_MONACO_COLOR.critical} !important; }
        .issue-bg-high { background-color: ${SEVERITY_MONACO_COLOR.high} !important; }
        .issue-bg-medium { background-color: ${SEVERITY_MONACO_COLOR.medium} !important; }
        .issue-bg-low { background-color: ${SEVERITY_MONACO_COLOR.low} !important; }
      `}</style>
    </Space>
  )
}
