import { useEffect, useState } from 'react'
import {
  Card, Table, Button, Modal, Form, Input, Select, Switch, Space, Tag, message, Popconfirm, Typography,
} from 'antd'
import { PlusOutlined, ApiOutlined, DeleteOutlined, EditOutlined } from '@ant-design/icons'
import { useConfigStore } from '../stores/configStore'
import { PROVIDER_LABELS, PROVIDER_MODELS } from '../utils/constants'
import type { AIConfig, AIProvider } from '../types'

const { Text } = Typography

export default function Settings() {
  const { configs, loading, fetchConfigs, saveConfig, updateConfig, deleteConfig, testConnection } = useConfigStore()
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<AIConfig | null>(null)
  const [testing, setTesting] = useState<string | null>(null)
  const [form] = Form.useForm()

  useEffect(() => {
    fetchConfigs()
  }, [fetchConfigs])

  const openCreate = () => {
    setEditing(null)
    form.resetFields()
    setModalOpen(true)
  }

  const openEdit = (config: AIConfig) => {
    setEditing(config)
    form.setFieldsValue({
      provider: config.provider,
      display_name: config.display_name,
      model_name: config.model_name,
      base_url: config.base_url,
      is_default: config.is_default,
      is_active: config.is_active,
    })
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    const values = await form.validateFields()
    try {
      if (editing) {
        await updateConfig(editing.id, values)
        message.success('配置已更新')
      } else {
        await saveConfig(values)
        message.success('配置已添加')
      }
      setModalOpen(false)
      form.resetFields()
    } catch (e) {
      message.error((e as Error).message || '操作失败')
    }
  }

  const handleTest = async (id: string) => {
    setTesting(id)
    try {
      const result = await testConnection(id)
      if (result.connected) {
        message.success(`连接成功 ${result.tokens_used ? `(${result.tokens_used} tokens)` : ''}`)
      } else {
        message.error(`连接失败: ${result.error}`)
      }
    } catch (e) {
      message.error((e as Error).message)
    } finally {
      setTesting(null)
    }
  }

  const provider = Form.useWatch('provider', form) as AIProvider | undefined

  const columns = [
    { title: '名称', dataIndex: 'display_name', key: 'name' },
    { title: '提供商', dataIndex: 'provider', key: 'provider', render: (v: AIProvider) => PROVIDER_LABELS[v] },
    { title: '模型', dataIndex: 'model_name', key: 'model' },
    {
      title: 'API Key', dataIndex: 'masked_api_key', key: 'key',
      render: (v: string) => <Text code>{v}</Text>,
    },
    {
      title: '默认', dataIndex: 'is_default', key: 'default',
      render: (v: boolean) => v ? <Tag color="blue">默认</Tag> : null,
    },
    {
      title: '操作', key: 'actions',
      render: (_: unknown, record: AIConfig) => (
        <Space>
          <Button size="small" icon={<ApiOutlined />} loading={testing === record.id} onClick={() => handleTest(record.id)}>
            测试
          </Button>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>
            编辑
          </Button>
          <Popconfirm title="确定删除？" onConfirm={async () => { await deleteConfig(record.id); message.success('已删除') }}>
            <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card
        title="AI 模型配置"
        extra={<Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>添加配置</Button>}
      >
        <Table
          columns={columns}
          dataSource={configs}
          rowKey="id"
          loading={loading}
          pagination={false}
        />
      </Card>

      <Modal
        title={editing ? '编辑配置' : '添加配置'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => { setModalOpen(false); form.resetFields() }}
        okText={editing ? '保存' : '添加'}
        width={520}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="provider" label="提供商" rules={[{ required: true, message: '请选择提供商' }]}>
            <Select options={Object.entries(PROVIDER_LABELS).map(([k, v]) => ({ value: k, label: v }))} />
          </Form.Item>
          <Form.Item name="display_name" label="显示名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="如: My GPT-4o" />
          </Form.Item>
          {!editing && (
            <Form.Item name="api_key" label="API Key" rules={[{ required: true, min: 8, message: '请输入 API Key' }]}>
              <Input.Password placeholder="sk-..." />
            </Form.Item>
          )}
          <Form.Item name="model_name" label="模型" rules={[{ required: true, message: '请选择或输入模型' }]}>
            <Select
              showSearch
              placeholder="选择或输入模型名称"
              options={(provider ? PROVIDER_MODELS[provider] : []).map((m) => ({ value: m, label: m }))}
            />
          </Form.Item>
          <Form.Item name="base_url" label="API 端点">
            <Input placeholder="Ollama 等需要填写，如 http://localhost:11434" />
          </Form.Item>
          <Form.Item name="is_default" label="设为默认" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="is_active" label="启用" valuePropName="checked" initialValue={true}>
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  )
}
