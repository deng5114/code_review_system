import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import AppLayout from './components/Layout'
import Upload from './pages/Upload'
import ProjectOverview from './pages/ProjectOverview'
import ReviewDashboard from './pages/ReviewDashboard'
import CodeViewer from './pages/CodeViewer'
import Settings from './pages/Settings'

export default function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<Upload />} />
            <Route path="/upload" element={<Upload />} />
            <Route path="/projects/:id" element={<ProjectOverview />} />
            <Route path="/reviews/:id" element={<ReviewDashboard />} />
            <Route path="/reviews/:id/code" element={<CodeViewer />} />
            <Route path="/settings" element={<Settings />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  )
}
