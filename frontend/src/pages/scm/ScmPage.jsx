import { useState } from 'react'
import {
  Boxes,
  Building2,
  Package,
  ShoppingCart,
  Tags,
  Truck,
  Warehouse,
} from 'lucide-react'
import PageHeader from '../../components/ui/PageHeader'
import Tabs from '../../components/ui/Tabs'
import ResourceSection from '../../components/ResourceSection'
import { scmApi } from '../../api/scm'
import { useList } from '../../lib/useList'
import { currency } from '../../lib/format'
import StocksSection from './StocksSection'
import PurchaseOrdersSection from './PurchaseOrdersSection'
import ShipmentsSection from './ShipmentsSection'

const TABS = [
  { key: 'categories', label: 'Categories', icon: Tags },
  { key: 'products', label: 'Products', icon: Package },
  { key: 'warehouses', label: 'Warehouses', icon: Warehouse },
  { key: 'stocks', label: 'Stocks', icon: Boxes },
  { key: 'vendors', label: 'Vendors', icon: Building2 },
  { key: 'purchase_orders', label: 'Purchase Orders', icon: ShoppingCart },
  { key: 'shipments', label: 'Shipments', icon: Truck },
]

/**
 * Products create form needs a category foreign-key <select>, so we wrap
 * ResourceSection: load categories, build the option list + an id→name map for
 * the table column, then render the generic list+create section.
 */
function ProductsSection() {
  const { rows: categories } = useList(() => scmApi.listCategories())
  const catName = new Map((categories || []).map((c) => [String(c.id), c.name]))
  const categoryOptions = (categories || []).map((c) => ({ value: String(c.id), label: c.name }))

  return (
    <ResourceSection
      title="Products"
      subtitle="Catalog of stock-keeping units and their pricing."
      moduleName="Supply Chain"
      fetcher={() => scmApi.listProducts()}
      create={scmApi.createProduct}
      createLabel="New product"
      createTitle="New product"
      update={(row, payload) => scmApi.updateProduct(row.id, payload)}
      updateTitle="Edit product"
      remove={(row) => scmApi.deleteProduct(row.id)}
      removeLabel="product"
      removeHint="Its stock records and movements will also be deleted."
      emptyHint="Add your first product to start tracking stock."
      columns={[
        { key: 'sku', header: 'SKU', render: (r) => <span className="mono cell-strong">{r.sku}</span> },
        { key: 'name', header: 'Name', render: (r) => <span className="cell-strong">{r.name}</span> },
        { key: 'category', header: 'Category', render: (r) => catName.get(String(r.category_id)) || '—' },
        { key: 'unit_price', header: 'Unit price', align: 'right', render: (r) => <span className="cell-num">{currency(r.unit_price)}</span> },
        { key: 'cost', header: 'Cost', align: 'right', render: (r) => <span className="cell-num">{currency(r.cost)}</span> },
      ]}
      fields={[
        { key: 'sku', label: 'SKU', required: true, placeholder: 'SKU-001' },
        { key: 'name', label: 'Name', required: true, placeholder: 'Wireless mouse' },
        { key: 'description', label: 'Description', type: 'textarea', full: true, nullable: true },
        { key: 'unit_price', label: 'Unit price', type: 'number', step: '0.01' },
        { key: 'cost', label: 'Cost', type: 'number', step: '0.01' },
        {
          key: 'category_id',
          label: 'Category',
          type: 'select',
          required: true,
          options: categoryOptions,
          placeholder: categoryOptions.length ? 'Select category…' : 'Create a category first',
        },
      ]}
    />
  )
}

/** Supply Chain module: inventory, procurement, vendors and logistics. */
export default function ScmPage() {
  const [tab, setTab] = useState('categories')

  return (
    <div className="module-page">
      <PageHeader
        title="Supply Chain"
        subtitle="Inventory, procurement, vendors, and logistics."
        icon={Boxes}
      />
      <Tabs tabs={TABS} active={tab} onChange={setTab} idBase="scm" />

      <div className="tab-panel">
        {tab === 'categories' && (
          <ResourceSection
            title="Categories"
            subtitle="Group products for reporting and organization."
            moduleName="Supply Chain"
            fetcher={() => scmApi.listCategories()}
            create={scmApi.createCategory}
            createLabel="New category"
            createTitle="New category"
            update={(row, payload) => scmApi.updateCategory(row.id, payload)}
            updateTitle="Edit category"
            remove={(row) => scmApi.deleteCategory(row.id)}
            removeLabel="category"
            removeHint="Categories that still have products cannot be deleted."
            emptyHint="Create a category to classify your products."
            columns={[
              { key: 'name', header: 'Name', render: (r) => <span className="cell-strong">{r.name}</span> },
              { key: 'description', header: 'Description', render: (r) => <span className="muted">{r.description || '—'}</span> },
            ]}
            fields={[
              { key: 'name', label: 'Name', required: true, placeholder: 'Electronics' },
              { key: 'description', label: 'Description', type: 'textarea', full: true, nullable: true },
            ]}
          />
        )}

        {tab === 'products' && <ProductsSection />}

        {tab === 'warehouses' && (
          <ResourceSection
            title="Warehouses"
            subtitle="Storage locations that hold stock."
            moduleName="Supply Chain"
            fetcher={() => scmApi.listWarehouses()}
            create={scmApi.createWarehouse}
            createLabel="New warehouse"
            createTitle="New warehouse"
            update={(row, payload) => scmApi.updateWarehouse(row.id, payload)}
            updateTitle="Edit warehouse"
            remove={(row) => scmApi.deleteWarehouse(row.id)}
            removeLabel="warehouse"
            removeHint="Its stock records and movements will also be deleted."
            emptyHint="Add a warehouse to store and move inventory."
            columns={[
              { key: 'code', header: 'Code', render: (r) => <span className="mono cell-strong">{r.code}</span> },
              { key: 'name', header: 'Name', render: (r) => <span className="cell-strong">{r.name}</span> },
              { key: 'location', header: 'Location', render: (r) => r.location || '—' },
            ]}
            fields={[
              { key: 'code', label: 'Code', required: true, placeholder: 'WH-01' },
              { key: 'name', label: 'Name', required: true, placeholder: 'Central warehouse' },
              { key: 'location', label: 'Location', nullable: true, placeholder: 'City, country' },
            ]}
          />
        )}

        {tab === 'stocks' && <StocksSection />}

        {tab === 'vendors' && (
          <ResourceSection
            title="Vendors"
            subtitle="Suppliers you purchase goods and services from."
            moduleName="Supply Chain"
            fetcher={() => scmApi.listVendors()}
            create={scmApi.createVendor}
            createLabel="New vendor"
            createTitle="New vendor"
            update={(row, payload) => scmApi.updateVendor(row.id, payload)}
            updateTitle="Edit vendor"
            remove={(row) => scmApi.deleteVendor(row.id)}
            removeLabel="vendor"
            removeHint="Vendors with purchase orders cannot be deleted."
            emptyHint="Add a vendor before raising purchase orders."
            columns={[
              { key: 'code', header: 'Code', render: (r) => <span className="mono cell-strong">{r.code}</span> },
              { key: 'name', header: 'Name', render: (r) => <span className="cell-strong">{r.name}</span> },
              { key: 'email', header: 'Email', render: (r) => r.email || '—' },
              { key: 'phone', header: 'Phone', render: (r) => r.phone || '—' },
            ]}
            fields={[
              { key: 'code', label: 'Code', required: true, placeholder: 'VEN-01' },
              { key: 'name', label: 'Name', required: true, placeholder: 'Acme Supplies' },
              { key: 'email', label: 'Email', type: 'email', nullable: true, placeholder: 'sales@acme.com' },
              { key: 'phone', label: 'Phone', nullable: true, placeholder: '+1 555 0100' },
              { key: 'address', label: 'Address', type: 'textarea', full: true, nullable: true },
            ]}
          />
        )}

        {tab === 'purchase_orders' && <PurchaseOrdersSection />}
        {tab === 'shipments' && <ShipmentsSection />}
      </div>
    </div>
  )
}
