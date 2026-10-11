import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useI18n } from '../context/I18nContext';
import { api } from '../services/api';
import {
  Search,
  Plus,
  BookOpen,
  Phone,
  AlertCircle,
  Building2,
  Edit2
} from 'lucide-react';
import { Button } from '../components/common/Button';
import { LoadingSpinner, Toast } from '../components/common/Feedback';
import { SupplierModal } from '../components/suppliers/SupplierModal';
import { SupplierPaymentModal } from '../components/suppliers/SupplierPaymentModal';
import { SupplierLedgerDrawer } from '../components/suppliers/SupplierLedgerDrawer';

export function SuppliersPage() {
  const { t, formatCurrency } = useI18n();

  const [suppliers, setSuppliers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [withBalanceOnly, setWithBalanceOnly] = useState(false);

  // Modals state
  const [showSupplierModal, setShowSupplierModal] = useState(false);
  const [selectedSupplier, setSelectedSupplier] = useState(null);

  const [paymentSupplier, setPaymentSupplier] = useState(null);
  const [ledgerSupplierId, setLedgerSupplierId] = useState(null);

  const [toastMessage, setToastMessage] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);

  const loadSuppliers = useCallback(async () => {
    try {
      setIsLoading(true);
      const res = await api.getSuppliers({
        search: search.trim() || undefined,
        with_balance_only: withBalanceOnly,
        limit: 100,
      });
      setSuppliers(res.data || []);
    } catch (err) {
      console.error('Failed to load suppliers:', err);
      setErrorMessage(err.message || 'Failed to load suppliers.');
    } finally {
      setIsLoading(false);
    }
  }, [search, withBalanceOnly]);

  useEffect(() => {
    loadSuppliers();
  }, [loadSuppliers]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    loadSuppliers();
  };

  // Metrics Calculations
  const metrics = useMemo(() => {
    let totalPayable = 0;
    let dueSuppliersCount = 0;

    suppliers.forEach((s) => {
      const bal = parseFloat(s.current_balance) || 0;
      if (bal > 0) {
        totalPayable += bal;
        dueSuppliersCount += 1;
      }
    });

    return {
      totalSuppliers: suppliers.length,
      totalPayable,
      dueSuppliersCount,
    };
  }, [suppliers]);

  // Save Supplier (Create or Update)
  const handleSaveSupplier = async (data) => {
    if (selectedSupplier) {
      await api.updateSupplier(selectedSupplier.id, data);
      setToastMessage('Supplier updated successfully!');
    } else {
      await api.createSupplier(data);
      setToastMessage('Supplier created successfully!');
    }
    loadSuppliers();
  };

  // Record Payment Handler
  const handleRecordPayment = async (supplierId, data) => {
    await api.recordSupplierPayment(supplierId, data);
    setToastMessage('Payment to supplier recorded successfully!');
    loadSuppliers();
  };

  return (
    <div className="suppliers-page" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Page Header */}
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '1rem' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 'var(--font-size-2xl)', fontWeight: 800, color: 'var(--color-primary)' }}>
            {t('suppliers_title')}
          </h1>
          <p style={{ margin: 0, fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>
            {t('suppliers_subtitle')}
          </p>
        </div>

        <Button
          variant="primary"
          icon={Plus}
          onClick={() => {
            setSelectedSupplier(null);
            setShowSupplierModal(true);
          }}
        >
          {t('add_supplier')}
        </Button>
      </div>

      {/* Metrics Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
        <div style={{ backgroundColor: 'var(--color-bg-surface)', padding: '1.25rem', borderRadius: 'var(--radius-lg)', border: '1px solid var(--color-border)', boxShadow: 'var(--shadow-sm)' }}>
          <div style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, color: 'var(--color-text-muted)' }}>
            Total Suppliers
          </div>
          <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 900, color: 'var(--color-primary)', marginTop: '0.25rem' }}>
            {metrics.totalSuppliers}
          </div>
        </div>

        <div style={{ backgroundColor: 'var(--color-bg-surface)', padding: '1.25rem', borderRadius: 'var(--radius-lg)', border: '1px solid var(--color-border)', boxShadow: 'var(--shadow-sm)' }}>
          <div style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, color: 'var(--color-text-muted)' }}>
            {t('total_payable')}
          </div>
          <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 900, color: 'var(--color-warning)', marginTop: '0.25rem' }}>
            {formatCurrency(metrics.totalPayable)}
          </div>
        </div>

        <div style={{ backgroundColor: 'var(--color-bg-surface)', padding: '1.25rem', borderRadius: 'var(--radius-lg)', border: '1px solid var(--color-border)', boxShadow: 'var(--shadow-sm)' }}>
          <div style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, color: 'var(--color-text-muted)' }}>
            Suppliers with Outstanding Dues
          </div>
          <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 900, color: '#b45309', marginTop: '0.25rem' }}>
            {metrics.dueSuppliersCount}
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
              placeholder="Search by supplier name, phone or email..."
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
          <span>Only show suppliers with outstanding dues</span>
        </label>
      </div>

      {/* Error Alert */}
      {errorMessage && (
        <div style={{ backgroundColor: 'var(--color-danger-soft)', border: '1px solid var(--color-danger)', color: 'var(--color-danger)', padding: '0.75rem 1rem', borderRadius: 'var(--radius-md)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <AlertCircle size={18} />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Suppliers Table */}
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
            <LoadingSpinner label="Loading suppliers..." />
          </div>
        ) : suppliers.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--color-text-muted)' }}>
            No suppliers found. Click "+ New Supplier" to register your first supplier.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--font-size-sm)' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid var(--color-border)', textAlign: 'left', color: 'var(--color-text-muted)' }}>
                  <th style={{ padding: '0.75rem 0.5rem' }}>{t('supplier_name')}</th>
                  <th style={{ padding: '0.75rem 0.5rem' }}>{t('supplier_phone')}</th>
                  <th style={{ padding: '0.75rem 0.5rem' }}>{t('supplier_address')}</th>
                  <th style={{ padding: '0.75rem 0.5rem', textAlign: 'right' }}>{t('supplier_dues')}</th>
                  <th style={{ padding: '0.75rem 0.5rem', textAlign: 'right' }}>{t('actions')}</th>
                </tr>
              </thead>
              <tbody>
                {suppliers.map((s) => {
                  const bal = parseFloat(s.current_balance) || 0;
                  const hasDue = bal > 0;

                  return (
                    <tr key={s.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                      <td style={{ padding: '0.75rem 0.5rem' }}>
                        <div style={{ fontWeight: 700, color: 'var(--color-text-main)' }}>{s.name}</div>
                        {s.email && <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-subtle)' }}>{s.email}</div>}
                      </td>
                      <td style={{ padding: '0.75rem 0.5rem', color: 'var(--color-text-muted)' }}>
                        {s.phone ? (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                            <Phone size={14} />
                            <span>{s.phone}</span>
                          </div>
                        ) : (
                          '—'
                        )}
                      </td>
                      <td style={{ padding: '0.75rem 0.5rem', color: 'var(--color-text-muted)', maxWidth: '200px' }}>
                        <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {s.address || '—'}
                        </div>
                      </td>
                      <td style={{ padding: '0.75rem 0.5rem', textAlign: 'right' }}>
                        <span
                          style={{
                            fontWeight: 800,
                            color: hasDue ? '#b45309' : 'var(--color-accent)',
                            backgroundColor: hasDue ? 'var(--color-warning-soft)' : 'transparent',
                            padding: hasDue ? '0.25rem 0.5rem' : '0',
                            borderRadius: 'var(--radius-sm)',
                          }}
                        >
                          {formatCurrency(s.current_balance)}
                        </span>
                      </td>
                      <td style={{ padding: '0.75rem 0.5rem', textAlign: 'right' }}>
                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
                          {hasDue && (
                            <Button
                              variant="primary"
                              size="small"
                              onClick={() => setPaymentSupplier(s)}
                            >
                              {t('pay_dues')}
                            </Button>
                          )}
                          <Button
                            variant="secondary"
                            size="small"
                            icon={BookOpen}
                            onClick={() => setLedgerSupplierId(s.id)}
                          >
                            Ledger
                          </Button>
                          <Button
                            variant="secondary"
                            size="small"
                            icon={Edit2}
                            onClick={() => {
                              setSelectedSupplier(s);
                              setShowSupplierModal(true);
                            }}
                          >
                            Edit
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

      {/* Modals */}
      <SupplierModal
        supplier={selectedSupplier}
        isOpen={showSupplierModal}
        onClose={() => {
          setShowSupplierModal(false);
          setSelectedSupplier(null);
        }}
        onSave={handleSaveSupplier}
      />

      <SupplierPaymentModal
        supplier={paymentSupplier}
        isOpen={!!paymentSupplier}
        onClose={() => setPaymentSupplier(null)}
        onPaymentRecorded={handleRecordPayment}
      />

      <SupplierLedgerDrawer
        supplierId={ledgerSupplierId}
        isOpen={!!ledgerSupplierId}
        onClose={() => setLedgerSupplierId(null)}
      />

      {toastMessage && (
        <Toast message={toastMessage} onClose={() => setToastMessage(null)} />
      )}
    </div>
  );
}
