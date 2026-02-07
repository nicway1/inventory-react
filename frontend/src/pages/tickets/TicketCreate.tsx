/**
 * TicketCreate Component
 *
 * Create new service ticket page.
 */

import { useNavigate } from 'react-router-dom'
import { PageLayout } from '@/components/templates/PageLayout'

export function TicketCreate() {
  const navigate = useNavigate()

  return (
    <PageLayout
      title="New Ticket"
      subtitle="Create a new service ticket"
      breadcrumbs={[
        { label: 'Tickets', href: '/tickets' },
        { label: 'New Ticket' },
      ]}
      actions={
        <button
          onClick={() => navigate('/tickets')}
          className="sf-btn sf-btn-neutral"
        >
          Cancel
        </button>
      }
    >
      <div className="card">
        <div className="card-body">
          <p className="text-gray-600 dark:text-gray-400">
            Ticket creation form coming soon...
          </p>
        </div>
      </div>
    </PageLayout>
  )
}

export default TicketCreate
