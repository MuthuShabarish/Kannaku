import React, { useState, useEffect } from 'react';
import { useI18n } from '../../context/I18nContext';
import { api } from '../../services/api';
import { X, Building2, ArrowDownLeft, ArrowUpRight, Clock, RefreshCw } from 'lucide-react';
import { LoadingSpinner } from '../common/Feedback';

export function SupplierLedgerDrawer({ supplierId, isOpen, onClose }) {
  const { t, formatCurrency } = useI18n();

  const [supplier, setSupplier] = useState(null);
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen && supplierId) {
      loadData();
    }
  }, [isOpen, supplierId]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.getSupplier(supplierId);
      if (res.data) {
        setSupplier(res.data);
        setEntries(res.data.recent_entries || []);
      }
    } catch (err) {
      setError(err.message || 'Failed to load supplier ledger.');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(15, 23, 42, 0.6)',
        backdropFilter: 'blur(3px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'flex-end',
        zIndex: 999,
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        style={{
          backgroundColor: '#ffffff',
          width: '100%',
          maxWidth: '560px',
          height: '100%',
          boxShadow: 'var(--shadow-lg)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        {/* Drawer Header */}
        <div
          style={{
            padding: '1.25rem 1.5rem',
            borderBottom: '1px solid var(--color-border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            backgroundColor: 'var(--color-bg-subtle)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
            <Building2 size={22} color="var(--color-primary)" />
            <div>
              <h3 style={{ margin: 0, fontSize: 'var(--font-size-base)', fontWeight: 700, color: 'var(--color-text-main)' }}>
                {supplier?.name || 'Supplier Ledger'}
              </h3>
              {supplier?.phone && (
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                  Phone: {supplier.phone}
                </div>
              )}
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <button
              onClick={loadData}
              title="Refresh"
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                color: 'var(--color-text-muted)',
                padding: '0.25rem',
              }}
            >
              <RefreshCw size={18} />
            </button>
            <button
              onClick={onClose}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                color: 'var(--color-text-muted)',
                padding: '0.25rem',
              }}
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Balance Card */}
        {supplier && (
          <div
            style={{
              padding: '1rem 1.5rem',
              backgroundColor: 'var(--color-primary-soft)',
              borderBottom: '1px solid var(--color-border)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <div>
              <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', fontWeight: 600 }}>
                {t('supplier_dues')}
              </span>
              <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 800, color: 'var(--color-primary)' }}>
                {formatCurrency(supplier.current_balance)}
              </div>
            </div>
            <div style={{ textAlign: 'right', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
              <div>{supplier.address || 'No address specified'}</div>
              {supplier.notes && <div style={{ fontStyle: 'italic', marginTop: '0.25rem' }}>{supplier.notes}</div>}
            </div>
          </div>
        )}

        {/* Entries List */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '1.5rem' }}>
          {loading ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}>
              <LoadingSpinner size="lg" />
            </div>
          ) : error ? (
            <div style={{ color: 'var(--color-danger)', textAlign: 'center', padding: '2rem' }}>{error}</div>
          ) : entries.length === 0 ? (
            <div style={{ textAlign: 'center', color: 'var(--color-text-muted)', padding: '3rem' }}>
              No transactions recorded for this supplier yet.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {entries.map((entry) => {
                const isPurchase = entry.entry_type === 'credit_purchase';
                return (
                  <div
                    key={entry.id}
                    style={{
                      border: '1px solid var(--color-border)',
                      borderRadius: 'var(--radius-md)',
                      padding: '1rem',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      backgroundColor: '#ffffff',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                      <div
                        style={{
                          width: '36px',
                          height: '36px',
                          borderRadius: 'var(--radius-full)',
                          backgroundColor: isPurchase ? 'var(--color-warning-soft)' : 'var(--color-accent-soft)',
                          color: isPurchase ? 'var(--color-warning)' : 'var(--color-accent)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                        }}
                      >
                        {isPurchase ? <ArrowDownLeft size={20} /> : <ArrowUpRight size={20} />}
                      </div>
                      <div>
                        <div style={{ fontWeight: 700, fontSize: 'var(--font-size-sm)', color: 'var(--color-text-main)' }}>
                          {isPurchase ? t('entry_credit_purchase') : t('entry_payment_made')}
                        </div>
                        <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', display: 'flex', alignItems: 'center', gap: '0.25rem', marginTop: '0.125rem' }}>
                          <Clock size={12} /> {new Date(entry.created_at).toLocaleString()}
                        </div>
                        {entry.notes && (
                          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-subtle)', marginTop: '0.25rem' }}>
                            {entry.notes}
                          </div>
                        )}
                      </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div
                        style={{
                          fontSize: 'var(--font-size-base)',
                          fontWeight: 800,
                          color: isPurchase ? 'var(--color-warning)' : 'var(--color-accent)',
                        }}
                      >
                        {isPurchase ? '+' : '-'}{formatCurrency(entry.amount)}
                      </div>
                      <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginTop: '0.125rem' }}>
                        Balance: {formatCurrency(entry.balance_after)}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
