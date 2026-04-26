import { useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import { SEVERITY_CONFIG } from '../../utils/constants'
import type { Severity } from '../../types'

interface SeverityBarChartProps {
  critical: number
  high: number
  medium: number
  low: number
}

export default function SeverityBarChart({ critical, high, medium, low }: SeverityBarChartProps) {
  const option = useMemo(() => {
    const data: { key: Severity; count: number }[] = [
      { key: 'critical', count: critical },
      { key: 'high', count: high },
      { key: 'medium', count: medium },
      { key: 'low', count: low },
    ]

    return {
      tooltip: {
        trigger: 'axis' as const,
        axisPointer: { type: 'shadow' as const },
      },
      grid: { left: 40, right: 20, top: 20, bottom: 30 },
      xAxis: {
        type: 'category' as const,
        data: data.map((d) => SEVERITY_CONFIG[d.key].label),
        axisLabel: { fontSize: 12 },
      },
      yAxis: {
        type: 'value' as const,
        minInterval: 1,
        axisLabel: { fontSize: 12 },
      },
      series: [
        {
          type: 'bar' as const,
          data: data.map((d) => ({
            value: d.count,
            itemStyle: { color: SEVERITY_CONFIG[d.key].color },
          })),
          barWidth: '50%',
          label: {
            show: true,
            position: 'top' as const,
            fontSize: 13,
            fontWeight: 'bold' as const,
          },
        },
      ],
    }
  }, [critical, high, medium, low])

  return <ReactECharts option={option} style={{ height: 240 }} />
}
