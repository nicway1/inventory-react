/**
 * TicketDetail Component
 *
 * View service ticket details page.
 */

import { useParams, useNavigate } from 'react-router-dom'
import { PencilIcon } from '@heroicons/react/24/outline'
import { PageLayout } from '@/components/templates/PageLayout'

export function TicketDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  return (
    <PageLayout
      title={`Ticket #${id}`}
      subtitle="Service ticket details"
      breadcrumbs={[
        { label: 'Tickets', href: '/tickets' },
        { label: `Ticket #${id}` },
      ]}
      actions={
        <button
          onClick={() => navigate(`/tickets/${id}/edit`)}
          className="sf-btn sf-btn-brand inline-flex items-center gap-2"
        >
          <PencilIcon className="h-4 w-4" />
          Edit Ticket
        </button>
      }
    >
      <div className="card">
        <div className="card-body">
          <p className="text-gray-600 dark:text-gray-400">
            Ticket detail view coming soon...
          </p>
        </div>
      </div>
    </PageLayout>
  )
}

export default TicketDetail
