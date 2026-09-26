/**
 * Supply Chain endpoints: /api/v1/scm
 *
 * The SCM module is a product / purchase catalog: SKU, name, description,
 * list price and unit cost.
 */
import { apiGet, apiPost, apiPut, apiDelete } from '../lib/api'

export const scmApi = {
  listProducts: () => apiGet('/scm/product_list'),
  getProduct: (id) => apiGet(`/scm/product/${id}`),
  createProduct: (payload) => apiPost('/scm/product', payload),
  updateProduct: (id, payload) => apiPut(`/scm/product/${id}`, payload),
  deleteProduct: (id) => apiDelete(`/scm/product/${id}`),
}
