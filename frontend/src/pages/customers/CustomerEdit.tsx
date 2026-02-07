/**
 * CustomerEdit Component
 *
 * Edit customer page.
 */

import { useParams, useNavigate } from 'react-router-dom'
import { PageLayout } from '@/components/templates/PageLayout'

export function CustomerEdit() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  return (
    <PageLayout
      title={`Edit Customer #${id}`}
      subtitle="Modify customer account details"
      breadcrumbs={[
        { label: 'Customers', href: '/customers' },
        { label: `Customer #${id}`, href: `/customers/${id}` },
        { label: 'Edit' },
      ]}
      actions={
        <button
          onClick={() => navigate(`/customers/${id}`)}
          className="sf-btn sf-btn-neutral"
        >
          Cancel
        </button>
      }
    >
      <div className="card">
        <div className="card-body">
          <p className="text-gray-600 dark:text-gray-400">
            Customer edit form coming soon...
          </p>
        </div>
      </div>
    </PageLayout>
  )
}

export default CustomerEdit
