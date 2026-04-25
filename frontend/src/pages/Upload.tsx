import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload as AntUpload, Button, Card, List, message, Space, Typography } from 'antd'
import { InboxOutlined, DeleteOutlined, EyeOutlined } from '@ant-design/icons'
import { useProjectStore } from '../stores/projectStore'
import { UPLOAD_ACCEPT, MAX_UPLOAD_SIZE } from '../utils/constants'

const { Dragger } = AntUpload
const { Title, Text } = Typography

export default function Upload() {
  const navigate = useNavigate()
  const { projects, uploading, uploadFile, fetchProjects, deleteProject } = useProjectStore()
  const [file, setFile] = useState<File | null>(null)

  useEffect(() => {
    fetchProjects()
  }, [fetchProjects])

  const handleUpload = async () => {
    if (!file) return
    const name = file.name.replace(/\.(zip|tar\.gz|tar\.bz2)$/, '')
    try {
      const project = await uploadFile(name, file)
      message.success('上传成功')
      setFile(null)
      navigate(`/projects/${project.id}`)
    } catch (e) {
      message.error((e as Error).message || '上传失败')
    }
  }

  const beforeUpload = (f: File) => {
    if (f.size > MAX_UPLOAD_SIZE) {
      message.error('文件大小不能超过 100MB')
      return AntUpload.LIST_IGNORE
    }
    setFile(f)
    return false
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card>
        <Title level={4} style={{ marginBottom: 24 }}>上传代码项目</Title>
        <Dragger
          accept={UPLOAD_ACCEPT}
          beforeUpload={beforeUpload}
          showUploadList={!!file}
          maxCount={1}
          onRemove={() => setFile(null)}
        >
          <p><InboxOutlined style={{ fontSize: 48, color: '#1677ff' }} /></p>
          <p>点击或拖拽文件到此区域上传</p>
          <Text type="secondary">支持 .zip / .tar.gz / .tar.bz2，最大 100MB</Text>
        </Dragger>
        {file && (
          <div style={{ marginTop: 16, textAlign: 'center' }}>
            <Button type="primary" loading={uploading} onClick={handleUpload} size="large">
              开始上传并解析
            </Button>
          </div>
        )}
      </Card>

      {projects.length > 0 && (
        <Card title="最近项目">
          <List
            dataSource={projects}
            renderItem={(project) => (
              <List.Item
                actions={[
                  <Button type="link" icon={<EyeOutlined />} onClick={() => navigate(`/projects/${project.id}`)}>
                    查看
                  </Button>,
                  <Button
                    type="link"
                    danger
                    icon={<DeleteOutlined />}
                    onClick={async () => {
                      try {
                        await deleteProject(project.id)
                        message.success('已删除')
                      } catch (e) {
                        message.error((e as Error).message || '删除失败')
                      }
                    }}
                  >
                    删除
                  </Button>,
                ]}
              >
                <List.Item.Meta
                  title={project.name}
                  description={`${project.project_type} | ${project.total_files} 文件 | ${project.total_lines} 行`}
                />
              </List.Item>
            )}
          />
        </Card>
      )}
    </Space>
  )
}
