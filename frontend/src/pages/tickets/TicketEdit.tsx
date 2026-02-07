/**
 * TicketEdit Component
 *
 * Edit service ticket page.
 */

import { useParams, useNavigate } from 'react-router-dom'
import { PageLayout } from '@/components/templates/PageLayout'

export function TicketEdit() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  return (
    <PageLayout
      title={`Edit Ticket #${id}`}
      subtitle="Modify service ticket details"
      breadcrumbs={[
        { label: 'Tickets', href: '/tickets' },
        { label: `Ticket #${id}`, href: `/tickets/${id}` },
        { label: 'Edit' },
      ]}
      actions={
        <button
          onClick={() => navigate(`/tickets/${id}`)}
          className="sf-btn sf-btn-neutral"
        >
          Cancel
        </button>
      }
    >
      <div className="card">
        <div className="card-body">
          <p className="text-gray-600 dark:text-gray-400">
            Ticket edit form coming soon...
          </p>
        </div>
      </div>
    </PageLayout>
  )
}

export default TicketEdit
