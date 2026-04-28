import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Table, Tag, Button, Space, Input, Select, Typography, Card, Empty, message } from 'antd'
import { PlusOutlined, SearchOutlined, ReloadOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import client from '../api/client'
import type { ApiResponse, Review, ReviewStatus, PaginatedData } from '../types'

const statusMap: Record<ReviewStatus, { color: string; label: string }> = {
  pending: { color: 'default', label: '等待中' },
  running: { color: 'processing', label: '审查中' },
  completed: { color: 'success', label: '已完成' },
  failed: { color: 'error', label: '失败' },
}

export default function Home() {
  const navigate = useNavigate()
  const [reviews, setReviews] = useState<Review[]>([])
  const [loading, setLoading] = useState(false)
  const [statusFilter, setStatusFilter] = useState<ReviewStatus | undefined>()
  const [search, setSearch] = useState('')
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20, total: 0 })

  const fetchReviews = async (page = 1, pageSize = 20) => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
      if (statusFilter) params.set('status', statusFilter)
      const res = await client.get<ApiResponse<PaginatedData<Review> | Review[]>>(
        `/reviews/?${params.toString()}`,
      )
      const raw = res.data
      if (raw.success && Array.isArray(raw.data)) {
        const pag = (raw as ApiResponse<PaginatedData<Review>>).pagination
        const items = raw.data
        setReviews(items)
        if (pag) {
          setPagination({ current: page, pageSize, total: pag.count })
        } else {
          setPagination({ current: page, pageSize, total: items.length })
        }
      }
    } catch {
      message.error('加载审查记录失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchReviews()
  }, [statusFilter])

  const filtered = search
    ? reviews.filter(
        (r) =>
          r.project_name.toLowerCase().includes(search.toLowerCase()) ||
          r.ai_model.toLowerCase().includes(search.toLowerCase()),
      )
    : reviews

  const columns: ColumnsType<Review> = [
    {
      title: '项目名称',
      dataIndex: 'project_name',
      key: 'project_name',
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: ReviewStatus) => {
        const s = statusMap[status]
        return <Tag color={s.color}>{s.label}</Tag>
      },
    },
    {
      title: 'AI 模型',
      dataIndex: 'ai_model',
      key: 'ai_model',
      width: 150,
      ellipsis: true,
    },
    {
      title: '问题数',
      key: 'issues',
      width: 200,
      render: (_, record) => {
        if (record.status !== 'completed') return '-'
        return (
          <Space size={4}>
            {record.critical_count > 0 && <Tag color="red">{record.critical_count} 严重</Tag>}
            {record.high_count > 0 && <Tag color="orange">{record.high_count} 高</Tag>}
            {record.medium_count > 0 && <Tag color="gold">{record.medium_count} 中</Tag>}
            {record.low_count > 0 && <Tag color="blue">{record.low_count} 低</Tag>}
            {record.total_issues === 0 && <Tag>无问题</Tag>}
          </Space>
        )
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (v: string) => new Date(v).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_, record) => (
        <Button
          type="link"
          onClick={() => navigate(`/reviews/${record.id}`)}
          disabled={record.status === 'pending'}
        >
          查看
        </Button>
      ),
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>
          审查记录
        </Typography.Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/upload')}>
          上传新项目
        </Button>
      </div>

      <Card>
        <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
          <Input
            prefix={<SearchOutlined />}
            placeholder="搜索项目名称或模型"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ width: 280 }}
            allowClear
          />
          <Select
            placeholder="状态筛选"
            value={statusFilter}
            onChange={(v) => setStatusFilter(v)}
            style={{ width: 140 }}
            allowClear
            options={[
              { label: '等待中', value: 'pending' },
              { label: '审查中', value: 'running' },
              { label: '已完成', value: 'completed' },
              { label: '失败', value: 'failed' },
            ]}
          />
          <Button icon={<ReloadOutlined />} onClick={() => fetchReviews(pagination.current)}>
            刷新
          </Button>
        </div>

        <Table<Review>
          rowKey="id"
          columns={columns}
          dataSource={filtered}
          loading={loading}
          locale={{ emptyText: <Empty description="暂无审查记录，点击右上角上传项目开始使用" /> }}
          pagination={{
            ...pagination,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (page, pageSize) => fetchReviews(page, pageSize),
          }}
        />
      </Card>
    </div>
  )
}
