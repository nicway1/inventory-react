/**
 * CustomerCreate Component
 *
 * Create new customer page.
 */

import { useNavigate } from 'react-router-dom'
import { PageLayout } from '@/components/templates/PageLayout'

export function CustomerCreate() {
  const navigate = useNavigate()

  return (
    <PageLayout
      title="New Customer"
      subtitle="Create a new customer account"
      breadcrumbs={[
        { label: 'Customers', href: '/customers' },
        { label: 'New Customer' },
      ]}
      actions={
        <button
          onClick={() => navigate('/customers')}
          className="sf-btn sf-btn-neutral"
        >
          Cancel
        </button>
      }
    >
      <div className="card">
        <div className="card-body">
          <p className="text-gray-600 dark:text-gray-400">
            Customer creation form coming soon...
          </p>
        </div>
      </div>
    </PageLayout>
  )
}

export default CustomerCreate
