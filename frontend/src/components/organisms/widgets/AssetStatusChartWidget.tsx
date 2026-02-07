/**
 * AssetStatusChartWidget Component
 *
 * Doughnut/pie chart showing assets by status.
 * Uses Recharts library for visualization.
 * Fetches data from GET /api/v2/dashboard/widgets/asset_status/data
 */

import { useWidgetData } from '@/hooks/useDashboard'
import { cn } from '@/utils/cn'
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from 'recharts'

interface AssetStatusData {
  widget_id: string
  generated_at: string
  values: {
    labels: string[]
    values: number[]
  }
}

// Status colors matching Salesforce Lightning palette
const STATUS_COLORS = [
  '#2E844A', // Available - Green
  '#0176D3', // Deployed - Blue
  '#FE9339', // Pending - Orange
  '#C23934', // Broken - Red
  '#7C41A1', // Retired - Purple
  '#057B6B', // Repair - Teal
  '#6B7280', // Other - Gray
]

export interface AssetStatusChartWidgetProps {
  /** Additional CSS classes */
  className?: string
}

export function AssetStatusChartWidget({
  className,
}: AssetStatusChartWidgetProps) {
  const { data, isLoading, isError, error, refetch } = useWidgetData<AssetStatusData>(
    'asset_status'
  )

  if (isError) {
    return (
      <div
        className={cn(
          'rounded bg-white p-6 shadow-[0_2px_4px_rgba(0,0,0,0.1)] border border-[#DDDBDA]',
          className
        )}
      >
        <div className="text-center">
          <p className="text-sm text-[#C23934]">Failed to load asset status chart</p>
          <p className="mt-1 text-xs text-gray-500">{error?.message}</p>
          <button
            onClick={() => refetch()}
            className="mt-3 text-sm font-medium text-[#0176D3] hover:text-[#014486]"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  // Transform data for Recharts
  const chartData = data?.values?.labels?.map((label, index) => ({
    name: label,
    value: data.values.values[index] ?? 0,
  })) ?? []

  const total = chartData.reduce((sum, item) => sum + item.value, 0)

  return (
    <div
      className={cn(
        'rounded bg-white p-6 shadow-[0_2px_4px_rgba(0,0,0,0.1)] border border-[#DDDBDA]',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="w-9 h-9 rounded-lg flex items-center justify-center bg-gradient-to-br from-[#7C41A1] to-[#5A2D82]">
          <svg
            className="h-5 w-5 text-white"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z"
            />
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z"
            />
          </svg>
        </div>
        <div>
          <h3 className="text-base font-bold text-gray-900">Asset Status Distribution</h3>
          <p className="text-xs text-gray-500">{total.toLocaleString()} total assets</p>
        </div>
      </div>

      {/* Chart */}
      {isLoading ? (
        <div className="h-[180px] flex items-center justify-center">
          <div className="w-32 h-32 rounded-full border-8 border-gray-100 animate-pulse" />
        </div>
      ) : chartData.length > 0 ? (
        <div className="h-[200px]">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={45}
                outerRadius={70}
                paddingAngle={2}
                dataKey="value"
              >
                {chartData.map((_, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={STATUS_COLORS[index % STATUS_COLORS.length]}
                  />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: 'white',
                  border: '1px solid #DDDBDA',
                  borderRadius: '4px',
                  boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                }}
                formatter={(value: number, name: string) => [
                  `${value} (${total > 0 ? Math.round((value / total) * 100) : 0}%)`,
                  name,
                ]}
              />
              <Legend
                layout="horizontal"
                verticalAlign="bottom"
                align="center"
                wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }}
                formatter={(value) => (
                  <span className="text-gray-700">{value}</span>
                )}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="h-[180px] flex items-center justify-center">
          <p className="text-sm text-gray-500">No asset status data available</p>
        </div>
      )}
    </div>
  )
}

export default AssetStatusChartWidget
