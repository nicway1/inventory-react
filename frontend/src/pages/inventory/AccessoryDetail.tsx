/**
 * AccessoryDetail Component
 *
 * View accessory details page.
 */

import { useParams, useNavigate } from 'react-router-dom'
import { PageLayout } from '@/components/templates/PageLayout'

export function AccessoryDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  return (
    <PageLayout
      title={`Accessory #${id}`}
      subtitle="Accessory details"
      breadcrumbs={[
        { label: 'Inventory', href: '/inventory' },
        { label: `Accessory #${id}` },
      ]}
      actions={
        <button
          onClick={() => navigate('/inventory')}
          className="sf-btn sf-btn-neutral"
        >
          Back to Inventory
        </button>
      }
    >
      <div className="card">
        <div className="card-body">
          <p className="text-gray-600 dark:text-gray-400">
            Accessory detail view coming soon...
          </p>
        </div>
      </div>
    </PageLayout>
  )
}

export default AccessoryDetail
