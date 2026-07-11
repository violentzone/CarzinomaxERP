/** Supply Chain endpoints: /api/v1/scm */
import { apiGet, apiPost, apiPut, apiDelete } from '../lib/api'

export const scmApi = {
  listCategories: () => apiGet('/scm/categories'),
  createCategory: (payload) => apiPost('/scm/categories', payload),
  updateCategory: (id, payload) => apiPut(`/scm/categories/${id}`, payload),
  deleteCategory: (id) => apiDelete(`/scm/categories/${id}`),

  listProducts: (params) => apiGet('/scm/products', params),
  createProduct: (payload) => apiPost('/scm/products', payload),
  updateProduct: (id, payload) => apiPut(`/scm/products/${id}`, payload),
  deleteProduct: (id) => apiDelete(`/scm/products/${id}`),

  listWarehouses: () => apiGet('/scm/warehouses'),
  createWarehouse: (payload) => apiPost('/scm/warehouses', payload),
  updateWarehouse: (id, payload) => apiPut(`/scm/warehouses/${id}`, payload),
  deleteWarehouse: (id) => apiDelete(`/scm/warehouses/${id}`),

  listStocks: (params) => apiGet('/scm/stocks', params),
  updateStock: (id, payload) => apiPut(`/scm/stocks/${id}`, payload),
  deleteStock: (id) => apiDelete(`/scm/stocks/${id}`),

  listVendors: () => apiGet('/scm/vendors'),
  createVendor: (payload) => apiPost('/scm/vendors', payload),
  updateVendor: (id, payload) => apiPut(`/scm/vendors/${id}`, payload),
  deleteVendor: (id) => apiDelete(`/scm/vendors/${id}`),

  createPurchaseOrder: (payload) => apiPost('/scm/purchase-orders', payload),
  updatePurchaseOrder: (id, payload) => apiPut(`/scm/purchase-orders/${id}`, payload),
  deletePurchaseOrder: (id) => apiDelete(`/scm/purchase-orders/${id}`),
  receivePurchaseOrder: (poId, warehouseId) =>
    apiPost(`/scm/purchase-orders/${poId}/receive?warehouse_id=${warehouseId}`),

  createShipment: (payload) => apiPost('/scm/shipments', payload),
  updateShipment: (id, payload) => apiPut(`/scm/shipments/${id}`, payload),
  deleteShipment: (id) => apiDelete(`/scm/shipments/${id}`),
}
