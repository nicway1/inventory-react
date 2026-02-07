/**
 * AssetEdit Component
 *
 * Edit asset page.
 */

import { useParams, useNavigate } from 'react-router-dom'
import { PageLayout } from '@/components/templates/PageLayout'

export function AssetEdit() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  return (
    <PageLayout
      title={`Edit Asset #${id}`}
      subtitle="Modify asset details"
      breadcrumbs={[
        { label: 'Inventory', href: '/inventory' },
        { label: `Asset #${id}`, href: `/inventory/assets/${id}` },
        { label: 'Edit' },
      ]}
      actions={
        <button
          onClick={() => navigate(`/inventory/assets/${id}`)}
          className="sf-btn sf-btn-neutral"
        >
          Cancel
        </button>
      }
    >
      <div className="card">
        <div className="card-body">
          <p className="text-gray-600 dark:text-gray-400">
            Asset edit form coming soon...
          </p>
        </div>
      </div>
    </PageLayout>
  )
}

export default AssetEdit
