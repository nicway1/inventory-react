/**
 * WeeklyTicketsChartWidget Component
 *
 * Bar chart showing tickets created by day for the current week.
 * Uses Recharts library for visualization.
 * Fetches data from GET /api/v2/dashboard/widgets/weekly_tickets/data
 */

import { useWidgetData } from '@/hooks/useDashboard'
import { cn } from '@/utils/cn'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

interface WeeklyTicketsData {
  widget_id: string
  generated_at: string
  values: {
    labels: string[]
    values: number[]
  }
}

export interface WeeklyTicketsChartWidgetProps {
  /** Additional CSS classes */
  className?: string
}

export function WeeklyTicketsChartWidget({
  className,
}: WeeklyTicketsChartWidgetProps) {
  const { data, isLoading, isError, error, refetch } = useWidgetData<WeeklyTicketsData>(
    'weekly_tickets'
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
          <p className="text-sm text-[#C23934]">Failed to load weekly tickets chart</p>
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
    day: label,
    tickets: data.values.values[index] ?? 0,
  })) ?? []

  return (
    <div
      className={cn(
        'rounded bg-white p-6 shadow-[0_2px_4px_rgba(0,0,0,0.1)] border border-[#DDDBDA]',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="w-9 h-9 rounded-lg flex items-center justify-center bg-gradient-to-br from-[#3b82f6] to-[#2563eb]">
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
              d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
        </div>
        <div>
          <h3 className="text-base font-bold text-gray-900">Weekly Tickets</h3>
          <p className="text-xs text-gray-500">This Week (Mon-Fri)</p>
        </div>
      </div>

      {/* Chart */}
      {isLoading ? (
        <div className="h-[180px] flex items-center justify-center">
          <div className="animate-pulse flex flex-col items-center gap-2">
            <div className="h-24 w-full bg-gray-100 rounded" />
            <div className="h-4 w-32 bg-gray-100 rounded" />
          </div>
        </div>
      ) : chartData.length > 0 ? (
        <div className="h-[180px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={chartData}
              margin={{ top: 10, right: 10, left: -10, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" vertical={false} />
              <XAxis
                dataKey="day"
                tick={{ fontSize: 12, fill: '#6B7280' }}
                tickLine={false}
                axisLine={{ stroke: '#E5E7EB' }}
              />
              <YAxis
                tick={{ fontSize: 12, fill: '#6B7280' }}
                tickLine={false}
                axisLine={false}
                allowDecimals={false}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'white',
                  border: '1px solid #DDDBDA',
                  borderRadius: '4px',
                  boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                }}
                labelStyle={{ fontWeight: 600, color: '#1F2937' }}
                formatter={(value: number) => [value, 'Tickets']}
              />
              <Bar
                dataKey="tickets"
                fill="#3b82f6"
                radius={[4, 4, 0, 0]}
                maxBarSize={40}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="h-[180px] flex items-center justify-center">
          <p className="text-sm text-gray-500">No data available for this week</p>
        </div>
      )}
    </div>
  )
}

export default WeeklyTicketsChartWidget
