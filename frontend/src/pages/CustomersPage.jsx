import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useI18n } from '../context/I18nContext';
import { api } from '../services/api';
import {
  Search,
  Plus,
  BookOpen,
  Phone,
  AlertCircle,
  ArrowDownLeft,
  ArrowUpRight,
  X
} from 'lucide-react';
import { Button } from '../components/common/Button';
import { Input } from '../components/common/Input';
import { LoadingSpinner, Toast } from '../components/common/Feedback';

export function CustomersPage() {
  const { t, formatCurrency } = useI18n();

  const [customers, setCustomers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [withBalanceOnly, setWithBalanceOnly] = useState(false);

  // Modals
  const [showAddModal, setShowAddModal] = useState(false);
  const [addForm, setAddForm] = useState({ name: '', phone: '', email: '', address: '', credit_limit: '0' });

  const [paymentCustomer, setPaymentCustomer] = useState(null);
  const [paymentForm, setPaymentForm] = useState({ amount: '', payment_mode: 'cash', notes: '' });

  const [ledgerCustomer, setLedgerCustomer] = useState(null);
  const [ledgerEntries, setLedgerEntries] = useState([]);
  const [isLoadingLedger, setIsLoadingLedger] = useState(false);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);

  const loadCustomers = useCallback(async () => {
    try {
      setIsLoading(true);
      const res = await api.getCustomers({
        search: search.trim() || undefined,
        with_balance_only: withBalanceOnly,
        limit: 100,
      });
      setCustomers(res.data || []);
    } catch (err) {
      console.error('Failed to load customers:', err);
    } finally {
      setIsLoading(false);
    }
  }, [search, withBalanceOnly]);

  useEffect(() => {
    loadCustomers();
  }, [loadCustomers]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    loadCustomers();
  };

  // Metrics Calculations
  const metrics = useMemo(() => {
    let totalReceivable = 0;
    let debtCustomersCount = 0;

    customers.forEach((c) => {
      const bal = parseFloat(c.current_balance) || 0;
      if (bal > 0) {
        totalReceivable += bal;
        debtCustomersCount += 1;
      }
    });

    return {
      totalCustomers: customers.length,
      totalReceivable,
      debtCustomersCount,
    };
  }, [customers]);

  // Create Customer Handler
  const handleCreateCustomer = async (e) => {
    e.preventDefault();
    setErrorMessage(null);
    try {
      setIsSubmitting(true);
      const res = await api.createCustomer(addForm);
      setCustomers([res.data, ...customers]);
      setShowAddModal(false);
      setAddForm({ name: '', phone: '', email: '', address: '', credit_limit: '0' });
      setToastMessage('Customer created successfully!');
    } catch (err) {
      setErrorMessage(err.message || 'Failed to create customer');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Record Payment Handler
  const handleRecordPayment = async (e) => {
    e.preventDefault();
    if (!paymentCustomer) return;
    setErrorMessage(null);

    const amt = parseFloat(paymentForm.amount) || 0;
    if (amt <= 0) {
      setErrorMessage('Payment amount must be greater than zero.');
      return;
    }

    try {
      setIsSubmitting(true);
      await api.recordCustomerPayment(paymentCustomer.id, {
        amount: amt.toFixed(4),
        payment_mode: paymentForm.payment_mode,
        notes: paymentForm.notes.trim() || undefined,
      });

      setToastMessage(t('payment_recorded_success'));
      setPaymentCustomer(null);
      setPaymentForm({ amount: '', payment_mode: 'cash', notes: '' });
      loadCustomers();
    } catch (err) {
      setErrorMessage(err.message || 'Failed to record payment');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Open Ledger Modal
  const openLedgerModal = async (customer) => {
    setLedgerCustomer(customer);
    try {
      setIsLoadingLedger(true);
      const res = await api.getCustomer(customer.id);
      setLedgerEntries(res.data.recent_entries || []);
    } catch (err) {
      console.error('Failed to load ledger:', err);
    } finally {
      setIsLoadingLedger(false);
    }
  };

  return (
    <div className="customers-page" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Page Header */}
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '1rem' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 'var(--font-size-2xl)', fontWeight: 800, color: 'var(--color-primary)' }}>
            {t('customers_title')}
          </h1>
          <p style={{ margin: 0, fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>
            {t('customers_subtitle')}
          </p>
        </div>

        <Button variant="primary" icon={Plus} onClick={() => setShowAddModal(true)}>
          {t('add_customer')}
        </Button>
      </div>

      {/* Metrics Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
        <div style={{ backgroundColor: 'var(--color-bg-surface)', padding: '1.25rem', borderRadius: 'var(--radius-lg)', border: '1px solid var(--color-border)', boxShadow: 'var(--shadow-sm)' }}>
          <div style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, color: 'var(--color-text-muted)' }}>
            Total Customers
          </div>
          <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 900, color: 'var(--color-primary)', marginTop: '0.25rem' }}>
            {metrics.totalCustomers}
          </div>
        </div>

        <div style={{ backgroundColor: 'var(--color-bg-surface)', padding: '1.25rem', borderRadius: 'var(--radius-lg)', border: '1px solid var(--color-border)', boxShadow: 'var(--shadow-sm)' }}>
          <div style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, color: 'var(--color-text-muted)' }}>
            {t('total_receivable')}
          </div>
          <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 900, color: 'var(--color-danger)', marginTop: '0.25rem' }}>
            {formatCurrency(metrics.totalReceivable)}
          </div>
        </div>

        <div style={{ backgroundColor: 'var(--color-bg-surface)', padding: '1.25rem', borderRadius: 'var(--radius-lg)', border: '1px solid var(--color-border)', boxShadow: 'var(--shadow-sm)' }}>
          <div style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, color: 'var(--color-text-muted)' }}>
            Customers with Outstanding Debt
          </div>
          <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 900, color: 'var(--color-warning)', marginTop: '0.25rem' }}>
            {metrics.debtCustomersCount}
          </div>
        </div>
      </div>

      {/* Search & Filter Bar */}
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
        <form onSubmit={handleSearchSubmit} style={{ display: 'flex', gap: '0.5rem', flex: 1, maxWidth: '400px' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <Search size={18} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--color-text-subtle)' }} />
            <input
              type="text"
              placeholder="Search by name, phone or email..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
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
          <Button variant="secondary" type="submit" size="small">
            Search
          </Button>
        </form>

        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: 'var(--font-size-sm)', cursor: 'pointer', fontWeight: 600 }}>
          <input
            type="checkbox"
            checked={withBalanceOnly}
            onChange={(e) => setWithBalanceOnly(e.target.checked)}
          />
          <span>Only show customers with outstanding debt</span>
        </label>
      </div>

      {/* Error Alert */}
      {errorMessage && (
        <div style={{ backgroundColor: 'var(--color-danger-soft)', border: '1px solid var(--color-danger)', color: 'var(--color-danger)', padding: '0.75rem 1rem', borderRadius: 'var(--radius-md)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <AlertCircle size={18} />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Customer List Table */}
      <div
        style={{
          backgroundColor: 'var(--color-bg-surface)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--color-border)',
          padding: '1.25rem',
          boxShadow: 'var(--shadow-sm)',
        }}
      >
        {isLoading ? (
          <div style={{ padding: '3rem', display: 'flex', justifyContent: 'center' }}>
            <LoadingSpinner label="Loading customer ledger..." />
          </div>
        ) : customers.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--color-text-muted)' }}>
            No customers found. Click "+ New Customer" to register your first customer.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--font-size-sm)' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid var(--color-border)', textAlign: 'left', color: 'var(--color-text-muted)' }}>
                  <th style={{ padding: '0.75rem 0.5rem' }}>{t('customer_name')}</th>
                  <th style={{ padding: '0.75rem 0.5rem' }}>{t('customer_phone')}</th>
                  <th style={{ padding: '0.75rem 0.5rem', textAlign: 'right' }}>{t('credit_limit')}</th>
                  <th style={{ padding: '0.75rem 0.5rem', textAlign: 'right' }}>{t('current_balance')}</th>
                  <th style={{ padding: '0.75rem 0.5rem', textAlign: 'right' }}>{t('actions')}</th>
                </tr>
              </thead>
              <tbody>
                {customers.map((c) => {
                  const bal = parseFloat(c.current_balance) || 0;
                  const hasDebt = bal > 0;

                  return (
                    <tr key={c.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                      <td style={{ padding: '0.75rem 0.5rem' }}>
                        <div style={{ fontWeight: 700, color: 'var(--color-text-main)' }}>{c.name}</div>
                        {c.email && <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-subtle)' }}>{c.email}</div>}
                      </td>
                      <td style={{ padding: '0.75rem 0.5rem', color: 'var(--color-text-muted)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                          <Phone size={14} />
                          <span>{c.phone}</span>
                        </div>
                      </td>
                      <td style={{ padding: '0.75rem 0.5rem', textAlign: 'right' }}>
                        {formatCurrency(c.credit_limit)}
                      </td>
                      <td style={{ padding: '0.75rem 0.5rem', textAlign: 'right' }}>
                        <span
                          style={{
                            fontWeight: 800,
                            color: hasDebt ? 'var(--color-danger)' : 'var(--color-accent)',
                            backgroundColor: hasDebt ? 'var(--color-danger-soft)' : 'transparent',
                            padding: hasDebt ? '0.25rem 0.5rem' : '0',
                            borderRadius: 'var(--radius-sm)',
                          }}
                        >
                          {formatCurrency(c.current_balance)}
                        </span>
                      </td>
                      <td style={{ padding: '0.75rem 0.5rem', textAlign: 'right' }}>
                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
                          <Button
                            variant="primary"
                            size="small"
                            onClick={() => {
                              setPaymentCustomer(c);
                              setPaymentForm({
                                amount: bal > 0 ? bal.toString() : '',
                                payment_mode: 'cash',
                                notes: '',
                              });
                            }}
                          >
                            {t('record_payment')}
                          </Button>
                          <Button
                            variant="secondary"
                            size="small"
                            icon={BookOpen}
                            onClick={() => openLedgerModal(c)}
                          >
                            Khata Ledger
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* MODAL 1: ADD CUSTOMER */}
      {showAddModal && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(15, 23, 42, 0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1100, padding: '1rem' }}>
          <div style={{ backgroundColor: '#ffffff', borderRadius: 'var(--radius-lg)', padding: '1.5rem', width: '100%', maxWidth: '440px', boxShadow: 'var(--shadow-lg)' }}>
            <h3 style={{ margin: '0 0 1rem', fontSize: 'var(--font-size-lg)', fontWeight: 800 }}>
              {t('add_customer')}
            </h3>

            <form onSubmit={handleCreateCustomer} style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
              <div>
                <label style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700 }}>{t('customer_name')} *</label>
                <Input
                  value={addForm.name}
                  onChange={(e) => setAddForm({ ...addForm, name: e.target.value })}
                  placeholder="e.g. Ramanathan"
                  required
                />
              </div>

              <div>
                <label style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700 }}>{t('customer_phone')} *</label>
                <Input
                  value={addForm.phone}
                  onChange={(e) => setAddForm({ ...addForm, phone: e.target.value })}
                  placeholder="10-digit mobile number"
                  required
                />
              </div>

              <div>
                <label style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700 }}>Email (Optional)</label>
                <Input
                  type="email"
                  value={addForm.email}
                  onChange={(e) => setAddForm({ ...addForm, email: e.target.value })}
                  placeholder="raman@example.com"
                />
              </div>

              <div>
                <label style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700 }}>Address (Optional)</label>
                <Input
                  value={addForm.address}
                  onChange={(e) => setAddForm({ ...addForm, address: e.target.value })}
                  placeholder="Shop or street address"
                />
              </div>

              <div>
                <label style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700 }}>{t('credit_limit')} (₹)</label>
                <Input
                  type="number"
                  value={addForm.credit_limit}
                  onChange={(e) => setAddForm({ ...addForm, credit_limit: e.target.value })}
                  placeholder="0.00"
                />
              </div>

              <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
                <Button variant="secondary" type="button" onClick={() => setShowAddModal(false)}>
                  Cancel
                </Button>
                <Button variant="primary" type="submit" disabled={isSubmitting}>
                  {isSubmitting ? 'Saving...' : 'Save Customer'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: RECORD KHATA PAYMENT */}
      {paymentCustomer && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(15, 23, 42, 0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1100, padding: '1rem' }}>
          <div style={{ backgroundColor: '#ffffff', borderRadius: 'var(--radius-lg)', padding: '1.5rem', width: '100%', maxWidth: '420px', boxShadow: 'var(--shadow-lg)' }}>
            <h3 style={{ margin: '0 0 0.5rem', fontSize: 'var(--font-size-lg)', fontWeight: 800 }}>
              {t('record_payment')}
            </h3>
            <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)', marginBottom: '1.25rem' }}>
              Customer: <strong>{paymentCustomer.name}</strong> • Outstanding Debt:{' '}
              <strong style={{ color: 'var(--color-danger)' }}>{formatCurrency(paymentCustomer.current_balance)}</strong>
            </div>

            <form onSubmit={handleRecordPayment} style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
                  <label style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700 }}>{t('payment_amount')} (₹) *</label>
                  {parseFloat(paymentCustomer.current_balance) > 0 && (
                    <button
                      type="button"
                      onClick={() => setPaymentForm({ ...paymentForm, amount: paymentCustomer.current_balance })}
                      style={{ background: 'none', border: 'none', color: 'var(--color-primary)', fontSize: '0.7rem', fontWeight: 700, cursor: 'pointer' }}
                    >
                      Pay Full Debt
                    </button>
                  )}
                </div>
                <Input
                  type="number"
                  step="any"
                  value={paymentForm.amount}
                  onChange={(e) => setPaymentForm({ ...paymentForm, amount: e.target.value })}
                  placeholder="Amount received"
                  required
                />
              </div>

              <div>
                <label style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700 }}>{t('payment_method')}</label>
                <select
                  value={paymentForm.payment_mode}
                  onChange={(e) => setPaymentForm({ ...paymentForm, payment_mode: e.target.value })}
                  style={{
                    width: '100%',
                    padding: '0.5rem',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--color-border)',
                    fontSize: 'var(--font-size-sm)',
                  }}
                >
                  <option value="cash">Cash (ரொக்கம்)</option>
                  <option value="upi">UPI (GPay/PhonePe)</option>
                  <option value="card">Card</option>
                  <option value="bank_transfer">Bank Transfer</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700 }}>Notes / Reference (Optional)</label>
                <Input
                  value={paymentForm.notes}
                  onChange={(e) => setPaymentForm({ ...paymentForm, notes: e.target.value })}
                  placeholder="e.g. Paid in cash at counter"
                />
              </div>

              <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
                <Button variant="secondary" type="button" onClick={() => setPaymentCustomer(null)}>
                  Cancel
                </Button>
                <Button variant="primary" type="submit" disabled={isSubmitting}>
                  {isSubmitting ? 'Recording...' : 'Record Payment'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 3: KHATA LEDGER HISTORY */}
      {ledgerCustomer && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(15, 23, 42, 0.65)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1100, padding: '1rem' }}>
          <div style={{ backgroundColor: '#ffffff', borderRadius: 'var(--radius-lg)', width: '100%', maxWidth: '600px', maxHeight: '85vh', display: 'flex', flexDirection: 'column', boxShadow: 'var(--shadow-lg)', overflow: 'hidden' }}>
            <div style={{ padding: '1.25rem', borderBottom: '1px solid var(--color-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: 'var(--color-bg-subtle)' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: 'var(--font-size-lg)', fontWeight: 800 }}>
                  {ledgerCustomer.name} — Khata Ledger
                </h3>
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                  Phone: {ledgerCustomer.phone} • Current Debt: <strong style={{ color: 'var(--color-danger)' }}>{formatCurrency(ledgerCustomer.current_balance)}</strong>
                </div>
              </div>
              <button
                onClick={() => setLedgerCustomer(null)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-muted)' }}
              >
                <X size={20} />
              </button>
            </div>

            <div style={{ padding: '1.25rem', overflowY: 'auto', flex: 1 }}>
              {isLoadingLedger ? (
                <div style={{ padding: '2rem', display: 'flex', justifyContent: 'center' }}>
                  <LoadingSpinner label="Loading ledger transactions..." />
                </div>
              ) : ledgerEntries.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--color-text-muted)' }}>
                  No transaction history recorded for this customer.
                </div>
              ) : (
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--font-size-sm)' }}>
                  <thead>
                    <tr style={{ borderBottom: '2px solid var(--color-border)', textAlign: 'left', color: 'var(--color-text-muted)' }}>
                      <th style={{ padding: '0.5rem' }}>Date</th>
                      <th style={{ padding: '0.5rem' }}>{t('entry_type')}</th>
                      <th style={{ padding: '0.5rem', textAlign: 'right' }}>{t('amount')}</th>
                      <th style={{ padding: '0.5rem', textAlign: 'right' }}>Balance After</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ledgerEntries.map((entry) => {
                      const isCreditSale = entry.entry_type === 'credit_sale';
                      return (
                        <tr key={entry.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                          <td style={{ padding: '0.5rem', color: 'var(--color-text-muted)', fontSize: 'var(--font-size-xs)' }}>
                            {new Date(entry.created_at).toLocaleDateString()} {new Date(entry.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </td>
                          <td style={{ padding: '0.5rem' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', fontWeight: 600 }}>
                              {isCreditSale ? (
                                <ArrowUpRight size={14} color="var(--color-danger)" />
                              ) : (
                                <ArrowDownLeft size={14} color="var(--color-accent)" />
                              )}
                              <span>{isCreditSale ? t('entry_credit_sale') : t('entry_payment_received')}</span>
                            </div>
                            {entry.notes && (
                              <div style={{ fontSize: '0.7rem', color: 'var(--color-text-subtle)' }}>
                                {entry.notes}
                              </div>
                            )}
                          </td>
                          <td
                            style={{
                              padding: '0.5rem',
                              textAlign: 'right',
                              fontWeight: 700,
                              color: isCreditSale ? 'var(--color-danger)' : 'var(--color-accent)',
                            }}
                          >
                            {isCreditSale ? `+${formatCurrency(entry.amount)}` : `-${formatCurrency(entry.amount)}`}
                          </td>
                          <td style={{ padding: '0.5rem', textAlign: 'right', fontWeight: 800 }}>
                            {formatCurrency(entry.balance_after)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>

            <div style={{ padding: '1rem', borderTop: '1px solid var(--color-border)', display: 'flex', justifyContent: 'flex-end', backgroundColor: 'var(--color-bg-subtle)' }}>
              <Button variant="secondary" onClick={() => setLedgerCustomer(null)}>
                Close
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Toast Notification */}
      {toastMessage && (
        <Toast message={toastMessage} onClose={() => setToastMessage(null)} />
      )}
    </div>
  );
}
