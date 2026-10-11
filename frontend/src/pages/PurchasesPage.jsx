import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useI18n } from '../context/I18nContext';
import { api } from '../services/api';
import {
  Search,
  Plus,
  Trash2,
  FileText,
  Banknote,
  QrCode,
  CreditCard,
  Building,
  AlertCircle,
  ShoppingBag,
  Clock
} from 'lucide-react';
import { Button } from '../components/common/Button';
import { LoadingSpinner, Toast } from '../components/common/Feedback';
import { PurchaseBillModal } from '../components/purchases/PurchaseBillModal';
import { SupplierModal } from '../components/suppliers/SupplierModal';

export function PurchasesPage() {
  const { t, formatCurrency } = useI18n();

  // Active Tab: 'entry' or 'history'
  const [activeTab, setActiveTab] = useState('entry');

  // Suppliers & Products Catalog
  const [suppliers, setSuppliers] = useState([]);
  const [products, setProducts] = useState([]);
  const [_isLoadingCatalogs, setIsLoadingCatalogs] = useState(true);

  // New Purchase Form State
  const [selectedSupplierId, setSelectedSupplierId] = useState('');
  const [supplierInvoiceRef, setSupplierInvoiceRef] = useState('');
  const [purchaseItems, setPurchaseItems] = useState([]);
  const [overallDiscount, setOverallDiscount] = useState('0');
  const [paymentMethod, setPaymentMethod] = useState('cash');
  const [paidAmount, setPaidAmount] = useState('');
  const [splitPayments, setSplitPayments] = useState([
    { mode: 'cash', amount: '' },
    { mode: 'upi', amount: '' },
  ]);
  const [notes, setNotes] = useState('');

  // Product Picker state
  const [productSearch, setProductSearch] = useState('');

  // History State
  const [purchases, setPurchases] = useState([]);
  const [historySearch, setHistorySearch] = useState('');
  const [historyStatus, setHistoryStatus] = useState('');
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  // Modals & Feedback
  const [viewingPurchase, setViewingPurchase] = useState(null);
  const [showSupplierModal, setShowSupplierModal] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);

  // Load Catalogs
  const loadCatalogs = useCallback(async () => {
    try {
      setIsLoadingCatalogs(true);
      const [supRes, prodRes] = await Promise.all([
        api.getSuppliers({ limit: 100 }),
        api.getProducts({ is_active: true, limit: 100 }),
      ]);
      setSuppliers(supRes.data || []);
      setProducts(prodRes.data || []);
    } catch (err) {
      console.error('Failed to load catalogs:', err);
    } finally {
      setIsLoadingCatalogs(false);
    }
  }, []);

  // Load Purchases History
  const loadPurchases = useCallback(async () => {
    try {
      setIsLoadingHistory(true);
      const res = await api.getPurchases({
        search: historySearch.trim() || undefined,
        payment_status: historyStatus || undefined,
        limit: 50,
      });
      setPurchases(res.data || []);
    } catch (err) {
      console.error('Failed to load purchases:', err);
    } finally {
      setIsLoadingHistory(false);
    }
  }, [historySearch, historyStatus]);

  useEffect(() => {
    loadCatalogs();
  }, [loadCatalogs]);

  useEffect(() => {
    if (activeTab === 'history') {
      loadPurchases();
    }
  }, [activeTab, loadPurchases]);

  // Cart Calculations
  const cartSummary = useMemo(() => {
    let subtotal = 0;
    purchaseItems.forEach((item) => {
      const q = parseFloat(item.quantity) || 0;
      const c = parseFloat(item.unit_cost) || 0;
      const d = parseFloat(item.discount_amount) || 0;
      const lineNet = Math.max(0, q * c - d);
      subtotal += lineNet;
    });

    const disc = parseFloat(overallDiscount) || 0;
    const finalTotal = Math.max(0, subtotal - disc);

    let calculatedPaid = finalTotal;
    if (paymentMethod === 'credit') {
      calculatedPaid = parseFloat(paidAmount) || 0;
    } else if (paymentMethod === 'split') {
      calculatedPaid = splitPayments.reduce((acc, p) => acc + (parseFloat(p.amount) || 0), 0);
    } else {
      calculatedPaid = paidAmount === '' ? finalTotal : (parseFloat(paidAmount) || 0);
    }

    const remainingPayable = Math.max(0, finalTotal - calculatedPaid);

    return {
      subtotal,
      finalTotal,
      paidAmount: calculatedPaid,
      remainingPayable,
    };
  }, [purchaseItems, overallDiscount, paymentMethod, paidAmount, splitPayments]);

  // Add Item to Purchase Cart
  const handleAddProduct = (prod) => {
    const existingIdx = purchaseItems.findIndex((it) => it.product_id === prod.id);
    if (existingIdx >= 0) {
      const updated = [...purchaseItems];
      updated[existingIdx].quantity = (parseFloat(updated[existingIdx].quantity || '0') + 1).toString();
      setPurchaseItems(updated);
    } else {
      setPurchaseItems([
        ...purchaseItems,
        {
          product_id: prod.id,
          product_name: prod.name,
          unit: prod.unit || 'piece',
          quantity: '1',
          unit_cost: parseFloat(prod.purchase_cost || '0') > 0 ? prod.purchase_cost.toString() : '0',
          discount_amount: '0',
        },
      ]);
    }
  };

  const handleUpdateItem = (idx, field, val) => {
    const updated = [...purchaseItems];
    updated[idx][field] = val;
    setPurchaseItems(updated);
  };

  const handleRemoveItem = (idx) => {
    setPurchaseItems(purchaseItems.filter((_, i) => i !== idx));
  };

  // Submit Purchase
  const handleSubmitPurchase = async (e) => {
    e.preventDefault();
    setErrorMessage(null);

    if (purchaseItems.length === 0) {
      setErrorMessage('Please add at least one product to the purchase.');
      return;
    }

    for (const it of purchaseItems) {
      const q = parseFloat(it.quantity);
      const c = parseFloat(it.unit_cost);
      if (isNaN(q) || q <= 0) {
        setErrorMessage(`Invalid quantity for ${it.product_name}. Must be greater than zero.`);
        return;
      }
      if (isNaN(c) || c < 0) {
        setErrorMessage(`Invalid unit cost for ${it.product_name}.`);
        return;
      }
    }

    if (cartSummary.remainingPayable > 0 && !selectedSupplierId) {
      setErrorMessage('A supplier must be selected when purchase leaves an outstanding payable balance.');
      return;
    }

    try {
      setIsSubmitting(true);
      const payload = {
        supplier_id: selectedSupplierId || undefined,
        supplier_invoice_ref: supplierInvoiceRef.trim() || undefined,
        items: purchaseItems.map((it) => ({
          product_id: it.product_id,
          quantity: parseFloat(it.quantity),
          unit_cost: parseFloat(it.unit_cost),
          discount_amount: parseFloat(it.discount_amount) || 0,
        })),
        discount_amount: parseFloat(overallDiscount) || 0,
        payment_method: paymentMethod,
        paid_amount: cartSummary.paidAmount,
        split_payments: paymentMethod === 'split' ? splitPayments.filter((p) => parseFloat(p.amount) > 0).map((p) => ({ mode: p.mode, amount: parseFloat(p.amount) })) : undefined,
        notes: notes.trim() || undefined,
      };

      const res = await api.createPurchase(payload);
      setToastMessage(t('purchase_success'));
      setViewingPurchase(res.data);

      // Reset Form
      setPurchaseItems([]);
      setOverallDiscount('0');
      setPaidAmount('');
      setSupplierInvoiceRef('');
      setNotes('');
      loadCatalogs();
    } catch (err) {
      setErrorMessage(err.message || 'Failed to record purchase.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Filtered Products for Catalog Search
  const filteredProducts = useMemo(() => {
    if (!productSearch.trim()) return products.slice(0, 8);
    const s = productSearch.toLowerCase();
    return products.filter((p) => p.name.toLowerCase().includes(s) || (p.sku && p.sku.toLowerCase().includes(s)));
  }, [products, productSearch]);

  const selectedSupplierObj = useMemo(() => {
    return suppliers.find((s) => s.id === selectedSupplierId);
  }, [suppliers, selectedSupplierId]);

  return (
    <div className="purchases-page" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '1rem' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 'var(--font-size-2xl)', fontWeight: 800, color: 'var(--color-primary)' }}>
            {t('purchases_title')}
          </h1>
          <p style={{ margin: 0, fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>
            {t('purchases_subtitle')}
          </p>
        </div>

        {/* Tab Buttons */}
        <div style={{ display: 'flex', gap: '0.5rem', backgroundColor: 'var(--color-bg-subtle)', padding: '0.25rem', borderRadius: 'var(--radius-lg)' }}>
          <button
            type="button"
            onClick={() => setActiveTab('entry')}
            style={{
              padding: '0.5rem 1rem',
              borderRadius: 'var(--radius-md)',
              border: 'none',
              fontWeight: 700,
              fontSize: 'var(--font-size-sm)',
              cursor: 'pointer',
              backgroundColor: activeTab === 'entry' ? '#ffffff' : 'transparent',
              color: activeTab === 'entry' ? 'var(--color-primary)' : 'var(--color-text-muted)',
              boxShadow: activeTab === 'entry' ? 'var(--shadow-sm)' : 'none',
            }}
          >
            {t('new_purchase_btn')}
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('history')}
            style={{
              padding: '0.5rem 1rem',
              borderRadius: 'var(--radius-md)',
              border: 'none',
              fontWeight: 700,
              fontSize: 'var(--font-size-sm)',
              cursor: 'pointer',
              backgroundColor: activeTab === 'history' ? '#ffffff' : 'transparent',
              color: activeTab === 'history' ? 'var(--color-primary)' : 'var(--color-text-muted)',
              boxShadow: activeTab === 'history' ? 'var(--shadow-sm)' : 'none',
            }}
          >
            {t('purchase_history')}
          </button>
        </div>
      </div>

      {errorMessage && (
        <div style={{ backgroundColor: 'var(--color-danger-soft)', border: '1px solid var(--color-danger)', color: 'var(--color-danger)', padding: '0.75rem 1rem', borderRadius: 'var(--radius-md)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <AlertCircle size={18} />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* TAB 1: NEW PURCHASE ENTRY */}
      {activeTab === 'entry' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.8fr) minmax(320px, 1.2fr)', gap: '1.25rem' }}>
          {/* Left Column: Product Selection & Cart */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            {/* Supplier & Ref Section */}
            <div
              style={{
                backgroundColor: 'var(--color-bg-surface)',
                padding: '1.25rem',
                borderRadius: 'var(--radius-lg)',
                border: '1px solid var(--color-border)',
                boxShadow: 'var(--shadow-sm)',
                display: 'grid',
                gridTemplateColumns: '1.5fr 1fr',
                gap: '1rem',
                alignItems: 'center',
              }}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.375rem' }}>
                  <label style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, color: 'var(--color-text-main)' }}>
                    {t('select_supplier')}
                  </label>
                  <button
                    type="button"
                    onClick={() => setShowSupplierModal(true)}
                    style={{ background: 'none', border: 'none', color: 'var(--color-primary)', fontSize: '0.75rem', fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.25rem' }}
                  >
                    <Plus size={14} /> {t('add_supplier')}
                  </button>
                </div>
                <select
                  value={selectedSupplierId}
                  onChange={(e) => setSelectedSupplierId(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.625rem',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--color-border)',
                    fontSize: 'var(--font-size-sm)',
                    backgroundColor: '#ffffff',
                  }}
                >
                  <option value="">— Cash / Walk-in Supplier —</option>
                  {suppliers.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} {parseFloat(s.current_balance) > 0 ? `(Dues: ${formatCurrency(s.current_balance)})` : ''}
                    </option>
                  ))}
                </select>
                {selectedSupplierObj && parseFloat(selectedSupplierObj.current_balance) > 0 && (
                  <div style={{ fontSize: 'var(--font-size-xs)', color: '#b45309', fontWeight: 600, marginTop: '0.375rem' }}>
                    Current Payable Balance: {formatCurrency(selectedSupplierObj.current_balance)}
                  </div>
                )}
              </div>

              <div>
                <label style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, color: 'var(--color-text-main)', display: 'block', marginBottom: '0.375rem' }}>
                  {t('supplier_invoice_ref')}
                </label>
                <input
                  type="text"
                  placeholder="e.g. BILL-9901 / DC-442"
                  value={supplierInvoiceRef}
                  onChange={(e) => setSupplierInvoiceRef(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.625rem',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--color-border)',
                    fontSize: 'var(--font-size-sm)',
                    backgroundColor: '#ffffff',
                  }}
                />
              </div>
            </div>

            {/* Product Quick-Add Picker */}
            <div
              style={{
                backgroundColor: 'var(--color-bg-surface)',
                padding: '1.25rem',
                borderRadius: 'var(--radius-lg)',
                border: '1px solid var(--color-border)',
                boxShadow: 'var(--shadow-sm)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                <span style={{ fontSize: 'var(--font-size-sm)', fontWeight: 700, color: 'var(--color-text-main)' }}>
                  Add Products to Bill
                </span>
                <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                  Click to add product into receiving cart
                </span>
              </div>

              <div style={{ position: 'relative', marginBottom: '0.75rem' }}>
                <Search size={16} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--color-text-subtle)' }} />
                <input
                  type="text"
                  placeholder="Search products by name or SKU..."
                  value={productSearch}
                  onChange={(e) => setProductSearch(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.5rem 0.75rem 0.5rem 2.25rem',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--color-border)',
                    fontSize: 'var(--font-size-sm)',
                    backgroundColor: 'var(--color-bg-app)',
                  }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '0.625rem' }}>
                {filteredProducts.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => handleAddProduct(p)}
                    style={{
                      padding: '0.625rem 0.75rem',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--color-border)',
                      backgroundColor: '#ffffff',
                      textAlign: 'left',
                      cursor: 'pointer',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '0.25rem',
                    }}
                  >
                    <div style={{ fontWeight: 700, fontSize: 'var(--font-size-xs)', color: 'var(--color-text-main)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {p.name}
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>
                      <span>Cost: {formatCurrency(p.purchase_cost)}</span>
                      <span>Stock: {parseFloat(p.current_stock || '0').toFixed(0)}</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Cart Table */}
            <div
              style={{
                backgroundColor: 'var(--color-bg-surface)',
                padding: '1.25rem',
                borderRadius: 'var(--radius-lg)',
                border: '1px solid var(--color-border)',
                boxShadow: 'var(--shadow-sm)',
              }}
            >
              <h3 style={{ margin: '0 0 1rem', fontSize: 'var(--font-size-base)', fontWeight: 700 }}>
                Received Items ({purchaseItems.length})
              </h3>

              {purchaseItems.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--color-text-muted)' }}>
                  No items in purchase bill. Select products from above to receive inventory.
                </div>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--font-size-sm)' }}>
                    <thead>
                      <tr style={{ borderBottom: '2px solid var(--color-border)', textAlign: 'left', color: 'var(--color-text-muted)', fontSize: 'var(--font-size-xs)' }}>
                        <th style={{ padding: '0.5rem' }}>Product</th>
                        <th style={{ padding: '0.5rem', width: '90px' }}>Quantity</th>
                        <th style={{ padding: '0.5rem', width: '110px' }}>Unit Cost</th>
                        <th style={{ padding: '0.5rem', width: '90px' }}>Line Disc</th>
                        <th style={{ padding: '0.5rem', textAlign: 'right' }}>Total</th>
                        <th style={{ padding: '0.5rem', width: '40px' }}></th>
                      </tr>
                    </thead>
                    <tbody>
                      {purchaseItems.map((item, idx) => {
                        const q = parseFloat(item.quantity) || 0;
                        const c = parseFloat(item.unit_cost) || 0;
                        const d = parseFloat(item.discount_amount) || 0;
                        const lineNet = Math.max(0, q * c - d);

                        return (
                          <tr key={item.product_id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                            <td style={{ padding: '0.5rem' }}>
                              <div style={{ fontWeight: 700 }}>{item.product_name}</div>
                              <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>Unit: {item.unit}</div>
                            </td>
                            <td style={{ padding: '0.5rem' }}>
                              <input
                                type="number"
                                step="any"
                                min="0.0001"
                                value={item.quantity}
                                onChange={(e) => handleUpdateItem(idx, 'quantity', e.target.value)}
                                style={{ width: '100%', padding: '0.375rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border)' }}
                              />
                            </td>
                            <td style={{ padding: '0.5rem' }}>
                              <input
                                type="number"
                                step="any"
                                min="0"
                                value={item.unit_cost}
                                onChange={(e) => handleUpdateItem(idx, 'unit_cost', e.target.value)}
                                style={{ width: '100%', padding: '0.375rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border)' }}
                              />
                            </td>
                            <td style={{ padding: '0.5rem' }}>
                              <input
                                type="number"
                                step="any"
                                min="0"
                                value={item.discount_amount}
                                onChange={(e) => handleUpdateItem(idx, 'discount_amount', e.target.value)}
                                style={{ width: '100%', padding: '0.375rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border)' }}
                              />
                            </td>
                            <td style={{ padding: '0.5rem', textAlign: 'right', fontWeight: 700 }}>
                              {formatCurrency(lineNet)}
                            </td>
                            <td style={{ padding: '0.5rem', textAlign: 'center' }}>
                              <button
                                type="button"
                                onClick={() => handleRemoveItem(idx)}
                                style={{ background: 'none', border: 'none', color: 'var(--color-danger)', cursor: 'pointer', padding: '0.25rem' }}
                              >
                                <Trash2 size={16} />
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Checkout Summary & Payment */}
          <div
            style={{
              backgroundColor: 'var(--color-bg-surface)',
              padding: '1.5rem',
              borderRadius: 'var(--radius-lg)',
              border: '1px solid var(--color-border)',
              boxShadow: 'var(--shadow-sm)',
              display: 'flex',
              flexDirection: 'column',
              gap: '1.25rem',
              height: 'fit-content',
            }}
          >
            <h3 style={{ margin: 0, fontSize: 'var(--font-size-lg)', fontWeight: 800, color: 'var(--color-primary)' }}>
              Purchase Bill Summary
            </h3>

            {/* Calculations Box */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem', borderBottom: '1px solid var(--color-border)', paddingBottom: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>
                <span>Subtotal:</span>
                <span>{formatCurrency(cartSummary.subtotal)}</span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>Overall Bill Discount:</span>
                <input
                  type="number"
                  step="any"
                  min="0"
                  value={overallDiscount}
                  onChange={(e) => setOverallDiscount(e.target.value)}
                  style={{ width: '110px', padding: '0.375rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border)', textAlign: 'right', fontSize: 'var(--font-size-sm)' }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-size-xl)', fontWeight: 900, color: 'var(--color-primary)', borderTop: '2px dashed var(--color-border)', paddingTop: '0.75rem', marginTop: '0.25rem' }}>
                <span>{t('purchase_total')}:</span>
                <span>{formatCurrency(cartSummary.finalTotal)}</span>
              </div>
            </div>

            {/* Payment Method Selector */}
            <div>
              <label style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, color: 'var(--color-text-main)', display: 'block', marginBottom: '0.5rem' }}>
                {t('payment_method')}
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.5rem' }}>
                {[
                  { mode: 'cash', label: 'Cash', icon: Banknote },
                  { mode: 'upi', label: 'UPI', icon: QrCode },
                  { mode: 'bank_transfer', label: 'Bank', icon: Building },
                  { mode: 'card', label: 'Card', icon: CreditCard },
                  { mode: 'credit', label: 'Credit (AP)', icon: FileText },
                  { mode: 'split', label: 'Split', icon: ShoppingBag },
                ].map(({ mode, label, icon: Icon }) => (
                  <button
                    key={mode}
                    type="button"
                    onClick={() => setPaymentMethod(mode)}
                    style={{
                      padding: '0.5rem',
                      borderRadius: 'var(--radius-md)',
                      border: `1.5px solid ${paymentMethod === mode ? 'var(--color-primary)' : 'var(--color-border)'}`,
                      backgroundColor: paymentMethod === mode ? 'var(--color-primary-soft)' : '#ffffff',
                      color: paymentMethod === mode ? 'var(--color-primary)' : 'var(--color-text-muted)',
                      fontWeight: 700,
                      fontSize: '0.75rem',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '0.25rem',
                      cursor: 'pointer',
                    }}
                  >
                    <Icon size={14} />
                    <span>{label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Payment Inputs based on Mode */}
            {paymentMethod === 'credit' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <label style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700 }}>Immediate Down Payment (₹)</label>
                <input
                  type="number"
                  step="any"
                  min="0"
                  placeholder="0.00 (leave 0 for full credit)"
                  value={paidAmount}
                  onChange={(e) => setPaidAmount(e.target.value)}
                  style={{ padding: '0.5rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}
                />
              </div>
            )}

            {paymentMethod === 'split' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <input
                    type="number"
                    placeholder="Cash Amount"
                    value={splitPayments[0].amount}
                    onChange={(e) => setSplitPayments([{ mode: 'cash', amount: e.target.value }, splitPayments[1]])}
                    style={{ flex: 1, padding: '0.5rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border)', fontSize: 'var(--font-size-xs)' }}
                  />
                  <input
                    type="number"
                    placeholder="UPI Amount"
                    value={splitPayments[1].amount}
                    onChange={(e) => setSplitPayments([splitPayments[0], { mode: 'upi', amount: e.target.value }])}
                    style={{ flex: 1, padding: '0.5rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border)', fontSize: 'var(--font-size-xs)' }}
                  />
                </div>
              </div>
            )}

            {/* Payable / Dues Preview */}
            <div style={{ backgroundColor: 'var(--color-bg-subtle)', padding: '0.75rem 1rem', borderRadius: 'var(--radius-md)', display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-size-xs)' }}>
              <span>Remaining Payable (Dues):</span>
              <strong style={{ color: cartSummary.remainingPayable > 0 ? '#b45309' : 'var(--color-accent)' }}>
                {formatCurrency(cartSummary.remainingPayable)}
              </strong>
            </div>

            <textarea
              placeholder="Optional notes or remarks..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              style={{
                width: '100%',
                padding: '0.5rem 0.75rem',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-border)',
                fontSize: 'var(--font-size-xs)',
                fontFamily: 'inherit',
              }}
            />

            <Button
              variant="primary"
              size="large"
              onClick={handleSubmitPurchase}
              loading={isSubmitting}
              disabled={purchaseItems.length === 0}
            >
              {t('save_purchase_btn')}
            </Button>
          </div>
        </div>
      )}

      {/* TAB 2: PURCHASE HISTORY */}
      {activeTab === 'history' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {/* History Search & Filter */}
          <div
            style={{
              backgroundColor: 'var(--color-bg-surface)',
              padding: '1rem',
              borderRadius: 'var(--radius-lg)',
              border: '1px solid var(--color-border)',
              display: 'flex',
              flexWrap: 'wrap',
              gap: '1rem',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ display: 'flex', gap: '0.5rem', flex: 1, maxWidth: '440px' }}>
              <div style={{ position: 'relative', flex: 1 }}>
                <Search size={16} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--color-text-subtle)' }} />
                <input
                  type="text"
                  placeholder="Search invoice number, supplier or ref..."
                  value={historySearch}
                  onChange={(e) => setHistorySearch(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.5rem 0.75rem 0.5rem 2.25rem',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--color-border)',
                    fontSize: 'var(--font-size-sm)',
                    backgroundColor: 'var(--color-bg-app)',
                  }}
                />
              </div>
            </div>

            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <select
                value={historyStatus}
                onChange={(e) => setHistoryStatus(e.target.value)}
                style={{
                  padding: '0.5rem 0.75rem',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--color-border)',
                  fontSize: 'var(--font-size-sm)',
                  backgroundColor: '#ffffff',
                }}
              >
                <option value="">All Statuses</option>
                <option value="paid">Paid</option>
                <option value="partial">Partial</option>
                <option value="unpaid">Unpaid</option>
              </select>
            </div>
          </div>

          {/* History Table */}
          <div
            style={{
              backgroundColor: 'var(--color-bg-surface)',
              borderRadius: 'var(--radius-lg)',
              border: '1px solid var(--color-border)',
              padding: '1.25rem',
              boxShadow: 'var(--shadow-sm)',
            }}
          >
            {isLoadingHistory ? (
              <div style={{ padding: '3rem', display: 'flex', justifyContent: 'center' }}>
                <LoadingSpinner label="Loading purchase history..." />
              </div>
            ) : purchases.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--color-text-muted)' }}>
                No purchase records found.
              </div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--font-size-sm)' }}>
                  <thead>
                    <tr style={{ borderBottom: '2px solid var(--color-border)', textAlign: 'left', color: 'var(--color-text-muted)', fontSize: 'var(--font-size-xs)' }}>
                      <th style={{ padding: '0.75rem 0.5rem' }}>Invoice No</th>
                      <th style={{ padding: '0.75rem 0.5rem' }}>Date</th>
                      <th style={{ padding: '0.75rem 0.5rem' }}>Supplier</th>
                      <th style={{ padding: '0.75rem 0.5rem', textAlign: 'right' }}>Total</th>
                      <th style={{ padding: '0.75rem 0.5rem', textAlign: 'right' }}>Paid</th>
                      <th style={{ padding: '0.75rem 0.5rem', textAlign: 'right' }}>Payable Dues</th>
                      <th style={{ padding: '0.75rem 0.5rem', textAlign: 'center' }}>Status</th>
                      <th style={{ padding: '0.75rem 0.5rem', textAlign: 'right' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {purchases.map((p) => {
                      const isPaid = p.payment_status === 'paid';
                      return (
                        <tr key={p.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                          <td style={{ padding: '0.75rem 0.5rem' }}>
                            <div style={{ fontWeight: 700, color: 'var(--color-primary)' }}>{p.invoice_number}</div>
                            {p.supplier_invoice_ref && (
                              <div style={{ fontSize: '0.7rem', color: 'var(--color-text-subtle)' }}>Ref: {p.supplier_invoice_ref}</div>
                            )}
                          </td>
                          <td style={{ padding: '0.75rem 0.5rem', color: 'var(--color-text-muted)', fontSize: 'var(--font-size-xs)' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                              <Clock size={12} /> {new Date(p.purchase_date || p.created_at).toLocaleDateString()}
                            </div>
                          </td>
                          <td style={{ padding: '0.75rem 0.5rem' }}>
                            <div style={{ fontWeight: 600 }}>{p.supplier_name || 'Walk-in / Cash'}</div>
                          </td>
                          <td style={{ padding: '0.75rem 0.5rem', textAlign: 'right', fontWeight: 800 }}>
                            {formatCurrency(p.total_amount)}
                          </td>
                          <td style={{ padding: '0.75rem 0.5rem', textAlign: 'right', color: 'var(--color-accent)' }}>
                            {formatCurrency(p.paid_amount)}
                          </td>
                          <td style={{ padding: '0.75rem 0.5rem', textAlign: 'right', color: parseFloat(p.credit_amount) > 0 ? '#b45309' : 'var(--color-text-muted)', fontWeight: 700 }}>
                            {formatCurrency(p.credit_amount)}
                          </td>
                          <td style={{ padding: '0.75rem 0.5rem', textAlign: 'center' }}>
                            <span
                              style={{
                                padding: '0.125rem 0.5rem',
                                borderRadius: 'var(--radius-full)',
                                fontWeight: 700,
                                fontSize: '0.7rem',
                                backgroundColor: isPaid ? 'var(--color-accent-soft)' : 'var(--color-warning-soft)',
                                color: isPaid ? 'var(--color-accent)' : '#b45309',
                                textTransform: 'uppercase',
                              }}
                            >
                              {p.payment_status}
                            </span>
                          </td>
                          <td style={{ padding: '0.75rem 0.5rem', textAlign: 'right' }}>
                            <Button
                              variant="secondary"
                              size="small"
                              icon={FileText}
                              onClick={() => setViewingPurchase(p)}
                            >
                              {t('view_bill')}
                            </Button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Modals */}
      <PurchaseBillModal
        purchase={viewingPurchase}
        onClose={() => setViewingPurchase(null)}
      />

      <SupplierModal
        isOpen={showSupplierModal}
        onClose={() => setShowSupplierModal(false)}
        onSave={async (data) => {
          const res = await api.createSupplier(data);
          setSuppliers([res.data, ...suppliers]);
          setSelectedSupplierId(res.data.id);
          setToastMessage('Supplier created!');
        }}
      />

      {toastMessage && (
        <Toast message={toastMessage} onClose={() => setToastMessage(null)} />
      )}
    </div>
  );
}
