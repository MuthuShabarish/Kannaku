import React, { useState, useEffect, useCallback } from 'react';
import { useI18n } from '../context/I18nContext';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { Badge, LoadingSpinner, Alert } from '../components/common/Feedback';
import { Button } from '../components/common/Button';
import {
  TrendingUp,
  Receipt,
  ShoppingCart,
  Coins,
  Package,
  Calendar,
  Layers,
  Truck,
  ShieldCheck,
  RefreshCw
} from 'lucide-react';

export function ReportsPage() {
  const { t, formatCurrency } = useI18n();
  const { business } = useAuth();

  // Subtab State: 'overview' | 'trends' | 'products'
  const [activeSubTab, setActiveSubTab] = useState('overview');

  // Filter Preset State: 'today' | 'week' | 'month' | 'all' | 'custom'
  const [periodPreset, setPeriodPreset] = useState('month');
  const [customStartDate, setCustomStartDate] = useState('');
  const [customEndDate, setCustomEndDate] = useState('');

  // Trend Interval: 'day' | 'month'
  const [trendInterval, setTrendInterval] = useState('day');
  // Product View: 'revenue' | 'quantity'
  const [productSortMode, setProductSortMode] = useState('revenue');

  // Data States
  const [summaryData, setSummaryData] = useState(null);
  const [trendsData, setTrendsData] = useState(null);
  const [productData, setProductData] = useState(null);
  const [profitOverviewData, setProfitOverviewData] = useState(null);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Compute ISO date range params
  const getDateParams = useCallback(() => {
    if (periodPreset === 'custom') {
      const params = {};
      if (customStartDate) params.start_date = new Date(`${customStartDate}T00:00:00`).toISOString();
      if (customEndDate) params.end_date = new Date(`${customEndDate}T23:59:59`).toISOString();
      return params;
    }

    const now = new Date();
    if (periodPreset === 'today') {
      const start = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0);
      const end = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59);
      return { start_date: start.toISOString(), end_date: end.toISOString() };
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
    return {}; // 'all'
  }, [periodPreset, customStartDate, customEndDate]);

  const loadAllReports = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const dateParams = getDateParams();

      const [sumRes, trendRes, prodRes, profRes] = await Promise.all([
        api.getReportsSummary(dateParams),
        api.getSalesTrends({ ...dateParams, interval: trendInterval }),
        api.getProductSalesReport({ ...dateParams, limit: 15 }),
        api.getProfitOverview(dateParams)
      ]);

      setSummaryData(sumRes.data || null);
      setTrendsData(trendRes.data || null);
      setProductData(prodRes.data || null);
      setProfitOverviewData(profRes.data || null);
    } catch (err) {
      console.error('Failed to load reports:', err);
      setError(err.message || 'Failed to load report data');
    } finally {
      setIsLoading(false);
    }
  }, [getDateParams, trendInterval]);

  useEffect(() => {
    loadAllReports();
  }, [loadAllReports]);

  const sales = summaryData?.sales;
  const purchases = summaryData?.purchases;
  const expenses = summaryData?.expenses;
  const profit = summaryData?.profit;
  const cashMovement = summaryData?.cash_movement;

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Page Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', marginBottom: '0.25rem' }}>
            <h1 style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 800, color: 'var(--color-primary-dark)', margin: 0 }}>
              {t('reports_title')}
            </h1>
            <Badge variant="primary">{business?.tier ? t(`tier_${business.tier}`) : 'SIMPLE'}</Badge>
          </div>
          <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)', margin: 0 }}>
            {t('reports_subtitle')}
          </p>
        </div>

        <Button variant="outline" onClick={loadAllReports} disabled={isLoading}>
          <RefreshCw size={15} className={isLoading ? 'spin' : ''} />
          {t('apply_filter')}
        </Button>
      </div>

      {/* Date Filter Bar */}
      <div className="card" style={{ padding: '0.875rem 1.25rem', display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Calendar size={18} color="var(--color-primary)" />
            <span style={{ fontSize: 'var(--font-size-sm)', fontWeight: 700 }}>{t('filter_period')}:</span>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {[
              { id: 'today', label: t('period_today') },
              { id: 'week', label: t('period_week') },
              { id: 'month', label: t('period_month') },
              { id: 'all', label: t('period_all') },
              { id: 'custom', label: t('custom_date') }
            ].map((p) => (
              <button
                key={p.id}
                onClick={() => setPeriodPreset(p.id)}
                style={{
                  padding: '0.375rem 0.875rem',
                  borderRadius: 'var(--radius-full)',
                  fontSize: 'var(--font-size-xs)',
                  fontWeight: 600,
                  border: periodPreset === p.id ? '1px solid var(--color-primary)' : '1px solid var(--color-border)',
                  backgroundColor: periodPreset === p.id ? 'var(--color-primary-soft)' : 'transparent',
                  color: periodPreset === p.id ? 'var(--color-primary)' : 'var(--color-text-main)',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease'
                }}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {periodPreset === 'custom' && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap', paddingTop: '0.5rem', borderTop: '1px solid var(--color-border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
              <label style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', fontWeight: 600 }}>
                {t('start_date')}:
              </label>
              <input
                type="date"
                value={customStartDate}
                onChange={(e) => setCustomStartDate(e.target.value)}
                style={{
                  padding: '0.375rem 0.625rem',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--color-border)',
                  fontSize: 'var(--font-size-sm)'
                }}
              />
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
              <label style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', fontWeight: 600 }}>
                {t('end_date')}:
              </label>
              <input
                type="date"
                value={customEndDate}
                onChange={(e) => setCustomEndDate(e.target.value)}
                style={{
                  padding: '0.375rem 0.625rem',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--color-border)',
                  fontSize: 'var(--font-size-sm)'
                }}
              />
            </div>
            <Button variant="primary" size="sm" onClick={loadAllReports}>
              {t('apply_filter')}
            </Button>
          </div>
        )}
      </div>

      {/* Loading & Error States */}
      {isLoading && (
        <div style={{ padding: '3rem 0' }}>
          <LoadingSpinner label="Compiling business intelligence and financial metrics..." />
        </div>
      )}

      {error && !isLoading && (
        <Alert type="danger" title="Error loading report data" message={error} />
      )}

      {!isLoading && !error && (
        <>
          {/* Top Level Summary Cards Grid */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
              gap: '1rem'
            }}
          >
            {/* Sales Revenue */}
            <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                  {t('sales_revenue')}
                </span>
                <div style={{ padding: '0.375rem', borderRadius: 'var(--radius-md)', backgroundColor: 'var(--color-primary-soft)', color: 'var(--color-primary)' }}>
                  <ShoppingCart size={18} />
                </div>
              </div>
              <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 800, color: 'var(--color-primary-dark)' }}>
                {formatCurrency(sales?.total_revenue || 0)}
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                <span>{sales?.invoice_count || 0} {t('invoice_count')}</span>
                <span>{t('avg_order_value')}: {formatCurrency(sales?.average_invoice_value || 0)}</span>
              </div>
            </div>

            {/* COGS (Historical Snapshot) */}
            <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                  {t('cogs')}
                </span>
                <div style={{ padding: '0.375rem', borderRadius: 'var(--radius-md)', backgroundColor: '#fff7ed', color: '#c2410c' }}>
                  <Package size={18} />
                </div>
              </div>
              <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 800, color: '#c2410c' }}>
                {formatCurrency(profit?.cogs_total || 0)}
              </div>
              <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                Historical cost snapshotted at time of sale
              </div>
            </div>

            {/* Gross Profit */}
            <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                  {t('gross_profit')}
                </span>
                <div style={{ padding: '0.375rem', borderRadius: 'var(--radius-md)', backgroundColor: 'var(--color-accent-soft)', color: 'var(--color-accent)' }}>
                  <TrendingUp size={18} />
                </div>
              </div>
              <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 800, color: '#047857' }}>
                {formatCurrency(profit?.gross_profit || 0)}
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                <span>Sales Revenue &minus; COGS</span>
                <span style={{ fontWeight: 700, color: '#047857' }}>{profit?.gross_profit_margin_pct || 0}% {t('gross_margin')}</span>
              </div>
            </div>

            {/* Operating Profit Estimate */}
            <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', border: '2px solid var(--color-primary-light)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, color: 'var(--color-primary)', textTransform: 'uppercase' }}>
                  {t('operating_profit_estimate')}
                </span>
                <div style={{ padding: '0.375rem', borderRadius: 'var(--radius-md)', backgroundColor: 'var(--color-primary-soft)', color: 'var(--color-primary)' }}>
                  <Coins size={18} />
                </div>
              </div>
              <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 800, color: Number(profit?.operating_profit_estimate || 0) >= 0 ? 'var(--color-primary)' : 'var(--color-danger)' }}>
                {formatCurrency(profit?.operating_profit_estimate || 0)}
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                <span>Gross Profit &minus; Paid Expenses ({formatCurrency(profit?.operating_expenses || 0)})</span>
                <span style={{ fontWeight: 700 }}>{profit?.operating_profit_margin_pct || 0}% Margin</span>
              </div>
            </div>

            {/* Net Cash Movement */}
            <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                  {t('net_cash_flow')}
                </span>
                <div style={{ padding: '0.375rem', borderRadius: 'var(--radius-md)', backgroundColor: '#f0fdf4', color: '#16a34a' }}>
                  <Coins size={18} />
                </div>
              </div>
              <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 800, color: Number(cashMovement?.net_cash_movement || 0) >= 0 ? '#16a34a' : 'var(--color-danger)' }}>
                {formatCurrency(cashMovement?.net_cash_movement || 0)}
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                <span>In: {formatCurrency(cashMovement?.total_inflows || 0)}</span>
                <span>Out: {formatCurrency(cashMovement?.total_outflows || 0)}</span>
              </div>
            </div>

            {/* Total Purchases */}
            <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                  {t('total_purchases')}
                </span>
                <div style={{ padding: '0.375rem', borderRadius: 'var(--radius-md)', backgroundColor: '#eff6ff', color: '#2563eb' }}>
                  <Truck size={18} />
                </div>
              </div>
              <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 800, color: '#1e40af' }}>
                {formatCurrency(purchases?.total_purchases || 0)}
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                <span>{purchases?.purchase_count || 0} {t('purchases_count')}</span>
                <span>Stock Capitalized</span>
              </div>
            </div>
          </div>

          {/* Subtab Navigation Pill Buttons */}
          <div style={{ display: 'flex', gap: '0.5rem', borderBottom: '1px solid var(--color-border)', paddingBottom: '0.5rem' }}>
            <button
              onClick={() => setActiveSubTab('overview')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.5rem 1rem',
                borderRadius: 'var(--radius-md)',
                fontWeight: activeSubTab === 'overview' ? 700 : 500,
                fontSize: 'var(--font-size-sm)',
                backgroundColor: activeSubTab === 'overview' ? 'var(--color-primary-soft)' : 'transparent',
                color: activeSubTab === 'overview' ? 'var(--color-primary)' : 'var(--color-text-main)',
                border: 'none',
                cursor: 'pointer'
              }}
            >
              <Coins size={16} />
              {t('tab_overview')}
            </button>
            <button
              onClick={() => setActiveSubTab('trends')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.5rem 1rem',
                borderRadius: 'var(--radius-md)',
                fontWeight: activeSubTab === 'trends' ? 700 : 500,
                fontSize: 'var(--font-size-sm)',
                backgroundColor: activeSubTab === 'trends' ? 'var(--color-primary-soft)' : 'transparent',
                color: activeSubTab === 'trends' ? 'var(--color-primary)' : 'var(--color-text-main)',
                border: 'none',
                cursor: 'pointer'
              }}
            >
              <TrendingUp size={16} />
              {t('tab_trends')}
            </button>
            <button
              onClick={() => setActiveSubTab('products')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.5rem 1rem',
                borderRadius: 'var(--radius-md)',
                fontWeight: activeSubTab === 'products' ? 700 : 500,
                fontSize: 'var(--font-size-sm)',
                backgroundColor: activeSubTab === 'products' ? 'var(--color-primary-soft)' : 'transparent',
                color: activeSubTab === 'products' ? 'var(--color-primary)' : 'var(--color-text-main)',
                border: 'none',
                cursor: 'pointer'
              }}
            >
              <Package size={16} />
              {t('tab_products')}
            </button>
          </div>

          {/* Subtab 1: FINANCIAL OVERVIEW & PROFIT */}
          {activeSubTab === 'overview' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              {/* Profit vs Cash Flow Comparison */}
              <div className="card" style={{ padding: '1.25rem' }}>
                <h3 style={{ fontSize: 'var(--font-size-base)', fontWeight: 700, marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Coins size={18} color="var(--color-primary)" />
                  {t('profit_vs_cash')}
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
                  <div style={{ padding: '1rem', borderRadius: 'var(--radius-md)', backgroundColor: 'var(--color-bg-subtle)', border: '1px solid var(--color-border)' }}>
                    <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', fontWeight: 600 }}>OPERATING PROFIT ESTIMATE</div>
                    <div style={{ fontSize: 'var(--font-size-xl)', fontWeight: 800, color: 'var(--color-primary)', marginTop: '0.25rem' }}>
                      {formatCurrency(profit?.operating_profit_estimate || 0)}
                    </div>
                    <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginTop: '0.25rem' }}>
                      Sales delivered minus inventory COGS and paid business running expenses.
                    </div>
                  </div>

                  <div style={{ padding: '1rem', borderRadius: 'var(--radius-md)', backgroundColor: 'var(--color-bg-subtle)', border: '1px solid var(--color-border)' }}>
                    <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', fontWeight: 600 }}>NET RECORDED CASH MOVEMENT</div>
                    <div style={{ fontSize: 'var(--font-size-xl)', fontWeight: 800, color: '#16a34a', marginTop: '0.25rem' }}>
                      {formatCurrency(cashMovement?.net_cash_movement || 0)}
                    </div>
                    <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginTop: '0.25rem' }}>
                      Physical and digital money actually collected minus money actually disbursed.
                    </div>
                  </div>
                </div>

                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', lineHeight: 1.6 }}>
                  <strong>Key Accounting Safeguards:</strong> Customer Khata collections add liquidity (+cash) but are not new revenue.
                  Similarly, supplier settlements decrease cash (-cash) but are settlements of accounts payable, not new purchases or expenses.
                  Profit measures value creation, while cash measures liquidity timing.
                </div>
              </div>

              {/* Expense Breakdown Section */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.25rem' }}>
                {/* Expense Status Distribution */}
                <div className="card">
                  <h3 style={{ fontSize: 'var(--font-size-base)', fontWeight: 700, marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Receipt size={18} color="var(--color-primary)" />
                    Expense Status Distribution
                  </h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem', fontSize: 'var(--font-size-sm)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '0.375rem', borderBottom: '1px solid var(--color-border)' }}>
                      <span>{t('paid_expenses')} (included in profit estimate):</span>
                      <span style={{ fontWeight: 700, color: 'var(--color-primary)' }}>{formatCurrency(expenses?.paid_expenses || 0)}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '0.375rem', borderBottom: '1px solid var(--color-border)' }}>
                      <span>{t('unpaid_expenses')} (pending vouchers):</span>
                      <span style={{ fontWeight: 700, color: '#d97706' }}>{formatCurrency(expenses?.unpaid_expenses || 0)}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '0.375rem', borderBottom: '1px solid var(--color-border)' }}>
                      <span>{t('status_voided')} (excluded):</span>
                      <span style={{ fontWeight: 700, color: 'var(--color-text-muted)' }}>{formatCurrency(expenses?.voided_expenses || 0)}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', paddingTop: '0.25rem', fontWeight: 800 }}>
                      <span>Total Active Overheads:</span>
                      <span>{formatCurrency(expenses?.total_expenses || 0)}</span>
                    </div>
                  </div>
                </div>

                {/* Operating Expenses by Category */}
                <div className="card">
                  <h3 style={{ fontSize: 'var(--font-size-base)', fontWeight: 700, marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Layers size={18} color="var(--color-primary)" />
                    Operating Overheads by Category
                  </h3>
                  {profitOverviewData?.expense_breakdown_by_category?.length === 0 ? (
                    <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)', padding: '1rem 0' }}>
                      No paid expenses recorded in this period.
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '220px', overflowY: 'auto' }}>
                      {profitOverviewData?.expense_breakdown_by_category?.map((c) => (
                        <div
                          key={c.category_id}
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            fontSize: 'var(--font-size-sm)',
                            padding: '0.375rem 0',
                            borderBottom: '1px solid var(--color-border)'
                          }}
                        >
                          <div>
                            <span style={{ fontWeight: 600 }}>{c.category_name}</span>
                            <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginLeft: '0.5rem' }}>({c.count} items)</span>
                          </div>
                          <span style={{ fontWeight: 700 }}>{formatCurrency(c.amount)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Transparent Calculation Rules Disclosures Card */}
              <div className="card" style={{ backgroundColor: 'var(--color-bg-subtle)', border: '1px solid var(--color-border)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                  <ShieldCheck size={20} color="var(--color-primary)" />
                  <h3 style={{ fontSize: 'var(--font-size-base)', fontWeight: 700, margin: 0 }}>
                    {t('accounting_rules_title')}
                  </h3>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem', fontSize: 'var(--font-size-xs)', lineHeight: 1.6, color: 'var(--color-text-main)' }}>
                  <div>
                    <strong>1. Sales Revenue:</strong> Total invoices of completed sales. Cancelled sales are excluded. Khata credit repayments are debt collections, not sales revenue.
                  </div>
                  <div>
                    <strong>2. Cost of Goods Sold (COGS):</strong> Computed from historical moving-average cost snapshots stored on sale items at the moment of sale. Never altered by subsequent purchase price changes.
                  </div>
                  <div>
                    <strong>3. Gross Profit:</strong> Exact difference between Sales Revenue and COGS.
                  </div>
                  <div>
                    <strong>4. Inventory Purchases:</strong> Inventory purchases increase asset stock and accounts payable/cash; they are realized through COGS as goods are sold, and are never counted twice as operating expenses.
                  </div>
                  <div>
                    <strong>5. Operating Profit Estimate:</strong> Gross Profit minus Paid Operating Expenses. Labeled as an operational estimate because expenses represent cash vouchers rather than an independent accrual liability ledger.
                  </div>
                  <div>
                    <strong>6. Split Payments:</strong> Split-tender payments (e.g. ₹50 cash + ₹50 UPI) accurately allocate payment legs without multiplying invoice revenue.
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Subtab 2: SALES TRENDS */}
          {activeSubTab === 'trends' && (
            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.75rem' }}>
                <h3 style={{ fontSize: 'var(--font-size-base)', fontWeight: 700, margin: 0 }}>
                  Sales & Profit Trends
                </h3>
                <div style={{ display: 'flex', gap: '0.375rem' }}>
                  <Button
                    variant={trendInterval === 'day' ? 'primary' : 'outline'}
                    size="sm"
                    onClick={() => setTrendInterval('day')}
                  >
                    {t('daily_trend')}
                  </Button>
                  <Button
                    variant={trendInterval === 'month' ? 'primary' : 'outline'}
                    size="sm"
                    onClick={() => setTrendInterval('month')}
                  >
                    {t('monthly_trend')}
                  </Button>
                </div>
              </div>

              {trendsData?.trends?.length === 0 ? (
                <div style={{ padding: '2rem 0', textAlign: 'center', color: 'var(--color-text-muted)' }}>
                  {t('no_data_for_period')}
                </div>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--font-size-sm)' }}>
                    <thead>
                      <tr style={{ borderBottom: '2px solid var(--color-border)', textAlign: 'left', color: 'var(--color-text-muted)', fontSize: 'var(--font-size-xs)' }}>
                        <th style={{ padding: '0.625rem' }}>PERIOD</th>
                        <th style={{ padding: '0.625rem', textAlign: 'center' }}>{t('invoice_count')}</th>
                        <th style={{ padding: '0.625rem', textAlign: 'right' }}>{t('sales_revenue')}</th>
                        <th style={{ padding: '0.625rem', textAlign: 'right' }}>{t('cogs')}</th>
                        <th style={{ padding: '0.625rem', textAlign: 'right' }}>{t('gross_profit')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {trendsData?.trends?.map((pt) => (
                        <tr key={pt.date_key} style={{ borderBottom: '1px solid var(--color-border)' }}>
                          <td style={{ padding: '0.625rem', fontWeight: 600 }}>{pt.date_key}</td>
                          <td style={{ padding: '0.625rem', textAlign: 'center' }}>
                            <Badge variant="neutral">{pt.invoice_count}</Badge>
                          </td>
                          <td style={{ padding: '0.625rem', textAlign: 'right', fontWeight: 700, color: 'var(--color-primary)' }}>
                            {formatCurrency(pt.sales_revenue)}
                          </td>
                          <td style={{ padding: '0.625rem', textAlign: 'right', color: '#c2410c' }}>
                            {formatCurrency(pt.cogs_total)}
                          </td>
                          <td style={{ padding: '0.625rem', textAlign: 'right', fontWeight: 700, color: '#047857' }}>
                            {formatCurrency(pt.gross_profit)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Subtab 3: PRODUCT & CATEGORY PERFORMANCE */}
          {activeSubTab === 'products' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              {/* Product Rankings Card */}
              <div className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.75rem' }}>
                  <h3 style={{ fontSize: 'var(--font-size-base)', fontWeight: 700, margin: 0 }}>
                    Best-Selling Products
                  </h3>
                  <div style={{ display: 'flex', gap: '0.375rem' }}>
                    <Button
                      variant={productSortMode === 'revenue' ? 'primary' : 'outline'}
                      size="sm"
                      onClick={() => setProductSortMode('revenue')}
                    >
                      {t('top_by_revenue')}
                    </Button>
                    <Button
                      variant={productSortMode === 'quantity' ? 'primary' : 'outline'}
                      size="sm"
                      onClick={() => setProductSortMode('quantity')}
                    >
                      {t('top_by_qty')}
                    </Button>
                  </div>
                </div>

                {((productSortMode === 'revenue' ? productData?.top_by_revenue : productData?.top_by_quantity) || []).length === 0 ? (
                  <div style={{ padding: '2rem 0', textAlign: 'center', color: 'var(--color-text-muted)' }}>
                    {t('no_data_for_period')}
                  </div>
                ) : (
                  <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--font-size-sm)' }}>
                      <thead>
                        <tr style={{ borderBottom: '2px solid var(--color-border)', textAlign: 'left', color: 'var(--color-text-muted)', fontSize: 'var(--font-size-xs)' }}>
                          <th style={{ padding: '0.625rem' }}>PRODUCT</th>
                          <th style={{ padding: '0.625rem' }}>CATEGORY</th>
                          <th style={{ padding: '0.625rem', textAlign: 'center' }}>{t('quantity_sold')}</th>
                          <th style={{ padding: '0.625rem', textAlign: 'right' }}>{t('revenue')}</th>
                          <th style={{ padding: '0.625rem', textAlign: 'right' }}>{t('cogs')}</th>
                          <th style={{ padding: '0.625rem', textAlign: 'right' }}>{t('gross_profit')}</th>
                          <th style={{ padding: '0.625rem', textAlign: 'right' }}>{t('margin')}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(productSortMode === 'revenue' ? productData?.top_by_revenue : productData?.top_by_quantity)?.map((item) => (
                          <tr key={item.product_id} style={{ borderBottom: '1px solid var(--color-border)' }}>
                            <td style={{ padding: '0.625rem', fontWeight: 600 }}>{item.product_name}</td>
                            <td style={{ padding: '0.625rem', color: 'var(--color-text-muted)' }}>
                              <Badge variant="neutral">{item.category_name || 'General'}</Badge>
                            </td>
                            <td style={{ padding: '0.625rem', textAlign: 'center', fontWeight: 600 }}>
                              {Number(item.quantity_sold)} {item.unit}
                            </td>
                            <td style={{ padding: '0.625rem', textAlign: 'right', fontWeight: 700, color: 'var(--color-primary)' }}>
                              {formatCurrency(item.revenue)}
                            </td>
                            <td style={{ padding: '0.625rem', textAlign: 'right', color: '#c2410c' }}>
                              {formatCurrency(item.cogs)}
                            </td>
                            <td style={{ padding: '0.625rem', textAlign: 'right', fontWeight: 700, color: '#047857' }}>
                              {formatCurrency(item.gross_profit)}
                            </td>
                            <td style={{ padding: '0.625rem', textAlign: 'right', fontWeight: 600 }}>
                              {item.margin_pct}%
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* Category Performance Card */}
              <div className="card">
                <h3 style={{ fontSize: 'var(--font-size-base)', fontWeight: 700, marginBottom: '1rem' }}>
                  {t('category_performance')}
                </h3>
                {productData?.by_category?.length === 0 ? (
                  <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>
                    No category sales data for this period.
                  </div>
                ) : (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem' }}>
                    {productData?.by_category?.map((cat, idx) => (
                      <div
                        key={idx}
                        style={{
                          padding: '0.875rem 1rem',
                          borderRadius: 'var(--radius-md)',
                          backgroundColor: 'var(--color-bg-subtle)',
                          border: '1px solid var(--color-border)'
                        }}
                      >
                        <div style={{ fontWeight: 700, fontSize: 'var(--font-size-sm)', color: 'var(--color-primary-dark)' }}>
                          {cat.category_name}
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-size-xs)', marginTop: '0.5rem' }}>
                          <span style={{ color: 'var(--color-text-muted)' }}>Revenue:</span>
                          <span style={{ fontWeight: 700 }}>{formatCurrency(cat.revenue)}</span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-size-xs)', marginTop: '0.25rem' }}>
                          <span style={{ color: 'var(--color-text-muted)' }}>Gross Profit:</span>
                          <span style={{ fontWeight: 700, color: '#047857' }}>{formatCurrency(cat.gross_profit)}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
