/**
 * TicketList Component
 *
 * Service ticket list page with filtering and search.
 */

import { useNavigate } from 'react-router-dom'
import { PlusIcon } from '@heroicons/react/24/outline'
import { PageLayout } from '@/components/templates/PageLayout'

export function TicketList() {
  const navigate = useNavigate()

  return (
    <PageLayout
      title="Tickets"
      subtitle="Manage repair and service tickets"
      breadcrumbs={[{ label: 'Tickets' }]}
      actions={
        <button
          onClick={() => navigate('/tickets/new')}
          className="sf-btn sf-btn-brand inline-flex items-center gap-2"
        >
          <PlusIcon className="h-4 w-4" />
          New Ticket
        </button>
      }
    >
      <div className="card">
        <div className="card-body">
          <p className="text-gray-600 dark:text-gray-400">
            Ticket list coming soon...
          </p>
        </div>
      </div>
    </PageLayout>
  )
}

export default TicketList
