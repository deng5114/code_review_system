import { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout as AntLayout, Menu, theme, Dropdown, Avatar, Space } from 'antd'
import { UploadOutlined, SettingOutlined, HomeOutlined, UserOutlined, LogoutOutlined } from '@ant-design/icons'
import { useAuthStore } from '../stores/authStore'

const { Sider, Content } = AntLayout

const menuItems = [
  { key: '/', icon: <HomeOutlined />, label: '首页' },
  { key: '/upload', icon: <UploadOutlined />, label: '上传项目' },
  { key: '/settings', icon: <SettingOutlined />, label: 'AI 配置' },
]

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { token } = theme.useToken()
  const { user, logout } = useAuthStore()

  const selectedKey = menuItems.find((item) => location.pathname.startsWith(item.key) && item.key !== '/')?.key
    ?? (location.pathname === '/' ? '/' : '')

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        style={{ background: token.colorBgContainer }}
      >
        <div style={{ padding: '16px', textAlign: 'center' }}>
          <h2 style={{ margin: 0, fontSize: collapsed ? 14 : 18, fontWeight: 700 }}>
            {collapsed ? 'CR' : 'CodeReview'}
          </h2>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <AntLayout>
        <div style={{ padding: '12px 24px', background: token.colorBgContainer, borderBottom: `1px solid ${token.colorBorderSecondary}`, display: 'flex', justifyContent: 'flex-end' }}>
          <Dropdown
            menu={{
              items: [
                { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', onClick: handleLogout },
              ],
            }}
          >
            <Space style={{ cursor: 'pointer' }}>
              <Avatar size="small" icon={<UserOutlined />} />
              <span>{user?.username}</span>
            </Space>
          </Dropdown>
        </div>
        <Content style={{ padding: 24, background: token.colorBgLayout, minHeight: 'auto' }}>
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  )
}
