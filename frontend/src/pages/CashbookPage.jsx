import React, { useState, useEffect, useCallback } from 'react';
import { useI18n } from '../context/I18nContext';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { Badge, LoadingSpinner } from '../components/common/Feedback';
import {
  BookOpen,
  ArrowDownLeft,
  ArrowUpRight,
  TrendingUp,
  Banknote,
  QrCode,
  CreditCard,
  Building,
  Calendar,
  Filter,
  Info
} from 'lucide-react';

export function CashbookPage() {
  const { t, formatCurrency } = useI18n();
  const { business } = useAuth();
  const isSimpleTier = business?.tier === 'simple';

  // Filters State
  const [periodPreset, setPeriodPreset] = useState('all');
  const [directionFilter, setDirectionFilter] = useState('');
  const [modeFilter, setModeFilter] = useState('');
  const [sourceFilter, setSourceFilter] = useState('');

  // Data State
  const [transactions, setTransactions] = useState([]);
  const [summary, setSummary] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // Compute date range based on preset
  const getDateRange = useCallback(() => {
    const now = new Date();
    if (periodPreset === 'today') {
      const start = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0);
      return { start_date: start.toISOString() };
    }
    if (periodPreset === 'week') {
      const day = now.getDay() || 7;
      const start = new Date(now);
      start.setDate(now.getDate() - day + 1);
      start.setHours(0, 0, 0, 0);
      return { start_date: start.toISOString() };
    }
    if (periodPreset === 'month') {
      const start = new Date(now.getFullYear(), now.getMonth(), 1, 0, 0, 0);
      return { start_date: start.toISOString() };
    }
    return {};
  }, [periodPreset]);

  const loadCashbook = useCallback(async () => {
    try {
      setIsLoading(true);
      const dateRange = getDateRange();
      const [txRes, sumRes] = await Promise.all([
        api.getCashbookTransactions({
          ...dateRange,
          direction: directionFilter || undefined,
          payment_mode: modeFilter || undefined,
          source_type: sourceFilter || undefined,
          limit: 100,
        }),
        api.getCashbookSummary({
          ...dateRange,
        }),
      ]);

      setTransactions(txRes.data || []);
      setSummary(sumRes.data || null);
    } catch (err) {
      console.error('Failed to load cashbook records:', err);
    } finally {
      setIsLoading(false);
    }
  }, [getDateRange, directionFilter, modeFilter, sourceFilter]);

  useEffect(() => {
    loadCashbook();
  }, [loadCashbook]);

  const getModeIcon = (mode) => {
    switch (mode?.toLowerCase()) {
      case 'upi':
        return <QrCode size={14} color="#7c3aed" />;
      case 'card':
        return <CreditCard size={14} color="#2563eb" />;
      case 'bank_transfer':
        return <Building size={14} color="#0d9488" />;
      case 'cash':
      default:
        return <Banknote size={14} color="#16a34a" />;
    }
  };

  const getSourceBadgeVariant = (source) => {
    switch (source) {
      case 'sale_payment':
      case 'customer_settlement':
        return 'success';
      case 'purchase_payment':
      case 'supplier_settlement':
        return 'warning';
      case 'operating_expense':
      default:
        return 'neutral';
    }
  };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', paddingBottom: '3rem' }}>
      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
          marginBottom: '1.5rem',
        }}
      >
        <div>
          <h1 style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 800, color: 'var(--color-primary-dark)', margin: 0 }}>
            {t('cashbook_title')}
          </h1>
          <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)', margin: '0.25rem 0 0' }}>
            {t('cashbook_subtitle')}
          </p>
        </div>

        {/* Period Presets */}
        <div style={{ display: 'flex', gap: '0.5rem', backgroundColor: 'var(--color-bg-subtle)', padding: '0.25rem', borderRadius: 'var(--radius-md)' }}>
          {[
            { id: 'today', label: t('period_today') },
            { id: 'week', label: t('period_week') },
            { id: 'month', label: t('period_month') },
            { id: 'all', label: t('period_all') },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setPeriodPreset(tab.id)}
              style={{
                border: 'none',
                padding: '0.375rem 0.75rem',
                borderRadius: 'var(--radius-sm)',
                fontSize: 'var(--font-size-xs)',
                fontWeight: 700,
                cursor: 'pointer',
                backgroundColor: periodPreset === tab.id ? 'var(--color-primary)' : 'transparent',
                color: periodPreset === tab.id ? '#ffffff' : 'var(--color-text-muted)',
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* KPI Overview Cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: '1rem',
          marginBottom: '1.5rem',
        }}
      >
        {/* Total Inflows */}
        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', color: '#16a34a' }}>
            <ArrowDownLeft size={20} />
            <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, textTransform: 'uppercase' }}>
              {t('total_inflows')}
            </span>
          </div>
          <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 800, color: '#16a34a' }}>
            +{formatCurrency(summary?.total_inflows || 0)}
          </div>
          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginTop: '0.25rem' }}>
            Sales & Khata collections
          </div>
        </div>

        {/* Total Outflows */}
        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', color: 'var(--color-danger)' }}>
            <ArrowUpRight size={20} />
            <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, textTransform: 'uppercase' }}>
              {t('total_outflows')}
            </span>
          </div>
          <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 800, color: 'var(--color-danger)' }}>
            -{formatCurrency(summary?.total_outflows || 0)}
          </div>
          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginTop: '0.25rem' }}>
            Purchases, supplier dues & expenses
          </div>
        </div>

        {/* Net Cash Movement */}
        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', color: 'var(--color-primary)' }}>
            <TrendingUp size={20} />
            <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, textTransform: 'uppercase' }}>
              {t('net_cash_movement')}
            </span>
          </div>
          <div
            style={{
              fontSize: 'var(--font-size-2xl)',
              fontWeight: 800,
              color:
                parseFloat(summary?.net_cash_movement || 0) >= 0
                  ? '#16a34a'
                  : 'var(--color-danger)',
            }}
          >
            {parseFloat(summary?.net_cash_movement || 0) >= 0 ? '+' : ''}
            {formatCurrency(summary?.net_cash_movement || 0)}
          </div>
          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginTop: '0.25rem' }}>
            Net recorded cash change
          </div>
        </div>

        {/* Total Count */}
        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', color: 'var(--color-text-muted)' }}>
            <BookOpen size={20} color="var(--color-primary)" />
            <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, textTransform: 'uppercase' }}>
              {t('total_transactions')}
            </span>
          </div>
          <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 800, color: 'var(--color-primary-dark)' }}>
            {summary?.transaction_count || 0}
          </div>
          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginTop: '0.25rem' }}>
            Audit-reconciled entries
          </div>
        </div>
      </div>

      {/* Filters Bar */}
      <div
        className="card"
        style={{
          padding: '0.875rem 1rem',
          marginBottom: '1.5rem',
          display: 'flex',
          flexWrap: 'wrap',
          gap: '0.75rem',
          alignItems: 'center',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>
          <Filter size={16} />
          <span style={{ fontWeight: 700 }}>Filter:</span>
        </div>

        <select
          className="input"
          value={directionFilter}
          onChange={(e) => setDirectionFilter(e.target.value)}
          style={{ height: '36px', padding: '0 0.75rem', borderRadius: 'var(--radius-md)', flex: '0 1 160px' }}
        >
          <option value="">All Inflows & Outflows</option>
          <option value="inflow">{t('direction_inflow')}</option>
          <option value="outflow">{t('direction_outflow')}</option>
        </select>

        <select
          className="input"
          value={modeFilter}
          onChange={(e) => setModeFilter(e.target.value)}
          style={{ height: '36px', padding: '0 0.75rem', borderRadius: 'var(--radius-md)', flex: '0 1 140px' }}
        >
          <option value="">{t('all_modes')}</option>
          <option value="cash">Cash</option>
          <option value="upi">UPI</option>
          <option value="card">Card</option>
          <option value="bank_transfer">Bank Transfer</option>
        </select>

        <select
          className="input"
          value={sourceFilter}
          onChange={(e) => setSourceFilter(e.target.value)}
          style={{ height: '36px', padding: '0 0.75rem', borderRadius: 'var(--radius-md)', flex: '0 1 180px' }}
        >
          <option value="">All Sources</option>
          <option value="sale_payment">{t('source_sale')}</option>
          <option value="customer_settlement">{t('source_khata')}</option>
          <option value="purchase_payment">{t('source_purchase')}</option>
          <option value="supplier_settlement">{t('source_supplier')}</option>
          <option value="operating_expense">{t('source_expense')}</option>
        </select>
      </div>

      {/* Transaction Records */}
      {isLoading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}>
          <LoadingSpinner size="large" />
        </div>
      ) : transactions.length === 0 ? (
        <div className="card" style={{ padding: '3rem', textAlign: 'center' }}>
          <BookOpen size={40} color="var(--color-text-muted)" style={{ margin: '0 auto 1rem', opacity: 0.5 }} />
          <h3 style={{ margin: '0 0 0.5rem', fontWeight: 700 }}>No Cashbook Movements</h3>
          <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)', margin: 0 }}>
            No recorded money movements found for the selected filters.
          </p>
        </div>
      ) : isSimpleTier ? (
        /* Simple Mode: Touch Cards */
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
          {transactions.map((tx) => {
            const isInflow = tx.direction === 'inflow';
            return (
              <div
                key={tx.id}
                className="card"
                style={{
                  padding: '1.25rem',
                  borderLeft: `4px solid ${isInflow ? '#16a34a' : 'var(--color-danger)'}`,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.375rem' }}>
                  <div>
                    <div style={{ fontWeight: 800, fontSize: 'var(--font-size-base)', color: 'var(--color-primary-dark)' }}>
                      {tx.party_name || tx.category}
                    </div>
                    <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                      {tx.category} {tx.reference ? `• ${tx.reference}` : ''}
                    </div>
                  </div>
                  <div style={{ fontSize: 'var(--font-size-lg)', fontWeight: 800, color: isInflow ? '#16a34a' : 'var(--color-danger)' }}>
                    {isInflow ? '+' : '-'}{formatCurrency(tx.amount)}
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginTop: '0.75rem', borderTop: '1px solid var(--color-border)', paddingTop: '0.5rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                    {getModeIcon(tx.payment_mode)}
                    <span style={{ textTransform: 'capitalize' }}>{tx.payment_mode.replace('_', ' ')}</span>
                  </div>
                  <span>{new Date(tx.transaction_date).toLocaleDateString()}</span>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        /* Growth & Enterprise: Dense Unified Ledger Table */
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 'var(--font-size-sm)' }}>
              <thead>
                <tr style={{ backgroundColor: 'var(--color-bg-subtle)', borderBottom: '1px solid var(--color-border)' }}>
                  <th style={{ padding: '0.75rem 1rem', fontWeight: 700 }}>Date & Time</th>
                  <th style={{ padding: '0.75rem 1rem', fontWeight: 700 }}>Direction</th>
                  <th style={{ padding: '0.75rem 1rem', fontWeight: 700 }}>Category / Source</th>
                  <th style={{ padding: '0.75rem 1rem', fontWeight: 700 }}>Reference</th>
                  <th style={{ padding: '0.75rem 1rem', fontWeight: 700 }}>Party / Payee</th>
                  <th style={{ padding: '0.75rem 1rem', fontWeight: 700 }}>Payment Mode</th>
                  <th style={{ padding: '0.75rem 1rem', fontWeight: 700, textAlign: 'right' }}>Amount</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((tx) => {
                  const isInflow = tx.direction === 'inflow';
                  return (
                    <tr key={tx.id} style={{ borderBottom: '1px solid var(--color-border)' }}>
                      <td style={{ padding: '0.75rem 1rem', whiteSpace: 'nowrap' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                          <Calendar size={14} color="var(--color-text-muted)" />
                          <span>{new Date(tx.transaction_date).toLocaleDateString()} {new Date(tx.transaction_date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                        </div>
                      </td>
                      <td style={{ padding: '0.75rem 1rem' }}>
                        <span
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.25rem',
                            padding: '0.2rem 0.5rem',
                            borderRadius: 'var(--radius-sm)',
                            fontSize: 'var(--font-size-xs)',
                            fontWeight: 700,
                            backgroundColor: isInflow ? 'rgba(22, 163, 74, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                            color: isInflow ? '#16a34a' : 'var(--color-danger)',
                          }}
                        >
                          {isInflow ? <ArrowDownLeft size={12} /> : <ArrowUpRight size={12} />}
                          {isInflow ? 'Inflow' : 'Outflow'}
                        </span>
                      </td>
                      <td style={{ padding: '0.75rem 1rem' }}>
                        <Badge variant={getSourceBadgeVariant(tx.source_type)}>
                          {tx.category}
                        </Badge>
                      </td>
                      <td style={{ padding: '0.75rem 1rem', fontFamily: 'monospace', fontWeight: 600 }}>
                        {tx.reference || '—'}
                      </td>
                      <td style={{ padding: '0.75rem 1rem', fontWeight: 600 }}>
                        {tx.party_name || '—'}
                      </td>
                      <td style={{ padding: '0.75rem 1rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                          {getModeIcon(tx.payment_mode)}
                          <span style={{ textTransform: 'capitalize' }}>
                            {tx.payment_mode.replace('_', ' ')}
                          </span>
                        </div>
                      </td>
                      <td
                        style={{
                          padding: '0.75rem 1rem',
                          textAlign: 'right',
                          fontWeight: 800,
                          color: isInflow ? '#16a34a' : 'var(--color-danger)',
                        }}
                      >
                        {isInflow ? '+' : '-'}{formatCurrency(tx.amount)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Accounting Disclosure */}
      <div
        style={{
          marginTop: '1.5rem',
          padding: '0.875rem 1.25rem',
          borderRadius: 'var(--radius-md)',
          backgroundColor: 'var(--color-bg-subtle)',
          border: '1px solid var(--color-border)',
          display: 'flex',
          alignItems: 'center',
          gap: '0.625rem',
          fontSize: 'var(--font-size-xs)',
          color: 'var(--color-text-muted)',
        }}
      >
        <Info size={16} color="var(--color-primary)" style={{ flexShrink: 0 }} />
        <span>{t('cashbook_disclosure')}</span>
      </div>
    </div>
  );
}
