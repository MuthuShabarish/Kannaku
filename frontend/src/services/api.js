const API_BASE = import.meta.env.VITE_API_URL || '';

function getAuthHeader() {
  const token = localStorage.getItem('kanakku_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function handleResponse(response) {
  const contentType = response.headers.get('content-type');
  const isJson = contentType && contentType.includes('application/json');
  const data = isJson ? await response.json() : await response.text();

  if (!response.ok) {
    const errorMsg = data?.error?.message || data?.detail?.message || data?.message || 'Request failed';
    const errorCode = data?.error?.code || 'API_ERROR';
    const err = new Error(errorMsg);
    err.code = errorCode;
    err.status = response.status;
    err.details = data?.error?.details || data;
    throw err;
  }

  return data;
}

export const api = {
  async getHealth() {
    const res = await fetch(`${API_BASE}/api/v1/health`);
    return handleResponse(res);
  },

  async register(payload) {
    const res = await fetch(`${API_BASE}/api/v1/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async login(payload) {
    const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async getMe() {
    const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse(res);
  },

  async getOnboardingState() {
    const res = await fetch(`${API_BASE}/api/v1/onboarding`, {
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse(res);
  },

  async saveOnboardingDraft(payload) {
    const res = await fetch(`${API_BASE}/api/v1/onboarding/draft`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async getRecommendation(answers) {
    const res = await fetch(`${API_BASE}/api/v1/onboarding/recommend`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(answers),
    });
    return handleResponse(res);
  },

  async completeOnboarding(payload) {
    const res = await fetch(`${API_BASE}/api/v1/onboarding/complete`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async getBusinessProfile() {
    const res = await fetch(`${API_BASE}/api/v1/business/profile`, {
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse(res);
  },

  async updateBusinessPreferences(payload) {
    const res = await fetch(`${API_BASE}/api/v1/business/preferences`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  // Category APIs
  async getCategories() {
    const res = await fetch(`${API_BASE}/api/v1/categories`, {
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse(res);
  },

  async createCategory(payload) {
    const res = await fetch(`${API_BASE}/api/v1/categories`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async updateCategory(categoryId, payload) {
    const res = await fetch(`${API_BASE}/api/v1/categories/${categoryId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async deleteCategory(categoryId) {
    const res = await fetch(`${API_BASE}/api/v1/categories/${categoryId}`, {
      method: 'DELETE',
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse(res);
  },

  // Product APIs
  async getProducts(params = {}) {
    const query = new URLSearchParams();
    if (params.search) query.append('search', params.search);
    if (params.category_id) query.append('category_id', params.category_id);
    if (params.is_active !== undefined) query.append('is_active', params.is_active);
    if (params.low_stock) query.append('low_stock', 'true');
    if (params.sort_by) query.append('sort_by', params.sort_by);
    if (params.order) query.append('order', params.order);
    if (params.limit) query.append('limit', params.limit);
    if (params.offset) query.append('offset', params.offset);

    const queryString = query.toString() ? `?${query.toString()}` : '';
    const res = await fetch(`${API_BASE}/api/v1/products${queryString}`, {
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse(res);
  },

  async getProduct(productId) {
    const res = await fetch(`${API_BASE}/api/v1/products/${productId}`, {
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse(res);
  },

  async createProduct(payload) {
    const res = await fetch(`${API_BASE}/api/v1/products`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async updateProduct(productId, payload) {
    const res = await fetch(`${API_BASE}/api/v1/products/${productId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async toggleProductStatus(productId, isActive) {
    const res = await fetch(`${API_BASE}/api/v1/products/${productId}/status`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify({ is_active: isActive }),
    });
    return handleResponse(res);
  },

  // Inventory APIs
  async getInventoryOverview() {
    const res = await fetch(`${API_BASE}/api/v1/inventory/overview`, {
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse(res);
  },

  async adjustStock(payload) {
    const res = await fetch(`${API_BASE}/api/v1/inventory/adjustments`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  // Customer & Khata APIs
  async getCustomers(params = {}) {
    const query = new URLSearchParams();
    if (params.search) query.append('search', params.search);
    if (params.with_balance_only) query.append('with_balance_only', 'true');
    if (params.limit) query.append('limit', params.limit);
    if (params.offset) query.append('offset', params.offset);

    const queryString = query.toString() ? `?${query.toString()}` : '';
    const res = await fetch(`${API_BASE}/api/v1/customers${queryString}`, {
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse(res);
  },

  async getCustomer(customerId) {
    const res = await fetch(`${API_BASE}/api/v1/customers/${customerId}`, {
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse(res);
  },

  async createCustomer(payload) {
    const res = await fetch(`${API_BASE}/api/v1/customers`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async updateCustomer(customerId, payload) {
    const res = await fetch(`${API_BASE}/api/v1/customers/${customerId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async recordCustomerPayment(customerId, payload) {
    const res = await fetch(`${API_BASE}/api/v1/customers/${customerId}/payments`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  // Sales & POS APIs
  async checkoutSale(payload) {
    const res = await fetch(`${API_BASE}/api/v1/sales`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async getSales(params = {}) {
    const query = new URLSearchParams();
    if (params.search) query.append('search', params.search);
    if (params.customer_id) query.append('customer_id', params.customer_id);
    if (params.payment_status) query.append('payment_status', params.payment_status);
    if (params.limit) query.append('limit', params.limit);
    if (params.offset) query.append('offset', params.offset);

    const queryString = query.toString() ? `?${query.toString()}` : '';
    const res = await fetch(`${API_BASE}/api/v1/sales${queryString}`, {
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse(res);
  },

  async getSale(saleId) {
    const res = await fetch(`${API_BASE}/api/v1/sales/${saleId}`, {
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse(res);
  },

  async getSalesOverview() {
    const res = await fetch(`${API_BASE}/api/v1/sales/overview`, {
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse(res);
  },

  // Supplier & Accounts Payable APIs
  async getSuppliers(params = {}) {
    const query = new URLSearchParams();
    if (params.search) query.append('search', params.search);
    if (params.with_balance_only) query.append('with_balance_only', 'true');
    if (params.limit) query.append('limit', params.limit);
    if (params.offset) query.append('offset', params.offset);

    const queryString = query.toString() ? `?${query.toString()}` : '';
    const res = await fetch(`${API_BASE}/api/v1/suppliers${queryString}`, {
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse(res);
  },

  async getSupplier(supplierId) {
    const res = await fetch(`${API_BASE}/api/v1/suppliers/${supplierId}`, {
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse(res);
  },

  async createSupplier(payload) {
    const res = await fetch(`${API_BASE}/api/v1/suppliers`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async updateSupplier(supplierId, payload) {
    const res = await fetch(`${API_BASE}/api/v1/suppliers/${supplierId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async recordSupplierPayment(supplierId, payload) {
    const res = await fetch(`${API_BASE}/api/v1/suppliers/${supplierId}/payments`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async getSupplierLedger(supplierId, params = {}) {
    const query = new URLSearchParams();
    if (params.limit) query.append('limit', params.limit);
    if (params.offset) query.append('offset', params.offset);

    const queryString = query.toString() ? `?${query.toString()}` : '';
    const res = await fetch(`${API_BASE}/api/v1/suppliers/${supplierId}/ledger${queryString}`, {
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse(res);
  },

  // Purchase & Inventory Receiving APIs
  async createPurchase(payload) {
    const res = await fetch(`${API_BASE}/api/v1/purchases`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async getPurchases(params = {}) {
    const query = new URLSearchParams();
    if (params.search) query.append('search', params.search);
    if (params.supplier_id) query.append('supplier_id', params.supplier_id);
    if (params.payment_status) query.append('payment_status', params.payment_status);
    if (params.limit) query.append('limit', params.limit);
    if (params.offset) query.append('offset', params.offset);

    const queryString = query.toString() ? `?${query.toString()}` : '';
    const res = await fetch(`${API_BASE}/api/v1/purchases${queryString}`, {
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse(res);
  },

  async getPurchase(purchaseId) {
    const res = await fetch(`${API_BASE}/api/v1/purchases/${purchaseId}`, {
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse(res);
  },

  async getPurchasesOverview() {
    const res = await fetch(`${API_BASE}/api/v1/purchases/overview`, {
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse(res);
  },

  // Stage 6: Expense Categories APIs
  async getExpenseCategories(params = {}) {
    const query = new URLSearchParams();
    if (params.is_active !== undefined) query.append('is_active', params.is_active);
    const queryString = query.toString() ? `?${query.toString()}` : '';
    const res = await fetch(`${API_BASE}/api/v1/expense-categories${queryString}`, {
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse(res);
  },

  async createExpenseCategory(payload) {
    const res = await fetch(`${API_BASE}/api/v1/expense-categories`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async updateExpenseCategory(categoryId, payload) {
    const res = await fetch(`${API_BASE}/api/v1/expense-categories/${categoryId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async deleteExpenseCategory(categoryId) {
    const res = await fetch(`${API_BASE}/api/v1/expense-categories/${categoryId}`, {
      method: 'DELETE',
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse(res);
  },

  // Stage 6: Operating Expenses APIs
  async getExpenses(params = {}) {
    const query = new URLSearchParams();
    if (params.start_date) query.append('start_date', params.start_date);
    if (params.end_date) query.append('end_date', params.end_date);
    if (params.category_id) query.append('category_id', params.category_id);
    if (params.payment_method) query.append('payment_method', params.payment_method);
    if (params.payment_status) query.append('payment_status', params.payment_status);
    if (params.search) query.append('search', params.search);
    if (params.limit) query.append('limit', params.limit);
    if (params.offset) query.append('offset', params.offset);

    const queryString = query.toString() ? `?${query.toString()}` : '';
    const res = await fetch(`${API_BASE}/api/v1/expenses${queryString}`, {
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse(res);
  },

  async getExpense(expenseId) {
    const res = await fetch(`${API_BASE}/api/v1/expenses/${expenseId}`, {
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse(res);
  },

  async createExpense(payload) {
    const res = await fetch(`${API_BASE}/api/v1/expenses`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async updateExpense(expenseId, payload) {
    const res = await fetch(`${API_BASE}/api/v1/expenses/${expenseId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async voidExpense(expenseId, payload) {
    const res = await fetch(`${API_BASE}/api/v1/expenses/${expenseId}/void`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async getExpensesOverview(params = {}) {
    const query = new URLSearchParams();
    if (params.start_date) query.append('start_date', params.start_date);
    if (params.end_date) query.append('end_date', params.end_date);
    const queryString = query.toString() ? `?${query.toString()}` : '';
    const res = await fetch(`${API_BASE}/api/v1/expenses/overview${queryString}`, {
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse(res);
  },

  // Stage 6: Operating Cashbook APIs
  async getCashbookTransactions(params = {}) {
    const query = new URLSearchParams();
    if (params.start_date) query.append('start_date', params.start_date);
    if (params.end_date) query.append('end_date', params.end_date);
    if (params.direction) query.append('direction', params.direction);
    if (params.payment_mode) query.append('payment_mode', params.payment_mode);
    if (params.source_type) query.append('source_type', params.source_type);
    if (params.limit) query.append('limit', params.limit);
    if (params.offset) query.append('offset', params.offset);

    const queryString = query.toString() ? `?${query.toString()}` : '';
    const res = await fetch(`${API_BASE}/api/v1/cashbook/transactions${queryString}`, {
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse(res);
  },

  async getCashbookSummary(params = {}) {
    const query = new URLSearchParams();
    if (params.start_date) query.append('start_date', params.start_date);
    if (params.end_date) query.append('end_date', params.end_date);
    const queryString = query.toString() ? `?${query.toString()}` : '';
    const res = await fetch(`${API_BASE}/api/v1/cashbook/summary${queryString}`, {
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse(res);
  },

  // Stage 7: Business Reports & Profit APIs
  async getReportsSummary(params = {}) {
    const query = new URLSearchParams();
    if (params.start_date) query.append('start_date', params.start_date);
    if (params.end_date) query.append('end_date', params.end_date);
    const queryString = query.toString() ? `?${query.toString()}` : '';
    const res = await fetch(`${API_BASE}/api/v1/reports/summary${queryString}`, {
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse(res);
  },

  async getSalesTrends(params = {}) {
    const query = new URLSearchParams();
    if (params.start_date) query.append('start_date', params.start_date);
    if (params.end_date) query.append('end_date', params.end_date);
    if (params.interval) query.append('interval', params.interval);
    const queryString = query.toString() ? `?${query.toString()}` : '';
    const res = await fetch(`${API_BASE}/api/v1/reports/sales-trends${queryString}`, {
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse(res);
  },

  async getProductSalesReport(params = {}) {
    const query = new URLSearchParams();
    if (params.start_date) query.append('start_date', params.start_date);
    if (params.end_date) query.append('end_date', params.end_date);
    if (params.limit) query.append('limit', params.limit);
    const queryString = query.toString() ? `?${query.toString()}` : '';
    const res = await fetch(`${API_BASE}/api/v1/reports/product-sales${queryString}`, {
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse(res);
  },

  async getProfitOverview(params = {}) {
    const query = new URLSearchParams();
    if (params.start_date) query.append('start_date', params.start_date);
    if (params.end_date) query.append('end_date', params.end_date);
    const queryString = query.toString() ? `?${query.toString()}` : '';
    const res = await fetch(`${API_BASE}/api/v1/reports/profit-overview${queryString}`, {
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse(res);
  },

  // Stage 7: Daily Cash Drawer Closing APIs
  async getCurrentCashDrawer(params = {}) {
    const query = new URLSearchParams();
    if (params.closing_date) query.append('closing_date', params.closing_date);
    const queryString = query.toString() ? `?${query.toString()}` : '';
    const res = await fetch(`${API_BASE}/api/v1/cash-closing/current${queryString}`, {
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse(res);
  },

  async closeCashDrawer(payload) {
    const res = await fetch(`${API_BASE}/api/v1/cash-closing/close`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async reopenCashClosing(closingId, payload) {
    const res = await fetch(`${API_BASE}/api/v1/cash-closing/${closingId}/reopen`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async getCashClosingHistory(params = {}) {
    const query = new URLSearchParams();
    if (params.start_date) query.append('start_date', params.start_date);
    if (params.end_date) query.append('end_date', params.end_date);
    if (params.limit) query.append('limit', params.limit);
    if (params.offset) query.append('offset', params.offset);
    const queryString = query.toString() ? `?${query.toString()}` : '';
    const res = await fetch(`${API_BASE}/api/v1/cash-closing/history${queryString}`, {
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse(res);
  },

  async getCashClosingDetail(closingId) {
    const res = await fetch(`${API_BASE}/api/v1/cash-closing/${closingId}`, {
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse(res);
  },

  async logout() {
    try {
      await fetch(`${API_BASE}/api/v1/auth/logout`, {
        method: 'POST',
        headers: {
          ...getAuthHeader(),
        },
      });
    } finally {
      localStorage.removeItem('kanakku_token');
    }
  },
};
