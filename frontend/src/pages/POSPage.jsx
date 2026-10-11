import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useI18n } from '../context/I18nContext';
import { api } from '../services/api';
import {
  ShoppingCart,
  Search,
  Plus,
  Minus,
  Trash2,
  User,
  CreditCard,
  Banknote,
  Smartphone,
  Receipt,
  AlertCircle,
  Layers
} from 'lucide-react';
import { Button } from '../components/common/Button';
import { Input } from '../components/common/Input';
import { LoadingSpinner, Toast } from '../components/common/Feedback';
import { ReceiptModal } from '../components/pos/ReceiptModal';

export function POSPage() {
  const { t, formatCurrency } = useI18n();

  // Active View Tab: 'pos' or 'history'
  const [activeTab, setActiveTab] = useState('pos');

  // Products & Categories
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [productSearch, setProductSearch] = useState('');
  const [isLoadingProducts, setIsLoadingProducts] = useState(true);

  // Cart State: [{ product, quantity, discount_amount }]
  const [cart, setCart] = useState([]);
  const [cartDiscount, setCartDiscount] = useState('0');

  // Customer Association
  const [customers, setCustomers] = useState([]);
  const [selectedCustomerId, setSelectedCustomerId] = useState('');
  const [showQuickCustomerModal, setShowQuickCustomerModal] = useState(false);
  const [quickCustomerForm, setQuickCustomerForm] = useState({ name: '', phone: '', credit_limit: '0' });

  // Payment Options
  const [paymentMethod, setPaymentMethod] = useState('cash'); // 'cash', 'upi', 'card', 'credit', 'split'
  const [splitCash, setSplitCash] = useState('');
  const [splitUpi, setSplitUpi] = useState('');
  const [splitCard, setSplitCard] = useState('');
  const [saleNotes, setSaleNotes] = useState('');

  // Checkout Status & Modals
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorBanner, setErrorBanner] = useState(null);
  const [completedSale, setCompletedSale] = useState(null);
  const [toastMessage, setToastMessage] = useState(null);

  // Sales History
  const [salesHistory, setSalesHistory] = useState([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  const loadProducts = useCallback(async () => {
    try {
      setIsLoadingProducts(true);
      const res = await api.getProducts({ is_active: true, limit: 100 });
      setProducts(res.data || []);
    } catch (err) {
      console.error('Failed to load products:', err);
    } finally {
      setIsLoadingProducts(false);
    }
  }, []);

  const loadCategories = useCallback(async () => {
    try {
      const res = await api.getCategories();
      setCategories(res.data || []);
    } catch (err) {
      console.error('Failed to load categories:', err);
    }
  }, []);

  const loadCustomers = useCallback(async () => {
    try {
      const res = await api.getCustomers({ limit: 100 });
      setCustomers(res.data || []);
    } catch (err) {
      console.error('Failed to load customers:', err);
    }
  }, []);

  const loadSalesHistory = useCallback(async () => {
    try {
      setIsLoadingHistory(true);
      const res = await api.getSales({ limit: 50 });
      setSalesHistory(res.data || []);
    } catch (err) {
      console.error('Failed to load sales history:', err);
    } finally {
      setIsLoadingHistory(false);
    }
  }, []);

  // Load Initial Data
  useEffect(() => {
    loadProducts();
    loadCategories();
    loadCustomers();
  }, [loadProducts, loadCategories, loadCustomers]);

  useEffect(() => {
    if (activeTab === 'history') {
      loadSalesHistory();
    }
  }, [activeTab, loadSalesHistory]);

  // Filtered Products Catalog
  const filteredProducts = useMemo(() => {
    return products.filter((p) => {
      const matchesCategory = !selectedCategory || p.category_id === selectedCategory;
      const matchesSearch =
        !productSearch ||
        p.name.toLowerCase().includes(productSearch.toLowerCase()) ||
        (p.tamil_name && p.tamil_name.toLowerCase().includes(productSearch.toLowerCase())) ||
        (p.sku && p.sku.toLowerCase().includes(productSearch.toLowerCase()));
      return matchesCategory && matchesSearch;
    });
  }, [products, selectedCategory, productSearch]);

  // Cart Calculations
  const cartSubtotal = useMemo(() => {
    return cart.reduce((sum, item) => {
      const unitPrice = parseFloat(item.product.selling_price) || 0;
      const qty = parseFloat(item.quantity) || 0;
      const lineDisc = parseFloat(item.discount_amount) || 0;
      return sum + Math.max(0, unitPrice * qty - lineDisc);
    }, 0);
  }, [cart]);

  const overallDiscountNum = parseFloat(cartDiscount) || 0;
  const cartTotal = Math.max(0, cartSubtotal - overallDiscountNum);

  // Cart Handlers
  const addToCart = (product) => {
    setErrorBanner(null);
    const existingIndex = cart.findIndex((item) => item.product.id === product.id);
    const currentStock = parseFloat(product.current_stock) || 0;

    if (currentStock <= 0) {
      setErrorBanner(`${product.name} is out of stock!`);
      return;
    }

    if (existingIndex > -1) {
      const currentQty = parseFloat(cart[existingIndex].quantity) || 0;
      if (currentQty + 1 > currentStock) {
        setErrorBanner(`Cannot add more than available stock (${currentStock} ${product.unit}) for ${product.name}.`);
        return;
      }
      const newCart = [...cart];
      newCart[existingIndex].quantity = (currentQty + 1).toString();
      setCart(newCart);
    } else {
      setCart([...cart, { product, quantity: '1', discount_amount: '0' }]);
    }
  };

  const updateQuantity = (productId, delta) => {
    setErrorBanner(null);
    const index = cart.findIndex((item) => item.product.id === productId);
    if (index === -1) return;

    const item = cart[index];
    const currentQty = parseFloat(item.quantity) || 0;
    const newQty = currentQty + delta;
    const currentStock = parseFloat(item.product.current_stock) || 0;

    if (newQty <= 0) {
      removeFromCart(productId);
      return;
    }

    if (newQty > currentStock) {
      setErrorBanner(`Maximum available stock is ${currentStock} ${item.product.unit}.`);
      return;
    }

    const newCart = [...cart];
    newCart[index].quantity = newQty.toString();
    setCart(newCart);
  };

  const removeFromCart = (productId) => {
    setCart(cart.filter((item) => item.product.id !== productId));
  };

  const clearCart = () => {
    setCart([]);
    setCartDiscount('0');
    setPaymentMethod('cash');
    setSplitCash('');
    setSplitUpi('');
    setSplitCard('');
    setSelectedCustomerId('');
    setErrorBanner(null);
  };

  // Quick Customer Creation
  const handleCreateQuickCustomer = async (e) => {
    e.preventDefault();
    if (!quickCustomerForm.name.trim() || !quickCustomerForm.phone.trim()) {
      setErrorBanner('Customer name and phone number are required.');
      return;
    }
    try {
      const res = await api.createCustomer(quickCustomerForm);
      setCustomers([res.data, ...customers]);
      setSelectedCustomerId(res.data.id);
      setShowQuickCustomerModal(false);
      setQuickCustomerForm({ name: '', phone: '', credit_limit: '0' });
      setToastMessage('Customer created and selected!');
    } catch (err) {
      setErrorBanner(err.message || 'Failed to create customer');
    }
  };

  // Selected Customer Entity
  const selectedCustomer = useMemo(() => {
    return customers.find((c) => c.id === selectedCustomerId) || null;
  }, [customers, selectedCustomerId]);

  // Checkout Submission
  const handleCheckout = async () => {
    setErrorBanner(null);

    if (cart.length === 0) {
      setErrorBanner('Cart is empty. Please add items to checkout.');
      return;
    }

    // Validation for Credit Sale
    if (paymentMethod === 'credit' && !selectedCustomerId) {
      setErrorBanner('A customer must be selected to record a credit sale (Khata).');
      return;
    }

    // Prepare Items
    const itemsPayload = cart.map((item) => ({
      product_id: item.product.id,
      quantity: parseFloat(item.quantity).toFixed(4),
      discount_amount: (parseFloat(item.discount_amount) || 0).toFixed(4),
    }));

    // Split Payments payload
    let splitPaymentsPayload = null;
    if (paymentMethod === 'split') {
      splitPaymentsPayload = [];
      const cashVal = parseFloat(splitCash) || 0;
      const upiVal = parseFloat(splitUpi) || 0;
      const cardVal = parseFloat(splitCard) || 0;

      if (cashVal > 0) splitPaymentsPayload.push({ mode: 'cash', amount: cashVal.toFixed(4) });
      if (upiVal > 0) splitPaymentsPayload.push({ mode: 'upi', amount: upiVal.toFixed(4) });
      if (cardVal > 0) splitPaymentsPayload.push({ mode: 'card', amount: cardVal.toFixed(4) });

      const totalSplit = cashVal + upiVal + cardVal;
      if (totalSplit < cartTotal && !selectedCustomerId) {
        setErrorBanner('Split payment has remaining unpaid balance; please select a customer for credit.');
        return;
      }
    }

    const payload = {
      items: itemsPayload,
      customer_id: selectedCustomerId || null,
      discount_amount: (parseFloat(cartDiscount) || 0).toFixed(4),
      payment_method: paymentMethod,
      split_payments: splitPaymentsPayload,
      notes: saleNotes.trim() || null,
      idempotency_key: `pos-${Date.now()}-${Math.random().toString(36).substring(2, 8)}`,
    };

    try {
      setIsSubmitting(true);
      const res = await api.checkoutSale(payload);
      setCompletedSale(res.data);
      setToastMessage(t('checkout_success'));
      clearCart();
      loadProducts(); // Refresh catalog stock counts immediately
    } catch (err) {
      console.error('Checkout failed:', err);
      setErrorBanner(err.message || 'Checkout failed. Please check stock balances.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="pos-page" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Top Header & Mode Toggle */}
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '1rem' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 'var(--font-size-2xl)', fontWeight: 800, color: 'var(--color-primary)' }}>
            {t('pos_billing')}
          </h1>
          <p style={{ margin: 0, fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>
            {t('pos_subtitle')}
          </p>
        </div>

        {/* View Switcher: POS vs History */}
        <div style={{ display: 'flex', backgroundColor: 'var(--color-bg-subtle)', borderRadius: 'var(--radius-md)', padding: '0.25rem', gap: '0.25rem' }}>
          <button
            onClick={() => setActiveTab('pos')}
            style={{
              padding: '0.5rem 1rem',
              borderRadius: 'var(--radius-sm)',
              border: 'none',
              backgroundColor: activeTab === 'pos' ? '#ffffff' : 'transparent',
              fontWeight: activeTab === 'pos' ? 700 : 500,
              color: activeTab === 'pos' ? 'var(--color-primary)' : 'var(--color-text-muted)',
              boxShadow: activeTab === 'pos' ? 'var(--shadow-sm)' : 'none',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.375rem',
            }}
          >
            <ShoppingCart size={16} />
            <span>POS Register</span>
          </button>
          <button
            onClick={() => setActiveTab('history')}
            style={{
              padding: '0.5rem 1rem',
              borderRadius: 'var(--radius-sm)',
              border: 'none',
              backgroundColor: activeTab === 'history' ? '#ffffff' : 'transparent',
              fontWeight: activeTab === 'history' ? 700 : 500,
              color: activeTab === 'history' ? 'var(--color-primary)' : 'var(--color-text-muted)',
              boxShadow: activeTab === 'history' ? 'var(--shadow-sm)' : 'none',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.375rem',
            }}
          >
            <Receipt size={16} />
            <span>{t('sales_history')}</span>
          </button>
        </div>
      </div>

      {/* Global Error Alert Banner */}
      {errorBanner && (
        <div
          style={{
            backgroundColor: 'var(--color-danger-soft)',
            border: '1px solid var(--color-danger)',
            color: 'var(--color-danger)',
            padding: '0.875rem 1.25rem',
            borderRadius: 'var(--radius-md)',
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            fontSize: 'var(--font-size-sm)',
          }}
        >
          <AlertCircle size={20} />
          <span style={{ flex: 1, fontWeight: 600 }}>{errorBanner}</span>
          <button
            onClick={() => setErrorBanner(null)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-danger)', fontWeight: 700 }}
          >
            ✕
          </button>
        </div>
      )}

      {/* TAB 1: POS REGISTER VIEW */}
      {activeTab === 'pos' && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'minmax(320px, 1.3fr) minmax(320px, 1fr)',
            gap: '1.5rem',
            alignItems: 'start',
          }}
        >
          {/* LEFT COLUMN: PRODUCT CATALOG */}
          <div
            style={{
              backgroundColor: 'var(--color-bg-surface)',
              borderRadius: 'var(--radius-lg)',
              border: '1px solid var(--color-border)',
              padding: '1.25rem',
              boxShadow: 'var(--shadow-sm)',
              display: 'flex',
              flexDirection: 'column',
              gap: '1rem',
              minHeight: '600px',
            }}
          >
            {/* Search & Filter Bar */}
            <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
              <div style={{ position: 'relative', flex: 1 }}>
                <Search
                  size={18}
                  style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--color-text-subtle)' }}
                />
                <input
                  type="text"
                  placeholder={t('search_products')}
                  value={productSearch}
                  onChange={(e) => setProductSearch(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.625rem 0.75rem 0.625rem 2.25rem',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--color-border)',
                    fontSize: 'var(--font-size-sm)',
                    outline: 'none',
                    backgroundColor: 'var(--color-bg-app)',
                  }}
                />
              </div>
            </div>

            {/* Category Pills */}
            <div style={{ display: 'flex', gap: '0.5rem', overflowX: 'auto', paddingBottom: '0.25rem' }}>
              <button
                onClick={() => setSelectedCategory(null)}
                style={{
                  padding: '0.375rem 0.875rem',
                  borderRadius: 'var(--radius-full)',
                  border: '1px solid var(--color-border)',
                  backgroundColor: selectedCategory === null ? 'var(--color-primary)' : 'var(--color-bg-subtle)',
                  color: selectedCategory === null ? '#ffffff' : 'var(--color-text-main)',
                  fontSize: 'var(--font-size-xs)',
                  fontWeight: 600,
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                }}
              >
                {t('filter_all')} ({products.length})
              </button>
              {categories.map((cat) => (
                <button
                  key={cat.id}
                  onClick={() => setSelectedCategory(cat.id)}
                  style={{
                    padding: '0.375rem 0.875rem',
                    borderRadius: 'var(--radius-full)',
                    border: '1px solid var(--color-border)',
                    backgroundColor: selectedCategory === cat.id ? 'var(--color-primary)' : 'var(--color-bg-subtle)',
                    color: selectedCategory === cat.id ? '#ffffff' : 'var(--color-text-main)',
                    fontSize: 'var(--font-size-xs)',
                    fontWeight: 600,
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {cat.name}
                </button>
              ))}
            </div>

            {/* Product Cards Grid */}
            {isLoadingProducts ? (
              <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}>
                <LoadingSpinner label="Loading products..." />
              </div>
            ) : filteredProducts.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--color-text-muted)' }}>
                {t('no_products_found')}
              </div>
            ) : (
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))',
                  gap: '0.75rem',
                  maxHeight: '620px',
                  overflowY: 'auto',
                  paddingRight: '0.25rem',
                }}
              >
                {filteredProducts.map((p) => {
                  const stockNum = parseFloat(p.current_stock) || 0;
                  const isOutOfStock = stockNum <= 0;
                  const isLowStock = !isOutOfStock && p.low_stock_threshold > 0 && stockNum <= p.low_stock_threshold;

                  return (
                    <div
                      key={p.id}
                      onClick={() => !isOutOfStock && addToCart(p)}
                      style={{
                        padding: '0.875rem',
                        borderRadius: 'var(--radius-md)',
                        border: '1px solid var(--color-border)',
                        backgroundColor: isOutOfStock ? '#f8fafc' : '#ffffff',
                        opacity: isOutOfStock ? 0.6 : 1,
                        cursor: isOutOfStock ? 'not-allowed' : 'pointer',
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'space-between',
                        gap: '0.5rem',
                        boxShadow: 'var(--shadow-sm)',
                        transition: 'transform 0.1s ease, border-color 0.1s ease',
                      }}
                      onMouseEnter={(e) => !isOutOfStock && (e.currentTarget.style.borderColor = 'var(--color-primary-light)')}
                      onMouseLeave={(e) => !isOutOfStock && (e.currentTarget.style.borderColor = 'var(--color-border)')}
                    >
                      <div>
                        <div style={{ fontWeight: 700, fontSize: 'var(--font-size-sm)', color: 'var(--color-text-main)', lineHeight: 1.2 }}>
                          {p.name}
                        </div>
                        {p.tamil_name && (
                          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-subtle)', marginTop: '0.125rem' }}>
                            {p.tamil_name}
                          </div>
                        )}
                      </div>

                      <div>
                        <div style={{ fontSize: 'var(--font-size-base)', fontWeight: 800, color: 'var(--color-primary)' }}>
                          {formatCurrency(p.selling_price)}
                          <span style={{ fontSize: '0.7rem', fontWeight: 500, color: 'var(--color-text-muted)' }}>
                            /{p.unit}
                          </span>
                        </div>

                        {/* Stock Status Badge */}
                        <div
                          style={{
                            marginTop: '0.25rem',
                            fontSize: '0.7rem',
                            fontWeight: 700,
                            color: isOutOfStock ? 'var(--color-danger)' : isLowStock ? 'var(--color-warning)' : 'var(--color-accent)',
                          }}
                        >
                          {isOutOfStock ? t('status_out_of_stock') : `${stockNum} ${p.unit}`}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* RIGHT COLUMN: POS CART & CHECKOUT PANEL */}
          <div
            style={{
              backgroundColor: 'var(--color-bg-surface)',
              borderRadius: 'var(--radius-lg)',
              border: '1px solid var(--color-border)',
              padding: '1.25rem',
              boxShadow: 'var(--shadow-md)',
              display: 'flex',
              flexDirection: 'column',
              gap: '1rem',
            }}
          >
            {/* Cart Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--color-border)', paddingBottom: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <ShoppingCart size={20} color="var(--color-primary)" />
                <h2 style={{ margin: 0, fontSize: 'var(--font-size-lg)', fontWeight: 800 }}>
                  {t('pos_cart')} ({cart.length})
                </h2>
              </div>
              {cart.length > 0 && (
                <button
                  onClick={clearCart}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--color-danger)',
                    fontSize: 'var(--font-size-xs)',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  Clear Cart
                </button>
              )}
            </div>

            {/* Customer Selector */}
            <div style={{ backgroundColor: 'var(--color-bg-subtle)', padding: '0.75rem', borderRadius: 'var(--radius-md)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.375rem' }}>
                <label style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, color: 'var(--color-text-muted)' }}>
                  {t('billed_to')}
                </label>
                <button
                  onClick={() => setShowQuickCustomerModal(true)}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--color-primary)',
                    fontSize: 'var(--font-size-xs)',
                    fontWeight: 700,
                    cursor: 'pointer',
                  }}
                >
                  + {t('add_customer')}
                </button>
              </div>

              <select
                value={selectedCustomerId}
                onChange={(e) => setSelectedCustomerId(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--color-border)',
                  fontSize: 'var(--font-size-sm)',
                  backgroundColor: '#ffffff',
                }}
              >
                <option value="">{t('walk_in_customer')}</option>
                {customers.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.phone}) {parseFloat(c.current_balance) > 0 ? `• Debt: ₹${c.current_balance}` : ''}
                  </option>
                ))}
              </select>

              {selectedCustomer && (
                <div style={{ marginTop: '0.375rem', fontSize: 'var(--font-size-xs)', display: 'flex', justifyContent: 'space-between' }}>
                  <span>Credit Limit: {formatCurrency(selectedCustomer.credit_limit)}</span>
                  <span style={{ fontWeight: 700, color: parseFloat(selectedCustomer.current_balance) > 0 ? 'var(--color-warning)' : 'var(--color-text-muted)' }}>
                    Khata Balance: {formatCurrency(selectedCustomer.current_balance)}
                  </span>
                </div>
              )}
            </div>

            {/* Cart Items List */}
            {cart.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '2.5rem 1rem', color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>
                {t('cart_empty')}
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '280px', overflowY: 'auto' }}>
                {cart.map((item) => {
                  const lineTotal = Math.max(
                    0,
                    parseFloat(item.product.selling_price) * parseFloat(item.quantity) - (parseFloat(item.discount_amount) || 0)
                  );

                  return (
                    <div
                      key={item.product.id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '0.625rem',
                        backgroundColor: '#ffffff',
                        border: '1px solid var(--color-border)',
                        borderRadius: 'var(--radius-md)',
                        fontSize: 'var(--font-size-sm)',
                      }}
                    >
                      <div style={{ flex: 1, minWidth: 0, paddingRight: '0.5rem' }}>
                        <div style={{ fontWeight: 700, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {item.product.name}
                        </div>
                        <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                          {formatCurrency(item.product.selling_price)} / {item.product.unit}
                        </div>
                      </div>

                      {/* Quantity Stepper */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                        <button
                          onClick={() => updateQuantity(item.product.id, -1)}
                          style={{
                            width: '28px',
                            height: '28px',
                            borderRadius: 'var(--radius-sm)',
                            border: '1px solid var(--color-border)',
                            backgroundColor: 'var(--color-bg-subtle)',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                          }}
                        >
                          <Minus size={14} />
                        </button>
                        <input
                          type="number"
                          step="any"
                          value={item.quantity}
                          onChange={(e) => {
                            const val = e.target.value;
                            const newCart = [...cart];
                            const idx = newCart.findIndex((x) => x.product.id === item.product.id);
                            if (idx > -1) {
                              newCart[idx].quantity = val;
                              setCart(newCart);
                            }
                          }}
                          style={{
                            width: '50px',
                            textAlign: 'center',
                            padding: '0.25rem',
                            border: '1px solid var(--color-border)',
                            borderRadius: 'var(--radius-sm)',
                            fontSize: 'var(--font-size-sm)',
                            fontWeight: 700,
                          }}
                        />
                        <button
                          onClick={() => updateQuantity(item.product.id, 1)}
                          style={{
                            width: '28px',
                            height: '28px',
                            borderRadius: 'var(--radius-sm)',
                            border: '1px solid var(--color-border)',
                            backgroundColor: 'var(--color-bg-subtle)',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                          }}
                        >
                          <Plus size={14} />
                        </button>
                      </div>

                      {/* Line Total */}
                      <div style={{ width: '85px', textAlign: 'right', fontWeight: 800, color: 'var(--color-text-main)' }}>
                        {formatCurrency(lineTotal)}
                      </div>

                      {/* Delete */}
                      <button
                        onClick={() => removeFromCart(item.product.id)}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: 'var(--color-text-subtle)',
                          cursor: 'pointer',
                          marginLeft: '0.25rem',
                        }}
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Cart Calculations Summary */}
            <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>
                <span>{t('subtotal')}</span>
                <span>{formatCurrency(cartSubtotal)}</span>
              </div>

              {/* Cart Overall Discount */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 'var(--font-size-sm)' }}>
                <span style={{ color: 'var(--color-text-muted)' }}>{t('discount')}</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                  <span style={{ color: 'var(--color-text-muted)' }}>-₹</span>
                  <input
                    type="number"
                    min="0"
                    step="any"
                    value={cartDiscount}
                    onChange={(e) => setCartDiscount(e.target.value)}
                    style={{
                      width: '70px',
                      padding: '0.25rem',
                      textAlign: 'right',
                      border: '1px solid var(--color-border)',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: 'var(--font-size-sm)',
                    }}
                  />
                </div>
              </div>

              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  fontSize: 'var(--font-size-xl)',
                  fontWeight: 900,
                  color: 'var(--color-primary)',
                  borderTop: '2px dashed var(--color-border)',
                  paddingTop: '0.5rem',
                }}
              >
                <span>{t('total')}</span>
                <span>{formatCurrency(cartTotal)}</span>
              </div>
            </div>

            {/* Payment Method Selector */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, color: 'var(--color-text-muted)' }}>
                {t('payment_method')}
              </label>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '0.375rem' }}>
                {[
                  { id: 'cash', label: t('pay_cash'), icon: Banknote },
                  { id: 'upi', label: t('pay_upi'), icon: Smartphone },
                  { id: 'card', label: t('pay_card'), icon: CreditCard },
                  { id: 'credit', label: t('pay_credit'), icon: User },
                  { id: 'split', label: t('pay_split'), icon: Layers },
                ].map((pm) => {
                  const Icon = pm.icon;
                  const isSelected = paymentMethod === pm.id;
                  return (
                    <button
                      key={pm.id}
                      onClick={() => setPaymentMethod(pm.id)}
                      style={{
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '0.25rem',
                        padding: '0.5rem 0.25rem',
                        borderRadius: 'var(--radius-md)',
                        border: isSelected ? '2px solid var(--color-primary)' : '1px solid var(--color-border)',
                        backgroundColor: isSelected ? 'var(--color-primary-soft)' : '#ffffff',
                        color: isSelected ? 'var(--color-primary)' : 'var(--color-text-main)',
                        fontWeight: isSelected ? 700 : 500,
                        fontSize: '0.7rem',
                        cursor: 'pointer',
                        transition: 'all 0.1s ease',
                      }}
                    >
                      <Icon size={16} />
                      <span>{pm.label}</span>
                    </button>
                  );
                })}
              </div>

              {/* Split Payment Breakdown Inputs */}
              {paymentMethod === 'split' && (
                <div style={{ backgroundColor: 'var(--color-bg-subtle)', padding: '0.75rem', borderRadius: 'var(--radius-md)', display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.5rem', marginTop: '0.25rem' }}>
                  <div>
                    <label style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>Cash (₹)</label>
                    <input
                      type="number"
                      placeholder="0.00"
                      value={splitCash}
                      onChange={(e) => setSplitCash(e.target.value)}
                      style={{ width: '100%', padding: '0.375rem', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-sm)' }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>UPI (₹)</label>
                    <input
                      type="number"
                      placeholder="0.00"
                      value={splitUpi}
                      onChange={(e) => setSplitUpi(e.target.value)}
                      style={{ width: '100%', padding: '0.375rem', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-sm)' }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>Card (₹)</label>
                    <input
                      type="number"
                      placeholder="0.00"
                      value={splitCard}
                      onChange={(e) => setSplitCard(e.target.value)}
                      style={{ width: '100%', padding: '0.375rem', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-sm)' }}
                    />
                  </div>
                </div>
              )}
            </div>

              {/* Order Notes / Remarks */}
              <input
                type="text"
                placeholder="Order Notes / Bill Remarks (Optional)"
                value={saleNotes}
                onChange={(e) => setSaleNotes(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.45rem 0.65rem',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--color-border)',
                  fontSize: 'var(--font-size-xs)',
                  marginTop: '0.25rem',
                  backgroundColor: '#ffffff',
                }}
              />

              {/* Complete Checkout Button */}
              <Button
                variant="primary"
                size="large"
                onClick={handleCheckout}
                disabled={cart.length === 0 || isSubmitting}
                style={{
                  width: '100%',
                  padding: '0.875rem',
                  fontSize: 'var(--font-size-base)',
                  fontWeight: 800,
                  marginTop: '0.5rem',
                }}
              >
                {isSubmitting ? t('processing_checkout') : `${t('checkout_btn')} (${formatCurrency(cartTotal)})`}
              </Button>
            </div>
          </div>
      )}

      {/* TAB 2: RECENT SALES INVOICES */}
      {activeTab === 'history' && (
        <div
          style={{
            backgroundColor: 'var(--color-bg-surface)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--color-border)',
            padding: '1.25rem',
            boxShadow: 'var(--shadow-sm)',
          }}
        >
          <div style={{ marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ margin: 0, fontSize: 'var(--font-size-lg)', fontWeight: 800 }}>
              {t('sales_history')}
            </h3>
            <Button variant="secondary" size="small" onClick={loadSalesHistory}>
              Refresh
            </Button>
          </div>

          {isLoadingHistory ? (
            <div style={{ padding: '3rem', display: 'flex', justifyContent: 'center' }}>
              <LoadingSpinner label="Loading sales history..." />
            </div>
          ) : salesHistory.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--color-text-muted)' }}>
              No completed sales records yet.
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--font-size-sm)' }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid var(--color-border)', textAlign: 'left', color: 'var(--color-text-muted)' }}>
                    <th style={{ padding: '0.75rem 0.5rem' }}>{t('invoice_number')}</th>
                    <th style={{ padding: '0.75rem 0.5rem' }}>{t('bill_date')}</th>
                    <th style={{ padding: '0.75rem 0.5rem' }}>{t('billed_to')}</th>
                    <th style={{ padding: '0.75rem 0.5rem' }}>Payment Mode</th>
                    <th style={{ padding: '0.75rem 0.5rem', textAlign: 'right' }}>{t('total')}</th>
                    <th style={{ padding: '0.75rem 0.5rem', textAlign: 'center' }}>Status</th>
                    <th style={{ padding: '0.75rem 0.5rem', textAlign: 'right' }}>{t('actions')}</th>
                  </tr>
                </thead>
                <tbody>
                  {salesHistory.map((s) => (
                    <tr key={s.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                      <td style={{ padding: '0.75rem 0.5rem', fontWeight: 700, color: 'var(--color-primary)' }}>
                        {s.invoice_number}
                      </td>
                      <td style={{ padding: '0.75rem 0.5rem', color: 'var(--color-text-muted)' }}>
                        {new Date(s.created_at).toLocaleDateString()} {new Date(s.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </td>
                      <td style={{ padding: '0.75rem 0.5rem' }}>
                        {s.customer_name || <span style={{ color: 'var(--color-text-subtle)' }}>Walk-in</span>}
                      </td>
                      <td style={{ padding: '0.75rem 0.5rem', textTransform: 'uppercase', fontSize: 'var(--font-size-xs)', fontWeight: 600 }}>
                        {s.payment_method}
                      </td>
                      <td style={{ padding: '0.75rem 0.5rem', textAlign: 'right', fontWeight: 700 }}>
                        {formatCurrency(s.total_amount)}
                      </td>
                      <td style={{ padding: '0.75rem 0.5rem', textAlign: 'center' }}>
                        <span
                          style={{
                            padding: '0.25rem 0.5rem',
                            borderRadius: 'var(--radius-full)',
                            fontSize: '0.7rem',
                            fontWeight: 700,
                            backgroundColor: s.payment_status === 'paid' ? 'var(--color-accent-soft)' : 'var(--color-danger-soft)',
                            color: s.payment_status === 'paid' ? 'var(--color-accent)' : 'var(--color-danger)',
                            textTransform: 'uppercase',
                          }}
                        >
                          {s.payment_status}
                        </span>
                      </td>
                      <td style={{ padding: '0.75rem 0.5rem', textAlign: 'right' }}>
                        <Button
                          variant="secondary"
                          size="small"
                          onClick={() => setCompletedSale(s)}
                          icon={Receipt}
                        >
                          {t('view_receipt')}
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* QUICK CUSTOMER CREATION MODAL */}
      {showQuickCustomerModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(15, 23, 42, 0.6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1100,
            padding: '1rem',
          }}
        >
          <div
            style={{
              backgroundColor: '#ffffff',
              borderRadius: 'var(--radius-lg)',
              padding: '1.5rem',
              width: '100%',
              maxWidth: '400px',
              boxShadow: 'var(--shadow-lg)',
            }}
          >
            <h3 style={{ margin: '0 0 1rem', fontSize: 'var(--font-size-lg)', fontWeight: 800 }}>
              {t('add_customer')}
            </h3>

            <form onSubmit={handleCreateQuickCustomer} style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
              <div>
                <label style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700 }}>{t('customer_name')} *</label>
                <Input
                  value={quickCustomerForm.name}
                  onChange={(e) => setQuickCustomerForm({ ...quickCustomerForm, name: e.target.value })}
                  placeholder="e.g. Senthil Kumar"
                  required
                />
              </div>

              <div>
                <label style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700 }}>{t('customer_phone')} *</label>
                <Input
                  value={quickCustomerForm.phone}
                  onChange={(e) => setQuickCustomerForm({ ...quickCustomerForm, phone: e.target.value })}
                  placeholder="10-digit mobile number"
                  required
                />
              </div>

              <div>
                <label style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700 }}>{t('credit_limit')} (₹)</label>
                <Input
                  type="number"
                  value={quickCustomerForm.credit_limit}
                  onChange={(e) => setQuickCustomerForm({ ...quickCustomerForm, credit_limit: e.target.value })}
                  placeholder="0.00"
                />
              </div>

              <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
                <Button variant="secondary" type="button" onClick={() => setShowQuickCustomerModal(false)}>
                  Cancel
                </Button>
                <Button variant="primary" type="submit">
                  Save Customer
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* COMPLETED SALE PRINTABLE RECEIPT MODAL */}
      {completedSale && (
        <ReceiptModal
          sale={completedSale}
          onClose={() => setCompletedSale(null)}
        />
      )}

      {/* Toast Notification */}
      {toastMessage && (
        <Toast
          message={toastMessage}
          onClose={() => setToastMessage(null)}
        />
      )}
    </div>
  );
}
