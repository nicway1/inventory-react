/**
 * AssetCreate Component
 *
 * Create new asset page.
 */

import { useNavigate } from 'react-router-dom'
import { PageLayout } from '@/components/templates/PageLayout'

export function AssetCreate() {
  const navigate = useNavigate()

  return (
    <PageLayout
      title="New Asset"
      subtitle="Add a new asset to inventory"
      breadcrumbs={[
        { label: 'Inventory', href: '/inventory' },
        { label: 'New Asset' },
      ]}
      actions={
        <button
          onClick={() => navigate('/inventory')}
          className="sf-btn sf-btn-neutral"
        >
          Cancel
        </button>
      }
    >
      <div className="card">
        <div className="card-body">
          <p className="text-gray-600 dark:text-gray-400">
            Asset creation form coming soon...
          </p>
        </div>
      </div>
    </PageLayout>
  )
}

export default AssetCreate
