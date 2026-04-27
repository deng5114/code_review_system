import { Component } from 'react'
import { Button, Result } from 'antd'

interface Props {
  children: React.ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  render() {
    if (this.state.hasError) {
      return (
        <Result
          status="error"
          title="页面渲染出错"
          subTitle={this.state.error?.message ?? '未知错误'}
          extra={<Button type="primary" onClick={() => window.location.reload()}>刷新页面</Button>}
        />
      )
    }
    return this.props.children
  }
}
