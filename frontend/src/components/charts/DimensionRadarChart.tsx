import { useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import { DIMENSION_LABELS } from '../../utils/constants'
import type { Dimension, ReviewIssue } from '../../types'

interface DimensionRadarChartProps {
  issues: ReviewIssue[]
}

const DIMENSION_KEYS: Dimension[] = [
  'security',
  'correctness',
  'performance',
  'maintainability',
  'type_safety',
  'completeness',
  'best_practices',
]

export default function DimensionRadarChart({ issues }: DimensionRadarChartProps) {
  const option = useMemo(() => {
    const counts: Record<Dimension, number> = {
      security: 0,
      correctness: 0,
      performance: 0,
      maintainability: 0,
      type_safety: 0,
      completeness: 0,
      best_practices: 0,
    }
    for (const issue of issues) {
      counts[issue.dimension]++
    }

    const maxVal = Math.max(...Object.values(counts), 1)

    return {
      tooltip: {},
      radar: {
        indicator: DIMENSION_KEYS.map((key) => ({
          name: DIMENSION_LABELS[key],
          max: maxVal,
        })),
        radius: '65%',
        axisName: { fontSize: 11 },
      },
      series: [
        {
          type: 'radar' as const,
          data: [
            {
              value: DIMENSION_KEYS.map((key) => counts[key]),
              name: '问题分布',
              areaStyle: { opacity: 0.25 },
              lineStyle: { width: 2 },
              itemStyle: { color: '#1890ff' },
            },
          ],
        },
      ],
    }
  }, [issues])

  return <ReactECharts option={option} style={{ height: 280 }} />
}
