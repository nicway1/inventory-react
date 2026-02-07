/**
 * AdminDashboardPage Component
 *
 * Main admin dashboard with system overview stats,
 * quick links to admin sections, and recent admin activities.
 */

import { useCallback, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowPathIcon,
  UsersIcon,
  BuildingOfficeIcon,
  QueueListIcon,
  TicketIcon,
  CubeIcon,
  ClockIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/utils/cn'
import { AdminLayout } from '@/components/templates/AdminLayout'
import { useAdminDashboardStats, useAdminActivities, useAdminRefresh } from '@/hooks/useAdmin'
import type { AdminDashboardStats, AdminActivity } from '@/types/admin'

// Stats card component
interface StatsCardProps {
  title: string
  value: number | string
  subtitle?: string
  icon: React.ComponentType<{ className?: string }>
  color: string
  onClick?: () => void
}

function StatsCard({ title, value, subtitle, icon: Icon, color, onClick }: StatsCardProps) {
  return (
    <div
      className={cn(
        'bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-5 shadow-sm',
        onClick && 'cursor-pointer hover:shadow-md transition-shadow'
      )}
      onClick={onClick}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{title}</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{value}</p>
          {subtitle && (
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">{subtitle}</p>
          )}
        </div>
        <div
          className={cn(
            'w-12 h-12 rounded-lg flex items-center justify-center',
            color
          )}
        >
          <Icon className="w-6 h-6 text-white" />
        </div>
      </div>
      {onClick && (
        <div className="mt-4 pt-4 border-t border-gray-100 dark:border-gray-800">
          <span className="text-sm text-[#0176d3] font-medium flex items-center gap-1">
            View Details
            <ChevronRightIcon className="w-4 h-4" />
          </span>
        </div>
      )}
    </div>
  )
}

// Quick link card
interface QuickLinkProps {
  title: string
  description: string
  icon: React.ComponentType<{ className?: string }>
  href: string
  color: string
}

function QuickLink({ title, description, icon: Icon, href, color }: QuickLinkProps) {
  const navigate = useNavigate()

  return (
    <button
      onClick={() => navigate(href)}
      className="w-full text-left bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-4 shadow-sm hover:shadow-md transition-all group"
    >
      <div className="flex items-center gap-4">
        <div
          className={cn(
            'w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0',
            color
          )}
        >
          <Icon className="w-5 h-5 text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-gray-900 dark:text-white group-hover:text-[#0176d3]">
            {title}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
            {description}
          </p>
        </div>
        <ChevronRightIcon className="w-5 h-5 text-gray-300 group-hover:text-[#0176d3] transition-colors" />
      </div>
    </button>
  )
}

// Activity item component
interface ActivityItemProps {
  activity: AdminActivity
}

function ActivityItem({ activity }: ActivityItemProps) {
  const getActivityIcon = (type: string) => {
    if (type.includes('user')) return UsersIcon
    if (type.includes('company')) return BuildingOfficeIcon
    if (type.includes('queue')) return QueueListIcon
    if (type.includes('settings')) return ClockIcon
    return ClockIcon
  }

  const getActivityColor = (type: string) => {
    if (type.includes('created')) return 'bg-green-100 text-green-600'
    if (type.includes('updated')) return 'bg-blue-100 text-blue-600'
    if (type.includes('deleted')) return 'bg-red-100 text-red-600'
    return 'bg-gray-100 text-gray-600'
  }

  const Icon = getActivityIcon(activity.type)
  const colorClass = getActivityColor(activity.type)

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    const days = Math.floor(diff / 86400000)

    if (minutes < 60) return `${minutes}m ago`
    if (hours < 24) return `${hours}h ago`
    if (days < 7) return `${days}d ago`
    return date.toLocaleDateString()
  }

  return (
    <div className="flex items-start gap-3 py-3">
      <div className={cn('w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0', colorClass)}>
        <Icon className="w-4 h-4" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-900 dark:text-white">{activity.content}</p>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
          {activity.username && <span className="font-medium">{activity.username}</span>}
          {activity.username && ' - '}
          {formatDate(activity.created_at)}
        </p>
      </div>
    </div>
  )
}

export function AdminDashboardPage() {
  const navigate = useNavigate()
  const { refreshAll } = useAdminRefresh()
  const [isRefreshing, setIsRefreshing] = useState(false)

  // Fetch data
  const { data: stats, isLoading: statsLoading } = useAdminDashboardStats()
  const { data: activities, isLoading: activitiesLoading } = useAdminActivities(10)

  // Handle refresh
  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true)
    refreshAll()
    setTimeout(() => setIsRefreshing(false), 500)
  }, [refreshAll])

  // Default stats if loading or error
  const dashboardStats: AdminDashboardStats = stats || {
    total_users: 0,
    active_users: 0,
    total_companies: 0,
    total_queues: 0,
    total_tickets: 0,
    open_tickets: 0,
    total_assets: 0,
  }

  return (
    <AdminLayout
      title="Admin Dashboard"
      subtitle="System overview and quick actions"
      actions={
        <button
          onClick={handleRefresh}
          disabled={isRefreshing}
          className={cn(
            'inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-md transition-all',
            'bg-white border border-gray-300 text-gray-700',
            'hover:bg-gray-50 hover:border-gray-400',
            'focus:outline-none focus:ring-2 focus:ring-[#0176d3] focus:ring-offset-2',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            'dark:bg-gray-800 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700'
          )}
        >
          <ArrowPathIcon className={cn('h-4 w-4', isRefreshing && 'animate-spin')} />
          {isRefreshing ? 'Refreshing...' : 'Refresh'}
        </button>
      }
    >
      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-6">
        <StatsCard
          title="Total Users"
          value={statsLoading ? '...' : dashboardStats.total_users}
          subtitle={`${dashboardStats.active_users} active`}
          icon={UsersIcon}
          color="bg-[#0176d3]"
          onClick={() => navigate('/admin/users')}
        />
        <StatsCard
          title="Companies"
          value={statsLoading ? '...' : dashboardStats.total_companies}
          icon={BuildingOfficeIcon}
          color="bg-[#2e844a]"
          onClick={() => navigate('/admin/companies')}
        />
        <StatsCard
          title="Queues"
          value={statsLoading ? '...' : dashboardStats.total_queues}
          icon={QueueListIcon}
          color="bg-[#9050e9]"
          onClick={() => navigate('/admin/queues')}
        />
        <StatsCard
          title="Open Tickets"
          value={statsLoading ? '...' : dashboardStats.open_tickets}
          subtitle={`of ${dashboardStats.total_tickets} total`}
          icon={TicketIcon}
          color="bg-[#ff5d2d]"
          onClick={() => navigate('/tickets')}
        />
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Quick Links */}
        <div className="lg:col-span-1">
          <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 shadow-sm">
            <div className="px-5 py-4 border-b border-gray-200 dark:border-gray-800">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Quick Actions
              </h2>
            </div>
            <div className="p-4 space-y-3">
              <QuickLink
                title="Add New User"
                description="Create a new user account"
                icon={UsersIcon}
                href="/admin/users?action=create"
                color="bg-[#0176d3]"
              />
              <QuickLink
                title="Add Company"
                description="Register a new company"
                icon={BuildingOfficeIcon}
                href="/admin/companies?action=create"
                color="bg-[#2e844a]"
              />
              <QuickLink
                title="Add Queue"
                description="Create a new ticket queue"
                icon={QueueListIcon}
                href="/admin/queues?action=create"
                color="bg-[#9050e9]"
              />
              <QuickLink
                title="System Settings"
                description="Configure system preferences"
                icon={CubeIcon}
                href="/admin/settings"
                color="bg-[#747474]"
              />
            </div>
          </div>
        </div>

        {/* Recent Activities */}
        <div className="lg:col-span-2">
          <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 shadow-sm">
            <div className="px-5 py-4 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Recent Admin Activities
              </h2>
              <span className="text-xs text-gray-400">Last 10 activities</span>
            </div>
            <div className="px-5 divide-y divide-gray-100 dark:divide-gray-800">
              {activitiesLoading ? (
                <div className="py-8 text-center text-gray-500">Loading activities...</div>
              ) : activities && activities.length > 0 ? (
                activities.map((activity) => (
                  <ActivityItem key={activity.id} activity={activity} />
                ))
              ) : (
                <div className="py-8 text-center text-gray-500">
                  <ClockIcon className="w-12 h-12 mx-auto text-gray-300 mb-3" />
                  <p className="text-sm">No recent activities</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* System Overview */}
      <div className="mt-6">
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 shadow-sm p-5">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            System Overview
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="text-center p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <CubeIcon className="w-8 h-8 mx-auto text-[#2e844a] mb-2" />
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {statsLoading ? '...' : dashboardStats.total_assets}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">Total Assets</p>
            </div>
            <div className="text-center p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <TicketIcon className="w-8 h-8 mx-auto text-[#ff5d2d] mb-2" />
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {statsLoading ? '...' : dashboardStats.total_tickets}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">Total Tickets</p>
            </div>
            <div className="text-center p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <UsersIcon className="w-8 h-8 mx-auto text-[#0176d3] mb-2" />
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {statsLoading ? '...' : dashboardStats.active_users}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">Active Users</p>
            </div>
            <div className="text-center p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <BuildingOfficeIcon className="w-8 h-8 mx-auto text-[#9050e9] mb-2" />
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {statsLoading ? '...' : dashboardStats.total_companies}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">Companies</p>
            </div>
          </div>
        </div>
      </div>
    </AdminLayout>
  )
}

export default AdminDashboardPage
