import { useCallback, useEffect, useRef, useState } from 'react'
import { Select, Input, Button, Space, Tag, AutoComplete } from 'antd'
import { ClearOutlined, SearchOutlined, SafetyOutlined, WarningOutlined } from '@ant-design/icons'
import { SEVERITY_CONFIG, DIMENSION_LABELS } from '../utils/constants'
import type { Severity, Dimension, IssueFilters } from '../types'

interface FilterPanelProps {
  filters: IssueFilters
  onChange: (filters: IssueFilters) => void
  availableFiles?: string[]
  totalIssues: number
  filteredCount: number
}

const severityOptions = (Object.entries(SEVERITY_CONFIG) as [Severity, { label: string }][]).map(
  ([value, { label }]) => ({ value, label })
)

const dimensionOptions = (Object.entries(DIMENSION_LABELS) as [Dimension, string][]).map(
  ([value, label]) => ({ value, label })
)

export default function FilterPanel({
  filters,
  onChange,
  availableFiles = [],
  totalIssues,
  filteredCount,
}: FilterPanelProps) {
  const [searchText, setSearchText] = useState(filters.search ?? '')
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const filtersRef = useRef(filters)
  filtersRef.current = filters

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [])

  const handleSearchChange = useCallback(
    (value: string) => {
      setSearchText(value)
      if (debounceRef.current) clearTimeout(debounceRef.current)
      debounceRef.current = setTimeout(() => {
        onChange({ ...filtersRef.current, search: value || undefined })
      }, 300)
    },
    [onChange]
  )

  const handleSeverityChange = useCallback(
    (values: Severity[]) => {
      onChange({ ...filtersRef.current, severity: values.length > 0 ? values : undefined })
    },
    [onChange]
  )

  const handleDimensionChange = useCallback(
    (values: Dimension[]) => {
      onChange({ ...filtersRef.current, dimension: values.length > 0 ? values : undefined })
    },
    [onChange]
  )

  const handleFilePathChange = useCallback(
    (value: string) => {
      onChange({ ...filtersRef.current, file_path: value || undefined })
    },
    [onChange]
  )

  const applyPreset = useCallback(
    (preset: IssueFilters) => {
      setSearchText(preset.search ?? '')
      onChange(preset)
    },
    [onChange]
  )

  const handleClear = useCallback(() => {
    setSearchText('')
    onChange({})
  }, [onChange])

  const fileOptions = availableFiles.map((f) => ({ value: f, label: f }))

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Space wrap size="middle">
        <Select<Severity[]>
          mode="multiple"
          placeholder="严重性"
          style={{ minWidth: 180 }}
          value={filters.severity ?? []}
          onChange={handleSeverityChange}
          options={severityOptions}
          allowClear
          maxTagCount="responsive"
        />
        <Select<Dimension[]>
          mode="multiple"
          placeholder="维度"
          style={{ minWidth: 180 }}
          value={filters.dimension ?? []}
          onChange={handleDimensionChange}
          options={dimensionOptions}
          allowClear
          maxTagCount="responsive"
        />
        <AutoComplete
          options={fileOptions}
          placeholder="文件路径"
          style={{ width: 200 }}
          value={filters.file_path ?? ''}
          onChange={handleFilePathChange}
          filterOption={(input, option) =>
            (option?.value as string)?.toLowerCase().includes(input.toLowerCase()) ?? false
          }
          allowClear
        />
        <Input
          placeholder="搜索标题或描述..."
          prefix={<SearchOutlined />}
          style={{ width: 220 }}
          value={searchText}
          onChange={(e) => handleSearchChange(e.target.value)}
          allowClear
          onClear={() => handleSearchChange('')}
        />
      </Space>
      <Space>
        <Button
          size="small"
          icon={<SafetyOutlined />}
          onClick={() =>
            applyPreset({ severity: ['critical', 'high'], dimension: ['security'] })
          }
        >
          仅安全问题
        </Button>
        <Button
          size="small"
          icon={<WarningOutlined />}
          onClick={() => applyPreset({ severity: ['critical', 'high'] })}
        >
          所有关键问题
        </Button>
        <Button size="small" icon={<ClearOutlined />} onClick={handleClear}>
          清除筛选
        </Button>
        <Tag color={filteredCount < totalIssues ? 'blue' : 'default'}>
          显示 {filteredCount} / {totalIssues} 个问题
        </Tag>
      </Space>
    </Space>
  )
}
