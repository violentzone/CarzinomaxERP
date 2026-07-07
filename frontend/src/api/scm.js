/** Supply Chain endpoints: /api/v1/scm */
import { apiGet, apiPost } from '../lib/api'

export const scmApi = {
  listCategories: () => apiGet('/scm/categories'),
  createCategory: (payload) => apiPost('/scm/categories', payload),

  listProducts: (params) => apiGet('/scm/products', params),
  createProduct: (payload) => apiPost('/scm/products', payload),

  listWarehouses: () => apiGet('/scm/warehouses'),
  createWarehouse: (payload) => apiPost('/scm/warehouses', payload),

  listStocks: (params) => apiGet('/scm/stocks', params),

  listVendors: () => apiGet('/scm/vendors'),
  createVendor: (payload) => apiPost('/scm/vendors', payload),

  createPurchaseOrder: (payload) => apiPost('/scm/purchase-orders', payload),
  receivePurchaseOrder: (poId, warehouseId) =>
    apiPost(`/scm/purchase-orders/${poId}/receive?warehouse_id=${warehouseId}`),

  createShipment: (payload) => apiPost('/scm/shipments', payload),
}
