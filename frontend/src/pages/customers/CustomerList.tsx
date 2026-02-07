/**
 * CustomerList Component
 *
 * Customer list page with search and filtering.
 */

import { useNavigate } from 'react-router-dom'
import { PlusIcon } from '@heroicons/react/24/outline'
import { PageLayout } from '@/components/templates/PageLayout'

export function CustomerList() {
  const navigate = useNavigate()

  return (
    <PageLayout
      title="Customers"
      subtitle="Manage customer accounts and contacts"
      breadcrumbs={[{ label: 'Customers' }]}
      actions={
        <button
          onClick={() => navigate('/customers/new')}
          className="sf-btn sf-btn-brand inline-flex items-center gap-2"
        >
          <PlusIcon className="h-4 w-4" />
          New Customer
        </button>
      }
    >
      <div className="card">
        <div className="card-body">
          <p className="text-gray-600 dark:text-gray-400">
            Customer list coming soon...
          </p>
        </div>
      </div>
    </PageLayout>
  )
}

export default CustomerList
