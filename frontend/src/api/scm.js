/**
 * Supply Chain endpoints: /api/v1/scm
 *
 * Two resources behind the same `has_scm_access` flag: products (the
 * company's software products: SKU, name, description, application price,
 * margin, copies sold) and purchases (goods the company buys: item name,
 * category, unit price, amount as quantity). A purchase's total is computed
 * by the server as unit_price x amount and is never sent by the client.
 */
import { apiGet, apiPost, apiPut, apiDelete } from '../lib/api'

export const scmApi = {
  listProducts: () => apiGet('/scm/product_list'),
  getProduct: (id) => apiGet(`/scm/product/${id}`),
  createProduct: (payload) => apiPost('/scm/product', payload),
  updateProduct: (id, payload) => apiPut(`/scm/product/${id}`, payload),
  deleteProduct: (id) => apiDelete(`/scm/product/${id}`),

  listPurchases: () => apiGet('/scm/purchase_list'),
  getPurchase: (id) => apiGet(`/scm/purchase/${id}`),
  createPurchase: (payload) => apiPost('/scm/purchase', payload),
  updatePurchase: (id, payload) => apiPut(`/scm/purchase/${id}`, payload),
  deletePurchase: (id) => apiDelete(`/scm/purchase/${id}`),
}
