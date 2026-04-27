import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { ConfigProvider, Spin } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import AppLayout from './components/Layout'
import ErrorBoundary from './components/ErrorBoundary'

const Upload = lazy(() => import('./pages/Upload'))
const ProjectOverview = lazy(() => import('./pages/ProjectOverview'))
const ReviewDashboard = lazy(() => import('./pages/ReviewDashboard'))
const CodeViewer = lazy(() => import('./pages/CodeViewer'))
const Settings = lazy(() => import('./pages/Settings'))

function PageLoader() {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
      <Spin size="large" />
    </div>
  )
}

export default function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>
        <ErrorBoundary>
          <Suspense fallback={<PageLoader />}>
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
          </Suspense>
        </ErrorBoundary>
      </BrowserRouter>
    </ConfigProvider>
  )
}
