import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Card, Progress, Statistic, Row, Col, Space, Tag, List, Spin, Typography, Button, Empty, message,
} from 'antd'
import { CodeOutlined, ArrowLeftOutlined, DownloadOutlined, WifiOutlined, ApiOutlined } from '@ant-design/icons'
import { useReviewStore } from '../stores/reviewStore'
import { useReviewWebSocket } from '../hooks/useReviewWebSocket'
import { SEVERITY_CONFIG, DIMENSION_LABELS } from '../utils/constants'
import { downloadReport } from '../api/reviews'
import FilterPanel from '../components/FilterPanel'
import SeverityBarChart from '../components/charts/SeverityBarChart'
import DimensionRadarChart from '../components/charts/DimensionRadarChart'
import type { Severity, ReviewIssue, IssueFilters } from '../types'

const { Title, Text, Paragraph } = Typography

function SeverityTag({ severity }: { severity: Severity }) {
  const cfg = SEVERITY_CONFIG[severity]
  return <Tag color={cfg.color}>{cfg.label}</Tag>
}

function IssueCard({ issue, onClickCode }: { issue: ReviewIssue; onClickCode: () => void }) {
  return (
    <Card size="small" style={{ marginBottom: 8 }}>
      <Space direction="vertical" style={{ width: '100%' }}>
        <Space wrap>
          <SeverityTag severity={issue.severity} />
          <Tag>{DIMENSION_LABELS[issue.dimension]}</Tag>
          <Text type="secondary" style={{ fontSize: 12 }}>{issue.file_path}:{issue.start_line}</Text>
        </Space>
        <Text strong>{issue.title}</Text>
        <Text type="secondary" ellipsis>{issue.description}</Text>
        <Space>
          <Button size="small" type="link" icon={<CodeOutlined />} onClick={onClickCode}>
            查看代码
          </Button>
        </Space>
      </Space>
    </Card>
  )
}

export default function ReviewDashboard() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const {
    currentReview, issues, loading,
    fetchReview, fetchIssues, pollReviewProgress, stopPolling,
    updateReviewProgress,
  } = useReviewStore()

  const [filters, setFilters] = useState<IssueFilters>({})
  const [exporting, setExporting] = useState(false)
  const allIssuesRef = useRef<ReviewIssue[]>([])
  const wsPollingStarted = useRef(false)

  const isInProgress = currentReview?.status === 'pending' || currentReview?.status === 'running'

  const { status: wsStatus } = useReviewWebSocket({
    reviewId: id ?? '',
    onMessage: useCallback((data) => {
      if (id) updateReviewProgress(id, data)
    }, [id, updateReviewProgress]),
    enabled: isInProgress && !!id,
  })

  useEffect(() => {
    if (issues.length > 0 && !filters.severity?.length && !filters.dimension?.length && !filters.file_path && !filters.search) {
      allIssuesRef.current = issues
    }
  }, [issues])

  useEffect(() => {
    if (!id) return
    fetchReview(id)
    return () => stopPolling()
  }, [id])

  useEffect(() => {
    if (!currentReview) return
    if (currentReview.status === 'pending' || currentReview.status === 'running') {
      if (wsStatus === 'unavailable' && !wsPollingStarted.current) {
        wsPollingStarted.current = true
        pollReviewProgress(currentReview.id)
      }
    } else if (currentReview.status === 'completed') {
      fetchIssues(currentReview.id)
    }
  }, [currentReview?.status, wsStatus])

  const [initialized, setInitialized] = useState(false)

  useEffect(() => {
    if (!id || !currentReview || currentReview.status !== 'completed' || initialized) return
    setInitialized(true)
  }, [currentReview?.status])

  useEffect(() => {
    if (!id || !currentReview || currentReview.status !== 'completed' || !initialized) return
    const hasFilters = filters.severity?.length || filters.dimension?.length || filters.file_path || filters.search
    fetchIssues(id, hasFilters ? filters : undefined)
  }, [filters, initialized])

  const allIssues = allIssuesRef.current
  const availableFiles = useMemo(
    () => [...new Set((allIssues.length > 0 ? allIssues : issues).map((i) => i.file_path))].sort(),
    [allIssues, issues]
  )

  const handleFilterChange = useCallback((newFilters: IssueFilters) => {
    setFilters(newFilters)
  }, [])

  const handleExport = useCallback(async () => {
    if (!currentReview) return
    setExporting(true)
    try {
      await downloadReport(currentReview.id, currentReview.project_name)
      message.success('报告已导出')
    } catch {
      message.error('导出失败')
    } finally {
      setExporting(false)
    }
  }, [currentReview])

  if (loading && !currentReview) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />
  if (!currentReview) return <Text>审查不存在</Text>

  const isCompleted = currentReview.status === 'completed'
  const isFailed = currentReview.status === 'failed'

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card>
        <Space style={{ marginBottom: 16 }}>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(`/projects/${currentReview.project}`)}>
            返回项目
          </Button>
          <Title level={4} style={{ margin: 0 }}>
            代码审查 — {currentReview.project_name}
          </Title>
          <Tag color={isCompleted ? 'green' : isInProgress ? 'blue' : 'red'}>
            {isInProgress ? '进行中' : isCompleted ? '已完成' : '失败'}
          </Tag>
          {isCompleted && (
            <Button
              icon={<DownloadOutlined />}
              onClick={handleExport}
              loading={exporting}
            >
              导出报告
            </Button>
          )}
        </Space>

        {isInProgress && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <Progress
              percent={currentReview.progress}
              status="active"
              style={{ flex: 1 }}
            />
            <Space size={4}>
              {wsStatus === 'connected' && (
                <Tag icon={<WifiOutlined />} color="success">实时</Tag>
              )}
              {wsStatus === 'unavailable' && (
                <Tag icon={<ApiOutlined />} color="warning">轮询</Tag>
              )}
            </Space>
          </div>
        )}

        {isFailed && (
          <Card type="inner" style={{ background: '#fff2f0' }}>
            <Text type="danger">审查失败: {currentReview.error_message}</Text>
          </Card>
        )}

        {isCompleted && (
          <Row gutter={16}>
            <Col span={4}><Statistic title="问题总数" value={currentReview.total_issues} /></Col>
            <Col span={4}><Statistic title="严重" value={currentReview.critical_count} valueStyle={{ color: SEVERITY_CONFIG.critical.color }} /></Col>
            <Col span={4}><Statistic title="高级" value={currentReview.high_count} valueStyle={{ color: SEVERITY_CONFIG.high.color }} /></Col>
            <Col span={4}><Statistic title="中级" value={currentReview.medium_count} valueStyle={{ color: SEVERITY_CONFIG.medium.color }} /></Col>
            <Col span={4}><Statistic title="低级" value={currentReview.low_count} valueStyle={{ color: SEVERITY_CONFIG.low.color }} /></Col>
          </Row>
        )}

        {isCompleted && currentReview.summary && (
          <Card type="inner" title="AI 总体评估" style={{ marginTop: 16 }}>
            <Paragraph>{currentReview.summary}</Paragraph>
          </Card>
        )}
      </Card>

      {isCompleted && (
        <>
          <Row gutter={16}>
            <Col span={12}>
              <Card title="严重性分布" size="small">
                <SeverityBarChart
                  critical={currentReview.critical_count}
                  high={currentReview.high_count}
                  medium={currentReview.medium_count}
                  low={currentReview.low_count}
                />
              </Card>
            </Col>
            <Col span={12}>
              <Card title="维度分布" size="small">
                <DimensionRadarChart issues={allIssues.length > 0 ? allIssues : issues} />
              </Card>
            </Col>
          </Row>

          <Card title="筛选">
            <FilterPanel
              filters={filters}
              onChange={handleFilterChange}
              availableFiles={availableFiles}
              totalIssues={currentReview.total_issues}
              filteredCount={issues.length}
            />
          </Card>

          <Card title={`问题列表 (${issues.length})`}>
            {issues.length === 0 ? (
              <Empty description="没有匹配的问题" />
            ) : (
              <List
                dataSource={issues}
                renderItem={(issue) => (
                  <IssueCard
                    issue={issue}
                    onClickCode={() => navigate(`/reviews/${id}/code`, { state: { issueId: issue.id, filePath: issue.file_path } })}
                  />
                )}
              />
            )}
          </Card>
        </>
      )}
    </Space>
  )
}
