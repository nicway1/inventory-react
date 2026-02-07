/**
 * TicketDetailPage Component
 *
 * Comprehensive ticket detail/view page matching Flask TrueLog design:
 * - Page header with ticket ID, subject, status, priority
 * - SF-style info cards (customer, details, assignee)
 * - Tabbed sections (Comments, Attachments, Assets, Accessories, Activity, Shipping)
 * - Messenger-style comments with @mentions
 * - Right sidebar with quick actions and SLA info
 */

import { useCallback, useEffect, useState, useRef, Fragment } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { Tab, TabGroup, TabList, TabPanel, TabPanels } from '@headlessui/react'
import {
  ArrowLeftIcon,
  PencilIcon,
  UserPlusIcon,
  XCircleIcon,
  TrashIcon,
  PaperClipIcon,
  ChatBubbleLeftIcon,
  ClockIcon,
  ComputerDesktopIcon,
  WrenchScrewdriverIcon,
  TruckIcon,
  DocumentTextIcon,
  PaperAirplaneIcon,
  EllipsisVerticalIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline'
import { PageLayout } from '@/components/templates/PageLayout'
import { Card, CardHeader } from '@/components/molecules/Card'
import { Badge } from '@/components/atoms/Badge'
import { Button } from '@/components/atoms/Button'
import { Avatar } from '@/components/atoms/Avatar'
import { Spinner } from '@/components/atoms/Spinner'
import { Modal } from '@/components/organisms/Modal'
import { cn } from '@/utils/cn'
import { formatDateTime, formatRelativeTime } from '@/utils/date'
import { useTabStore, type TabIconType } from '@/store/tabs.store'
import { useAuthStore } from '@/store/auth.store'
import apiClient from '@/services/api'

// ============================================================================
// Types
// ============================================================================

interface Ticket {
  id: number
  display_id: string
  subject: string
  description?: string
  status: string
  custom_status?: string
  priority: string
  category?: string
  queue?: { id: number; name: string }
  customer?: {
    id: number
    name: string
    email?: string
    contact_number?: string
    company?: { id: number; name: string }
  }
  assigned_to?: {
    id: number
    username: string
    first_name?: string
    last_name?: string
  }
  created_by?: {
    id: number
    username: string
  }
  created_at: string
  updated_at: string
  shipping_tracking?: string
  shipping_status?: string
  return_tracking?: string
  item_packed?: boolean
  item_packed_at?: string
}

interface Comment {
  id: number
  content: string
  user: {
    id: number
    username: string
    first_name?: string
    last_name?: string
  }
  created_at: string
  updated_at?: string
}

interface Attachment {
  id: number
  filename: string
  file_type: string
  file_size: number
  uploaded_at: string
  uploaded_by?: { id: number; username: string }
}

interface Asset {
  id: number
  asset_tag: string
  serial_num?: string
  model?: string
  status: string
}

interface Accessory {
  id: number
  name: string
  category?: string
  quantity: number
  condition?: string
}

interface ActivityLog {
  id: number
  action: string
  details?: string
  user?: { id: number; username: string }
  created_at: string
}

interface MentionSuggestion {
  id: number
  name: string
  type: 'user' | 'group'
}

// ============================================================================
// Helper Components
// ============================================================================

// SF-style field row component
const FieldRow: React.FC<{
  label: string
  value: React.ReactNode
  className?: string
}> = ({ label, value, className }) => (
  <div className={cn('flex mb-2', className)}>
    <div className="w-2/5 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide pr-4">
      {label}
    </div>
    <div className="w-3/5 text-sm text-gray-900 dark:text-white">{value || '-'}</div>
  </div>
)

// Status badge with color mapping
const StatusBadge: React.FC<{ status: string; customStatus?: string }> = ({
  status,
  customStatus,
}) => {
  const displayStatus = customStatus || status
  const statusLower = displayStatus.toLowerCase()

  let variant: 'success' | 'warning' | 'danger' | 'info' | 'neutral' = 'neutral'
  if (statusLower.includes('resolved') || statusLower.includes('closed') || statusLower.includes('delivered')) {
    variant = 'success'
  } else if (statusLower.includes('progress') || statusLower.includes('review')) {
    variant = 'info'
  } else if (statusLower.includes('hold') || statusLower.includes('pending')) {
    variant = 'warning'
  } else if (statusLower.includes('new') || statusLower.includes('open')) {
    variant = 'info'
  }

  return (
    <Badge variant={variant} dot>
      {displayStatus.replace(/_/g, ' ')}
    </Badge>
  )
}

// Priority badge with color mapping
const PriorityBadge: React.FC<{ priority: string }> = ({ priority }) => {
  const priorityLower = priority.toLowerCase()
  let variant: 'success' | 'warning' | 'danger' | 'info' | 'neutral' = 'neutral'

  if (priorityLower === 'high' || priorityLower === 'critical') {
    variant = 'danger'
  } else if (priorityLower === 'medium') {
    variant = 'warning'
  } else if (priorityLower === 'low') {
    variant = 'success'
  }

  return <Badge variant={variant}>{priority}</Badge>
}

// Comment bubble component (messenger-style)
const CommentBubble: React.FC<{
  comment: Comment
  isCurrentUser: boolean
}> = ({ comment, isCurrentUser }) => {
  return (
    <div className={cn('mb-4 flex', isCurrentUser ? 'justify-end' : 'justify-start')}>
      <div className="max-w-[75%]">
        {/* User avatar and name */}
        <div className={cn('flex items-center mb-1', isCurrentUser && 'flex-row-reverse')}>
          <Avatar
            name={comment.user.username}
            size="sm"
            className={cn(isCurrentUser ? 'ml-2' : 'mr-2')}
          />
          <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
            {comment.user.first_name || comment.user.username}
          </span>
        </div>

        {/* Message bubble */}
        <div
          className={cn(
            'px-4 py-3 shadow-sm',
            isCurrentUser
              ? 'bg-blue-500 text-white rounded-l-2xl rounded-tr-2xl'
              : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-800 dark:text-gray-200 rounded-r-2xl rounded-tl-2xl'
          )}
        >
          <div className="text-sm whitespace-pre-wrap break-words">{comment.content}</div>
        </div>

        {/* Timestamp */}
        <div className={cn('mt-1 text-xs text-gray-500 dark:text-gray-400', isCurrentUser && 'text-right')}>
          {formatRelativeTime(comment.created_at)}
        </div>
      </div>
    </div>
  )
}

// Empty state component
const EmptyState: React.FC<{
  icon: React.ReactNode
  title: string
  description?: string
  action?: React.ReactNode
}> = ({ icon, title, description, action }) => (
  <div className="text-center py-12">
    <div className="text-gray-300 dark:text-gray-600 mb-3">{icon}</div>
    <p className="text-gray-500 dark:text-gray-400 font-medium">{title}</p>
    {description && <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">{description}</p>}
    {action && <div className="mt-4">{action}</div>}
  </div>
)

// ============================================================================
// Main Component
// ============================================================================

export function TicketDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const { openNewTab, updateTab, getTabByUrl } = useTabStore()

  // State
  const [ticket, setTicket] = useState<Ticket | null>(null)
  const [comments, setComments] = useState<Comment[]>([])
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [assets, setAssets] = useState<Asset[]>([])
  const [accessories, setAccessories] = useState<Accessory[]>([])
  const [activityLog, setActivityLog] = useState<ActivityLog[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Comment form state
  const [newComment, setNewComment] = useState('')
  const [isSubmittingComment, setIsSubmittingComment] = useState(false)
  const [mentionQuery, setMentionQuery] = useState('')
  const [mentionSuggestions, setMentionSuggestions] = useState<MentionSuggestion[]>([])
  const [showMentionDropdown, setShowMentionDropdown] = useState(false)
  const [mentionStartPos, setMentionStartPos] = useState(-1)
  const commentTextareaRef = useRef<HTMLTextAreaElement>(null)
  const commentsContainerRef = useRef<HTMLDivElement>(null)

  // Modal state
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [showAssignModal, setShowAssignModal] = useState(false)

  // ============================================================================
  // Data Fetching
  // ============================================================================

  const fetchTicket = useCallback(async () => {
    if (!id) return

    try {
      setIsLoading(true)
      setError(null)

      const response = await apiClient.get(`/v2/tickets/${id}`)
      const ticketData = response.data.data || response.data

      setTicket(ticketData)

      // Update tab title
      const tabUrl = `/tickets/${id}`
      const existingTab = getTabByUrl(tabUrl)
      if (existingTab) {
        updateTab(existingTab.id, {
          title: `Case ${ticketData.display_id || id}`,
        })
      }
    } catch (err: any) {
      console.error('Error fetching ticket:', err)
      setError(err.response?.data?.message || 'Failed to load ticket')
    } finally {
      setIsLoading(false)
    }
  }, [id, getTabByUrl, updateTab])

  const fetchComments = useCallback(async () => {
    if (!id) return

    try {
      const response = await apiClient.get(`/v2/tickets/${id}/comments`)
      setComments(response.data.data || response.data.comments || [])
    } catch (err) {
      console.error('Error fetching comments:', err)
    }
  }, [id])

  const fetchAttachments = useCallback(async () => {
    if (!id) return

    try {
      const response = await apiClient.get(`/v2/tickets/${id}/attachments`)
      setAttachments(response.data.data || response.data.attachments || [])
    } catch (err) {
      console.error('Error fetching attachments:', err)
    }
  }, [id])

  const fetchAssets = useCallback(async () => {
    if (!id) return

    try {
      const response = await apiClient.get(`/v2/tickets/${id}/assets`)
      setAssets(response.data.data || response.data.assets || [])
    } catch (err) {
      console.error('Error fetching assets:', err)
    }
  }, [id])

  const fetchAccessories = useCallback(async () => {
    if (!id) return

    try {
      const response = await apiClient.get(`/v2/tickets/${id}/accessories`)
      setAccessories(response.data.data || response.data.accessories || [])
    } catch (err) {
      console.error('Error fetching accessories:', err)
    }
  }, [id])

  const fetchActivityLog = useCallback(async () => {
    if (!id) return

    try {
      const response = await apiClient.get(`/v2/tickets/${id}/activity`)
      setActivityLog(response.data.data || response.data.activities || [])
    } catch (err) {
      console.error('Error fetching activity log:', err)
    }
  }, [id])

  // Initial data load
  useEffect(() => {
    fetchTicket()
    fetchComments()
    fetchAttachments()
    fetchAssets()
    fetchAccessories()
    fetchActivityLog()
  }, [fetchTicket, fetchComments, fetchAttachments, fetchAssets, fetchAccessories, fetchActivityLog])

  // Add tab when page loads
  useEffect(() => {
    if (ticket) {
      const tabUrl = `/tickets/${id}`
      openNewTab(tabUrl, `Case ${ticket.display_id || id}`, 'ticket' as TabIconType)

      // Update browser tab title
      document.title = `Case ${ticket.display_id} - ${ticket.subject} | TrueLog`
    }
  }, [ticket, id, openNewTab])

  // ============================================================================
  // Comment Handlers
  // ============================================================================

  const handleCommentSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newComment.trim() || isSubmittingComment) return

    try {
      setIsSubmittingComment(true)
      await apiClient.post(`/v2/tickets/${id}/comments`, {
        content: newComment.trim(),
      })

      setNewComment('')
      await fetchComments()

      // Scroll to bottom of comments
      if (commentsContainerRef.current) {
        commentsContainerRef.current.scrollTop = commentsContainerRef.current.scrollHeight
      }
    } catch (err: any) {
      console.error('Error adding comment:', err)
      alert(err.response?.data?.message || 'Failed to add comment')
    } finally {
      setIsSubmittingComment(false)
    }
  }

  const handleCommentKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleCommentSubmit(e as unknown as React.FormEvent)
    }
  }

  const handleCommentInput = async (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value
    setNewComment(value)

    // Auto-resize textarea
    const textarea = e.target
    textarea.style.height = 'auto'
    textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px'

    // Check for @mention
    const cursorPos = textarea.selectionStart
    const textBeforeCursor = value.substring(0, cursorPos)
    const mentionMatch = textBeforeCursor.match(/@([a-zA-Z0-9._@-]*)$/)

    if (mentionMatch) {
      setMentionQuery(mentionMatch[1])
      setMentionStartPos(cursorPos - mentionMatch[0].length)
      await searchMentions(mentionMatch[1])
    } else {
      setShowMentionDropdown(false)
      setMentionSuggestions([])
    }
  }

  const searchMentions = async (query: string) => {
    try {
      const response = await apiClient.get(`/tickets/api/mention-suggestions?q=${encodeURIComponent(query)}`)
      const suggestions = response.data.suggestions || []
      setMentionSuggestions(suggestions)
      setShowMentionDropdown(suggestions.length > 0)
    } catch (err) {
      console.error('Error searching mentions:', err)
      setShowMentionDropdown(false)
    }
  }

  const selectMention = (suggestion: MentionSuggestion) => {
    if (commentTextareaRef.current && mentionStartPos >= 0) {
      const textarea = commentTextareaRef.current
      const value = textarea.value
      const beforeMention = value.substring(0, mentionStartPos)
      const afterCursor = value.substring(textarea.selectionStart)

      const mentionText = `@${suggestion.name} `
      const newValue = beforeMention + mentionText + afterCursor
      setNewComment(newValue)

      // Set cursor position after mention
      const newCursorPos = mentionStartPos + mentionText.length
      setTimeout(() => {
        textarea.setSelectionRange(newCursorPos, newCursorPos)
        textarea.focus()
      }, 0)
    }

    setShowMentionDropdown(false)
    setMentionSuggestions([])
  }

  // ============================================================================
  // Action Handlers
  // ============================================================================

  const handleEdit = () => {
    navigate(`/tickets/${id}/edit`)
  }

  const handleDelete = async () => {
    try {
      await apiClient.delete(`/v2/tickets/${id}`)
      navigate('/tickets')
    } catch (err: any) {
      console.error('Error deleting ticket:', err)
      alert(err.response?.data?.message || 'Failed to delete ticket')
    }
    setShowDeleteModal(false)
  }

  const handleBack = () => {
    navigate('/tickets')
  }

  // ============================================================================
  // Days Open Calculator
  // ============================================================================

  const calculateDaysOpen = (createdAt: string): number => {
    const created = new Date(createdAt)
    const now = new Date()
    const diffTime = Math.abs(now.getTime() - created.getTime())
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24))
  }

  // ============================================================================
  // Render
  // ============================================================================

  if (isLoading) {
    return (
      <PageLayout>
        <div className="flex items-center justify-center min-h-[400px]">
          <Spinner size="lg" label="Loading ticket..." />
        </div>
      </PageLayout>
    )
  }

  if (error || !ticket) {
    return (
      <PageLayout>
        <div className="flex flex-col items-center justify-center min-h-[400px]">
          <ExclamationTriangleIcon className="w-16 h-16 text-gray-400 mb-4" />
          <h2 className="text-xl font-semibold text-gray-700 dark:text-gray-300 mb-2">
            {error || 'Ticket not found'}
          </h2>
          <Button variant="secondary" onClick={handleBack}>
            Back to Tickets
          </Button>
        </div>
      </PageLayout>
    )
  }

  const daysOpen = calculateDaysOpen(ticket.created_at)

  return (
    <PageLayout fullWidth>
      <div className="bg-gray-100 dark:bg-gray-950 min-h-screen">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          {/* Page Header Card */}
          <Card className="mb-6">
            <CardHeader
              className="!bg-gradient-to-r !from-blue-50 !to-blue-100 dark:!from-gray-800 dark:!to-gray-800"
              action={
                <Link
                  to="/tickets"
                  className="inline-flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400"
                >
                  <ArrowLeftIcon className="w-4 h-4" />
                  Back to Tickets
                </Link>
              }
            >
              <div className="flex items-center gap-3">
                <DocumentTextIcon className="w-6 h-6 text-gray-500 dark:text-gray-400" />
                <div>
                  <h1 className="text-lg font-semibold text-gray-900 dark:text-white">
                    {ticket.subject}
                  </h1>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Case {ticket.display_id}
                  </p>
                </div>
              </div>
            </CardHeader>

            {/* Info Grid */}
            <div className="p-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {/* Column 1: Status & Priority */}
              <div className="space-y-3">
                <FieldRow label="Priority" value={<PriorityBadge priority={ticket.priority || 'Normal'} />} />
                <FieldRow
                  label="Status"
                  value={<StatusBadge status={ticket.status} customStatus={ticket.custom_status} />}
                />
              </div>

              {/* Column 2: Case Info */}
              <div className="space-y-3">
                <FieldRow label="Case Number" value={<span className="font-mono">{ticket.display_id}</span>} />
                {ticket.customer && (
                  <FieldRow label="Customer" value={ticket.customer.name} />
                )}
                {ticket.customer?.company && (
                  <FieldRow label="Company" value={ticket.customer.company.name} />
                )}
              </div>

              {/* Column 3: Dates */}
              <div className="space-y-3">
                <FieldRow label="Created" value={formatDateTime(ticket.created_at)} />
                <FieldRow label="Last Modified" value={formatDateTime(ticket.updated_at)} />
              </div>

              {/* Column 4: Assignment */}
              <div className="space-y-3">
                <FieldRow
                  label="Case Owner"
                  value={
                    ticket.assigned_to ? (
                      <div className="flex items-center gap-2">
                        <Avatar name={ticket.assigned_to.username} size="xs" />
                        <span>{ticket.assigned_to.first_name || ticket.assigned_to.username}</span>
                      </div>
                    ) : (
                      <span className="text-orange-600">Unassigned</span>
                    )
                  }
                />
                <FieldRow label="Category" value={ticket.category?.replace(/_/g, ' ') || 'General'} />
                <FieldRow label="Queue" value={ticket.queue?.name || 'No Queue'} />
              </div>
            </div>

            {/* Action Buttons */}
            <div className="px-4 pb-4 flex flex-wrap gap-2">
              <Button variant="primary" size="sm" leftIcon={<PencilIcon className="w-4 h-4" />} onClick={handleEdit}>
                Edit
              </Button>
              <Button variant="secondary" size="sm" leftIcon={<UserPlusIcon className="w-4 h-4" />} onClick={() => setShowAssignModal(true)}>
                Assign
              </Button>
              <Button variant="secondary" size="sm" leftIcon={<CheckCircleIcon className="w-4 h-4" />}>
                Close Case
              </Button>
              <Button variant="danger" size="sm" leftIcon={<TrashIcon className="w-4 h-4" />} onClick={() => setShowDeleteModal(true)}>
                Delete
              </Button>
            </div>
          </Card>

          {/* Days Open Badge */}
          <div className="mb-6 flex items-center gap-4">
            <div className="inline-flex items-center px-4 py-2 bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300 rounded-full text-sm font-medium">
              <ClockIcon className="w-4 h-4 mr-2" />
              Days Open: <span className="font-bold ml-1">{daysOpen}</span>
            </div>
          </div>

          {/* Main Content Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Left Content (3 columns) */}
            <div className="lg:col-span-3 space-y-6">
              {/* Tabs Section */}
              <Card padding="none">
                <TabGroup>
                  <TabList className="flex overflow-x-auto bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
                    {[
                      { name: 'Comments', icon: ChatBubbleLeftIcon, count: comments.length },
                      { name: 'Attachments', icon: PaperClipIcon, count: attachments.length },
                      { name: 'Assets', icon: ComputerDesktopIcon, count: assets.length },
                      { name: 'Accessories', icon: WrenchScrewdriverIcon, count: accessories.length },
                      { name: 'Activity', icon: ClockIcon, count: activityLog.length },
                      { name: 'Shipping', icon: TruckIcon },
                    ].map((tab) => (
                      <Tab
                        key={tab.name}
                        className={({ selected }) =>
                          cn(
                            'flex items-center gap-2 px-4 py-3 text-sm font-medium whitespace-nowrap',
                            'border-b-2 transition-colors focus:outline-none',
                            selected
                              ? 'border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400'
                              : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300'
                          )
                        }
                      >
                        <tab.icon className="w-4 h-4" />
                        {tab.name}
                        {tab.count !== undefined && tab.count > 0 && (
                          <span className="ml-1 px-2 py-0.5 text-xs bg-gray-200 dark:bg-gray-700 rounded-full">
                            {tab.count}
                          </span>
                        )}
                      </Tab>
                    ))}
                  </TabList>

                  <TabPanels>
                    {/* Comments Tab */}
                    <TabPanel>
                      <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-4">
                        <h3 className="text-lg font-semibold text-white flex items-center">
                          <ChatBubbleLeftIcon className="w-5 h-5 mr-2" />
                          Comments ({comments.length})
                        </h3>
                      </div>

                      {/* Comments List */}
                      <div
                        ref={commentsContainerRef}
                        className="p-4 max-h-[600px] overflow-y-auto bg-gray-50 dark:bg-gray-900"
                      >
                        {comments.length > 0 ? (
                          comments
                            .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
                            .map((comment) => (
                              <CommentBubble
                                key={comment.id}
                                comment={comment}
                                isCurrentUser={comment.user.id === user?.id}
                              />
                            ))
                        ) : (
                          <EmptyState
                            icon={<ChatBubbleLeftIcon className="w-12 h-12 mx-auto" />}
                            title="No comments yet"
                            description="Start the conversation!"
                          />
                        )}
                      </div>

                      {/* Comment Input */}
                      <div className="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
                        <form onSubmit={handleCommentSubmit}>
                          <div className="flex items-end space-x-2">
                            <div className="flex-1 relative">
                              <textarea
                                ref={commentTextareaRef}
                                value={newComment}
                                onChange={handleCommentInput}
                                onKeyDown={handleCommentKeyDown}
                                placeholder="Write a comment... Use @ to mention users"
                                rows={1}
                                className={cn(
                                  'w-full border border-gray-300 dark:border-gray-600 rounded-2xl px-4 py-2.5 pr-12',
                                  'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                                  'resize-none bg-white dark:bg-gray-900 text-gray-900 dark:text-white',
                                  'placeholder:text-gray-400 dark:placeholder:text-gray-500'
                                )}
                              />

                              {/* Mention Dropdown */}
                              {showMentionDropdown && mentionSuggestions.length > 0 && (
                                <div className="absolute bottom-full left-0 mb-2 w-80 bg-white dark:bg-gray-800 rounded-xl shadow-2xl border border-gray-300 dark:border-gray-600 overflow-hidden z-50">
                                  <div className="px-4 py-2 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-gray-700 dark:to-gray-700 border-b border-gray-200 dark:border-gray-600">
                                    <div className="flex items-center gap-2">
                                      <UserPlusIcon className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                                      <span className="text-xs font-semibold text-gray-700 dark:text-gray-300">
                                        Mention someone
                                      </span>
                                      <span className="ml-auto text-xs text-gray-500">
                                        {mentionSuggestions.length} result{mentionSuggestions.length !== 1 ? 's' : ''}
                                      </span>
                                    </div>
                                  </div>
                                  <div className="max-h-60 overflow-y-auto">
                                    {mentionSuggestions.map((suggestion) => (
                                      <button
                                        key={suggestion.id}
                                        type="button"
                                        onClick={() => selectMention(suggestion)}
                                        className="w-full text-left px-4 py-3 hover:bg-blue-50 dark:hover:bg-gray-700 flex items-center gap-3 transition-colors border-b border-gray-100 dark:border-gray-700 last:border-b-0"
                                      >
                                        <Avatar
                                          name={suggestion.name}
                                          size="sm"
                                          className={
                                            suggestion.type === 'group'
                                              ? '!bg-gradient-to-br !from-green-400 !to-emerald-500'
                                              : ''
                                          }
                                        />
                                        <div className="flex-1 min-w-0">
                                          <div className="flex items-center gap-2">
                                            <span className="font-semibold text-gray-900 dark:text-white text-sm">
                                              @{suggestion.name}
                                            </span>
                                            {suggestion.type === 'group' && (
                                              <span className="px-2 py-0.5 bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 text-xs font-medium rounded-full">
                                                Group
                                              </span>
                                            )}
                                          </div>
                                          <div className="text-xs text-gray-500 dark:text-gray-400 truncate">
                                            {suggestion.type === 'group' ? 'Notify all members' : 'User'}
                                          </div>
                                        </div>
                                      </button>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {/* Send Button */}
                              <button
                                type="submit"
                                disabled={isSubmittingComment || !newComment.trim()}
                                className={cn(
                                  'absolute right-2 bottom-2 bg-blue-600 hover:bg-blue-700 text-white',
                                  'rounded-full w-8 h-8 flex items-center justify-center transition-colors',
                                  'disabled:opacity-50 disabled:cursor-not-allowed'
                                )}
                              >
                                {isSubmittingComment ? (
                                  <Spinner size="sm" variant="white" />
                                ) : (
                                  <PaperAirplaneIcon className="w-4 h-4" />
                                )}
                              </button>
                            </div>
                          </div>
                          <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                            <InformationCircleIcon className="w-3 h-3 inline mr-1" />
                            Use <strong>@username</strong> to mention someone
                          </p>
                        </form>
                      </div>
                    </TabPanel>

                    {/* Attachments Tab */}
                    <TabPanel className="p-4">
                      <div className="mb-4 flex items-center justify-between">
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                          Attachments & Documents
                        </h3>
                        <Button variant="primary" size="sm" leftIcon={<PaperClipIcon className="w-4 h-4" />}>
                          Upload File
                        </Button>
                      </div>

                      {attachments.length > 0 ? (
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                          {attachments.map((attachment) => (
                            <div
                              key={attachment.id}
                              className="bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4"
                            >
                              <div className="flex items-center gap-3">
                                <PaperClipIcon className="w-6 h-6 text-gray-400" />
                                <div className="flex-1 min-w-0">
                                  <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                                    {attachment.filename}
                                  </p>
                                  <p className="text-xs text-gray-500 dark:text-gray-400">
                                    {attachment.file_type.toUpperCase()} - {formatRelativeTime(attachment.uploaded_at)}
                                  </p>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <EmptyState
                          icon={<PaperClipIcon className="w-12 h-12 mx-auto" />}
                          title="No attachments"
                          description="Upload documents related to this ticket"
                        />
                      )}
                    </TabPanel>

                    {/* Assets Tab */}
                    <TabPanel className="p-4">
                      <div className="mb-4 flex items-center justify-between">
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Linked Assets</h3>
                        <Button variant="primary" size="sm" leftIcon={<ComputerDesktopIcon className="w-4 h-4" />}>
                          Add Asset
                        </Button>
                      </div>

                      {assets.length > 0 ? (
                        <div className="overflow-x-auto">
                          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                            <thead className="bg-gray-50 dark:bg-gray-800">
                              <tr>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                  Asset Tag
                                </th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                  Serial Number
                                </th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                  Model
                                </th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                  Status
                                </th>
                              </tr>
                            </thead>
                            <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                              {assets.map((asset) => (
                                <tr key={asset.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                                  <td className="px-4 py-3 whitespace-nowrap">
                                    <Link
                                      to={`/inventory/${asset.id}`}
                                      className="text-blue-600 dark:text-blue-400 hover:underline font-medium"
                                    >
                                      {asset.asset_tag}
                                    </Link>
                                  </td>
                                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                                    {asset.serial_num || '-'}
                                  </td>
                                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                                    {asset.model || '-'}
                                  </td>
                                  <td className="px-4 py-3 whitespace-nowrap">
                                    <Badge variant="info" size="sm">
                                      {asset.status}
                                    </Badge>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <EmptyState
                          icon={<ComputerDesktopIcon className="w-12 h-12 mx-auto" />}
                          title="No assets linked"
                          description="Add assets to this ticket"
                        />
                      )}
                    </TabPanel>

                    {/* Accessories Tab */}
                    <TabPanel className="p-4">
                      <div className="mb-4 flex items-center justify-between">
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Accessories</h3>
                        <Button variant="primary" size="sm" leftIcon={<WrenchScrewdriverIcon className="w-4 h-4" />}>
                          Add Accessory
                        </Button>
                      </div>

                      {accessories.length > 0 ? (
                        <div className="overflow-x-auto">
                          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                            <thead className="bg-gray-50 dark:bg-gray-800">
                              <tr>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                  Name
                                </th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                  Category
                                </th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                  Quantity
                                </th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                  Condition
                                </th>
                              </tr>
                            </thead>
                            <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                              {accessories.map((accessory) => (
                                <tr key={accessory.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                                  <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                                    {accessory.name}
                                  </td>
                                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                                    {accessory.category || '-'}
                                  </td>
                                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                                    {accessory.quantity}
                                  </td>
                                  <td className="px-4 py-3 whitespace-nowrap">
                                    <Badge
                                      variant={
                                        accessory.condition === 'Good'
                                          ? 'success'
                                          : accessory.condition === 'Fair'
                                          ? 'warning'
                                          : 'danger'
                                      }
                                      size="sm"
                                    >
                                      {accessory.condition || 'Unknown'}
                                    </Badge>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <EmptyState
                          icon={<WrenchScrewdriverIcon className="w-12 h-12 mx-auto" />}
                          title="No accessories"
                          description="Add accessories to this ticket"
                        />
                      )}
                    </TabPanel>

                    {/* Activity Tab */}
                    <TabPanel className="p-4">
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Activity History</h3>

                      {activityLog.length > 0 ? (
                        <div className="space-y-4">
                          {activityLog.map((activity) => (
                            <div
                              key={activity.id}
                              className="flex items-start gap-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
                            >
                              <div className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center">
                                <ClockIcon className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                              </div>
                              <div className="flex-1">
                                <p className="text-sm text-gray-900 dark:text-white">{activity.action}</p>
                                {activity.details && (
                                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{activity.details}</p>
                                )}
                                <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                                  {activity.user?.username && `By ${activity.user.username} - `}
                                  {formatRelativeTime(activity.created_at)}
                                </p>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <EmptyState
                          icon={<ClockIcon className="w-12 h-12 mx-auto" />}
                          title="No activity yet"
                          description="Activity will appear here as changes are made"
                        />
                      )}
                    </TabPanel>

                    {/* Shipping Tab */}
                    <TabPanel className="p-4">
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                        Shipping & Tracking
                      </h3>

                      {ticket.shipping_tracking ? (
                        <div className="space-y-4">
                          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                            <div className="flex items-center gap-3 mb-3">
                              <TruckIcon className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                              <div>
                                <p className="text-sm font-medium text-gray-900 dark:text-white">
                                  Tracking Number
                                </p>
                                <p className="text-lg font-mono text-blue-600 dark:text-blue-400">
                                  {ticket.shipping_tracking}
                                </p>
                              </div>
                            </div>
                            {ticket.shipping_status && (
                              <div className="flex items-center gap-2">
                                <span className="text-sm text-gray-500 dark:text-gray-400">Status:</span>
                                <Badge
                                  variant={
                                    ticket.shipping_status.toLowerCase().includes('delivered')
                                      ? 'success'
                                      : ticket.shipping_status.toLowerCase().includes('transit')
                                      ? 'info'
                                      : 'warning'
                                  }
                                >
                                  {ticket.shipping_status}
                                </Badge>
                              </div>
                            )}
                          </div>

                          {ticket.return_tracking && (
                            <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
                              <div className="flex items-center gap-3">
                                <TruckIcon className="w-6 h-6 text-green-600 dark:text-green-400" />
                                <div>
                                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                                    Return Tracking
                                  </p>
                                  <p className="text-lg font-mono text-green-600 dark:text-green-400">
                                    {ticket.return_tracking}
                                  </p>
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      ) : (
                        <EmptyState
                          icon={<TruckIcon className="w-12 h-12 mx-auto" />}
                          title="No shipping information"
                          description="Tracking details will appear when shipping is created"
                          action={
                            <Button variant="primary" size="sm">
                              Add Tracking
                            </Button>
                          }
                        />
                      )}
                    </TabPanel>
                  </TabPanels>
                </TabGroup>
              </Card>
            </div>

            {/* Right Sidebar (1 column) */}
            <div className="space-y-6">
              {/* Quick Actions Card */}
              <Card>
                <CardHeader>Quick Actions</CardHeader>
                <div className="p-4 space-y-2">
                  <button className="w-full text-left px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md transition-colors flex items-center gap-2">
                    <PencilIcon className="w-4 h-4" />
                    Edit Ticket
                  </button>
                  <button className="w-full text-left px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md transition-colors flex items-center gap-2">
                    <UserPlusIcon className="w-4 h-4" />
                    Change Owner
                  </button>
                  <button className="w-full text-left px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md transition-colors flex items-center gap-2">
                    <DocumentTextIcon className="w-4 h-4" />
                    Clone Case
                  </button>
                  <button className="w-full text-left px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md transition-colors flex items-center gap-2">
                    <CheckCircleIcon className="w-4 h-4" />
                    Mark Resolved
                  </button>
                </div>
              </Card>

              {/* SLA Information Card */}
              <Card>
                <CardHeader>SLA Information</CardHeader>
                <div className="p-4 space-y-3">
                  <FieldRow
                    label="Response Time"
                    value={
                      <span className="text-green-600 dark:text-green-400 font-medium">
                        Within SLA
                      </span>
                    }
                  />
                  <FieldRow
                    label="Resolution Target"
                    value={
                      <span className="text-yellow-600 dark:text-yellow-400 font-medium">
                        48 hours
                      </span>
                    }
                  />
                  <FieldRow label="Days Open" value={<span className="font-bold">{daysOpen}</span>} />
                </div>
              </Card>

              {/* Customer Info Card */}
              {ticket.customer && (
                <Card>
                  <CardHeader>Customer Info</CardHeader>
                  <div className="p-4 space-y-3">
                    <div className="flex items-center gap-3 mb-3">
                      <Avatar name={ticket.customer.name} size="lg" />
                      <div>
                        <p className="font-medium text-gray-900 dark:text-white">{ticket.customer.name}</p>
                        {ticket.customer.company && (
                          <p className="text-sm text-gray-500 dark:text-gray-400">
                            {ticket.customer.company.name}
                          </p>
                        )}
                      </div>
                    </div>
                    {ticket.customer.email && (
                      <FieldRow
                        label="Email"
                        value={
                          <a
                            href={`mailto:${ticket.customer.email}`}
                            className="text-blue-600 dark:text-blue-400 hover:underline"
                          >
                            {ticket.customer.email}
                          </a>
                        }
                      />
                    )}
                    {ticket.customer.contact_number && (
                      <FieldRow
                        label="Phone"
                        value={
                          <a
                            href={`tel:${ticket.customer.contact_number}`}
                            className="text-blue-600 dark:text-blue-400 hover:underline"
                          >
                            {ticket.customer.contact_number}
                          </a>
                        }
                      />
                    )}
                    <div className="pt-3 border-t border-gray-200 dark:border-gray-700">
                      <Link
                        to={`/customers/${ticket.customer.id}`}
                        className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
                      >
                        View Customer Profile
                      </Link>
                    </div>
                  </div>
                </Card>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        title="Delete Ticket"
        size="sm"
        footer={
          <>
            <Button variant="ghost" onClick={() => setShowDeleteModal(false)}>
              Cancel
            </Button>
            <Button variant="danger" onClick={handleDelete}>
              Delete
            </Button>
          </>
        }
      >
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0">
            <ExclamationTriangleIcon className="w-5 h-5 text-red-600" />
          </div>
          <div>
            <p className="text-sm text-gray-700 dark:text-gray-300">
              Are you sure you want to delete this ticket? This action cannot be undone.
            </p>
            <p className="mt-2 text-sm font-medium text-gray-900 dark:text-white">
              Case {ticket.display_id}: {ticket.subject}
            </p>
          </div>
        </div>
      </Modal>

      {/* Assign Modal */}
      <Modal
        isOpen={showAssignModal}
        onClose={() => setShowAssignModal(false)}
        title="Assign Ticket"
        size="md"
        footer={
          <>
            <Button variant="ghost" onClick={() => setShowAssignModal(false)}>
              Cancel
            </Button>
            <Button variant="primary">Assign</Button>
          </>
        }
      >
        <div className="space-y-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Select a user to assign this ticket to.
          </p>
          {/* User selection would go here */}
          <div className="text-center py-8 text-gray-500">
            User selection coming soon...
          </div>
        </div>
      </Modal>
    </PageLayout>
  )
}

export default TicketDetailPage
