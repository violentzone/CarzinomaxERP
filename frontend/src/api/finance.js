/** Finance endpoints: /api/v1/finance */
import { apiGet, apiPost, apiPut, apiDelete } from '../lib/api'

export const financeApi = {
  listAccounts: (params) => apiGet('/finance/accounts', params),
  createAccount: (payload) => apiPost('/finance/accounts', payload),
  updateAccount: (id, payload) => apiPut(`/finance/accounts/${id}`, payload),
  deleteAccount: (id) => apiDelete(`/finance/accounts/${id}`),

  listInvoices: (params) => apiGet('/finance/invoices', params),
  createInvoice: (payload) => apiPost('/finance/invoices', payload),
  updateInvoice: (id, payload) => apiPut(`/finance/invoices/${id}`, payload),
  deleteInvoice: (id) => apiDelete(`/finance/invoices/${id}`),

  listPayments: (params) => apiGet('/finance/payments', params),
  createPayment: (payload) => apiPost('/finance/payments', payload),
  updatePayment: (id, payload) => apiPut(`/finance/payments/${id}`, payload),
  deletePayment: (id) => apiDelete(`/finance/payments/${id}`),

  listFixedAssets: (params) => apiGet('/finance/fixed-assets', params),
  createFixedAsset: (payload) => apiPost('/finance/fixed-assets', payload),
  updateFixedAsset: (id, payload) => apiPut(`/finance/fixed-assets/${id}`, payload),
  deleteFixedAsset: (id) => apiDelete(`/finance/fixed-assets/${id}`),

  createJournalEntry: (payload) => apiPost('/finance/journal-entries', payload),
  updateJournalEntry: (id, payload) => apiPut(`/finance/journal-entries/${id}`, payload),
  deleteJournalEntry: (id) => apiDelete(`/finance/journal-entries/${id}`),
}
