import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Tree, Button, Modal, Tag, Space, Spin, Typography, message, Row, Col, Statistic } from 'antd'
import { PlayCircleOutlined, FileOutlined } from '@ant-design/icons'
import { useProjectStore } from '../stores/projectStore'
import { useReviewStore } from '../stores/reviewStore'

import * as projectApi from '../api/projects'
import { buildFileTree } from '../utils/fileTree'
import type { FileContent, TreeNode } from '../types'

const { Title, Text } = Typography

export default function ProjectOverview() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { currentProject, fileList, loading, fetchProject, fetchFiles } = useProjectStore()
  const { startReview, creating } = useReviewStore()

  const [treeData, setTreeData] = useState<TreeNode[]>([])
  const [selectedFile, setSelectedFile] = useState<FileContent | null>(null)
  const [reviewModalOpen, setReviewModalOpen] = useState(false)

  useEffect(() => {
    if (id) {
      fetchProject(id)
      fetchFiles(id)
    }
  }, [id, fetchProject, fetchFiles])

  useEffect(() => {
    if (fileList.length > 0) {
      setTreeData(buildFileTree(fileList))
    }
  }, [fileList])

  const onSelectFile = async (selectedKeys: React.Key[]) => {
    if (!id || selectedKeys.length === 0) return
    const nodeId = selectedKeys[0] as string
    const file = fileList.find((f) => f.id === nodeId)
    if (!file) return

    try {
      const content = await projectApi.fetchFileContent(id, nodeId)
      setSelectedFile(content)
    } catch {
      message.error('加载文件失败')
    }
  }

  const handleStartReview = async () => {
    if (!id) return
    try {
      const review = await startReview(id)
      message.success('审查任务已提交')
      setReviewModalOpen(false)
      navigate(`/reviews/${review.id}`)
    } catch (e) {
      message.error((e as Error).message || '创建审查失败')
    }
  }

  if (loading && !currentProject) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />
  if (!currentProject) return <Text>项目不存在</Text>

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card>
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Title level={4} style={{ margin: 0 }}>{currentProject.name}</Title>
            <Space style={{ marginTop: 8 }} wrap>
              <Tag>{currentProject.project_type}</Tag>
              {currentProject.detected_frameworks.map((f) => <Tag key={f} color="blue">{f}</Tag>)}
              {Object.entries(currentProject.detected_languages).map(([lang, pct]) => (
                <Tag key={lang} color="green">{lang} {pct}%</Tag>
              ))}
            </Space>
          </Col>
          <Col>
            <Space>
              <Statistic title="文件数" value={currentProject.total_files} />
              <Statistic title="代码行" value={currentProject.total_lines} />
              <Button type="primary" icon={<PlayCircleOutlined />} onClick={() => setReviewModalOpen(true)}>
                发起审查
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      <Row gutter={16}>
        <Col span={6}>
          <Card title="文件树" style={{ height: '100%' }} bodyStyle={{ padding: 8, maxHeight: 600, overflow: 'auto' }}>
            {treeData.length > 0 ? (
              <Tree
                showIcon
                treeData={treeData}
                onSelect={onSelectFile}
                defaultExpandAll={false}
              />
            ) : (
              <Text type="secondary">无文件</Text>
            )}
          </Card>
        </Col>
        <Col span={18}>
          <Card
            title={selectedFile ? selectedFile.path : '选择文件查看内容'}
            style={{ height: '100%' }}
            bodyStyle={{ maxHeight: 600, overflow: 'auto' }}
          >
            {selectedFile ? (
              <pre style={{ margin: 0, fontSize: 13, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                {selectedFile.content}
              </pre>
            ) : (
              <div style={{ textAlign: 'center', padding: 40 }}>
                <FileOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />
                <p><Text type="secondary">点击左侧文件树选择文件</Text></p>
              </div>
            )}
          </Card>
        </Col>
      </Row>

      <Modal
        title="发起代码审查"
        open={reviewModalOpen}
        onOk={handleStartReview}
        onCancel={() => setReviewModalOpen(false)}
        confirmLoading={creating}
        okText="开始审查"
      >
        <p>将使用默认 AI 配置进行代码审查，可在"AI 配置"页面管理配置。</p>
      </Modal>
    </Space>
  )
}
