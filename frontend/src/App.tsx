import { lazy, Suspense, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ConfigProvider, Spin } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import AppLayout from './components/Layout'
import ErrorBoundary from './components/ErrorBoundary'
import ProtectedRoute from './components/ProtectedRoute'
import { useAuthStore } from './stores/authStore'

const Login = lazy(() => import('./pages/Login'))
const Register = lazy(() => import('./pages/Register'))
const Home = lazy(() => import('./pages/Home'))
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

function AuthRedirect({ children }: { children: React.ReactNode }) {
  const { user, initialized } = useAuthStore()
  if (!initialized) return <PageLoader />
  if (user) return <Navigate to="/" replace />
  return <>{children}</>
}

export default function App() {
  const init = useAuthStore((s) => s.init)

  useEffect(() => {
    init()
  }, [init])

  return (
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>
        <ErrorBoundary>
          <Suspense fallback={<PageLoader />}>
            <Routes>
              <Route path="/login" element={<AuthRedirect><Login /></AuthRedirect>} />
              <Route path="/register" element={<AuthRedirect><Register /></AuthRedirect>} />
              <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
                <Route path="/" element={<Home />} />
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
