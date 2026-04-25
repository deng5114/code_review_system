import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Card, Progress, Statistic, Row, Col, Space, Tag, List, Spin, Typography, Button, Select, Empty,
} from 'antd'
import { CodeOutlined, ArrowLeftOutlined } from '@ant-design/icons'
import { useReviewStore } from '../stores/reviewStore'
import { SEVERITY_CONFIG, DIMENSION_LABELS } from '../utils/constants'
import type { Severity, Dimension, ReviewIssue } from '../types'

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
  } = useReviewStore()

  const [severityFilter, setSeverityFilter] = useState<Severity[]>([])
  const [dimensionFilter, setDimensionFilter] = useState<Dimension[]>([])

  useEffect(() => {
    if (!id) return
    fetchReview(id)
    return () => stopPolling()
  }, [id])

  useEffect(() => {
    if (!currentReview) return
    if (currentReview.status === 'pending' || currentReview.status === 'running') {
      pollReviewProgress(currentReview.id)
    } else if (currentReview.status === 'completed') {
      fetchIssues(currentReview.id)
    }
  }, [currentReview?.status])

  useEffect(() => {
    if (!id || !currentReview || currentReview.status !== 'completed') return
    fetchIssues(id, { severity: severityFilter.length ? severityFilter : undefined, dimension: dimensionFilter.length ? dimensionFilter : undefined })
  }, [severityFilter, dimensionFilter])

  if (loading && !currentReview) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />
  if (!currentReview) return <Text>审查不存在</Text>

  const isInProgress = currentReview.status === 'pending' || currentReview.status === 'running'
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
        </Space>

        {isInProgress && (
          <Progress
            percent={currentReview.progress}
            status="active"
            format={(p) => `${p}%`}
          />
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
          <Card title="筛选">
            <Space wrap>
              <Select
                mode="multiple"
                placeholder="严重性筛选"
                style={{ minWidth: 200 }}
                value={severityFilter}
                onChange={setSeverityFilter}
                options={(Object.entries(SEVERITY_CONFIG) as [Severity, { label: string }][]).map(([k, v]) => ({
                  value: k, label: v.label,
                }))}
                allowClear
              />
              <Select
                mode="multiple"
                placeholder="维度筛选"
                style={{ minWidth: 200 }}
                value={dimensionFilter}
                onChange={setDimensionFilter}
                options={(Object.entries(DIMENSION_LABELS) as [Dimension, string][]).map(([k, v]) => ({
                  value: k, label: v,
                }))}
                allowClear
              />
            </Space>
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
