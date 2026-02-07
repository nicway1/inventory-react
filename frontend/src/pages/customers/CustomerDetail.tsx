/**
 * CustomerDetail Component
 *
 * View customer details page.
 */

import { useParams, useNavigate } from 'react-router-dom'
import { PencilIcon } from '@heroicons/react/24/outline'
import { PageLayout } from '@/components/templates/PageLayout'

export function CustomerDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  return (
    <PageLayout
      title={`Customer #${id}`}
      subtitle="Customer account details"
      breadcrumbs={[
        { label: 'Customers', href: '/customers' },
        { label: `Customer #${id}` },
      ]}
      actions={
        <button
          onClick={() => navigate(`/customers/${id}/edit`)}
          className="sf-btn sf-btn-brand inline-flex items-center gap-2"
        >
          <PencilIcon className="h-4 w-4" />
          Edit Customer
        </button>
      }
    >
      <div className="card">
        <div className="card-body">
          <p className="text-gray-600 dark:text-gray-400">
            Customer detail view coming soon...
          </p>
        </div>
      </div>
    </PageLayout>
  )
}

export default CustomerDetail
