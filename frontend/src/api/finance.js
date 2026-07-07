/** Finance endpoints: /api/v1/finance */
import { apiGet, apiPost } from '../lib/api'

export const financeApi = {
  listAccounts: (params) => apiGet('/finance/accounts', params),
  createAccount: (payload) => apiPost('/finance/accounts', payload),

  listInvoices: (params) => apiGet('/finance/invoices', params),
  createInvoice: (payload) => apiPost('/finance/invoices', payload),

  createPayment: (payload) => apiPost('/finance/payments', payload),

  listFixedAssets: (params) => apiGet('/finance/fixed-assets', params),
  createFixedAsset: (payload) => apiPost('/finance/fixed-assets', payload),

  createJournalEntry: (payload) => apiPost('/finance/journal-entries', payload),
}
